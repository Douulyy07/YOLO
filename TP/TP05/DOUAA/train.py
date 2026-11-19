"""Entraîne le modèle, le compare à la baseline, sauvegarde les artefacts et enregistre le run dans MLflow.

Usage : python -m maintai.train
        python -m maintai.train --model forest
        python -m maintai.train --C 0.1 --threshold 0.2
        python -m maintai.train --grid                 (grid search sur la régression logistique)
        python -m maintai.train --model forest --grid
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import joblib
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from maintai.config import FEATURES, SEED, TARGET, Settings, get_settings
from maintai.data import load_data, split
from maintai.tracking import log_run


def build_model(kind: str = "logreg", C: float = 1.0) -> Pipeline:
    """Le prétraitement fait partie du modèle : scaler et classifieur sont sauvegardés ensemble."""
    if kind == "forest":
        clf = RandomForestClassifier(n_estimators=200, random_state=SEED)
    else:
        clf = LogisticRegression(C=C, max_iter=1000)
    return Pipeline([("scale", StandardScaler()), ("clf", clf)])


# Les réglages essayés par la grid search (« clf__ » = l'étape « clf » du Pipeline)
MAX_COMBINAISONS = 25  # consigne : pas plus de 25 cas par grid search
GRILLES = {
    "logreg": {
        "clf__C": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
    },  # 6 combinaisons
    "forest": {
        "clf__n_estimators": [50, 100, 200],
        "clf__max_depth": [5, 10, None],
        "clf__min_samples_leaf": [1, 5],
    },  # 3 x 3 x 2 = 18 combinaisons
}


def grid_search(kind: str, X_train, y_train, scoring: str, cv: int = 5):
    """Essaie toutes les combinaisons de GRILLES[kind] en validation croisée, sur le train seulement."""
    n = len(ParameterGrid(GRILLES[kind]))
    if n > MAX_COMBINAISONS:
        raise ValueError(f"grille trop grande : {n} combinaisons (maximum {MAX_COMBINAISONS})")
    print(f"Grid search : {n} combinaisons x {cv} plis = {n * cv} entraînements")
    recherche = GridSearchCV(build_model(kind), GRILLES[kind], scoring=scoring, cv=cv, n_jobs=-1)
    recherche.fit(X_train, y_train)
    meilleurs = {k.removeprefix("clf__"): v for k, v in recherche.best_params_.items()}
    return recherche.best_estimator_, meilleurs, round(float(recherche.best_score_), 3)


def evaluate(model, X_test, y_test, threshold: float) -> dict:
    """Mesure le modèle au seuil de décision choisi, et non au seuil 0,5 par défaut."""
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_test, pred)), 3),
        "recall": round(float(recall_score(y_test, pred)), 3),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 3),
        "threshold": threshold,
    }


def evaluate_baseline(X_train, y_train, X_test, y_test) -> dict:
    """La méthode la plus simple : toujours prédire la classe majoritaire (« pas de panne »)."""
    baseline = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
    pred = baseline.predict(X_test)
    return {
        "accuracy": round(float(accuracy_score(y_test, pred)), 3),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 3),
    }


def save(model, metrics: dict, settings: Settings, threshold: float) -> None:
    """Écrit le modèle, son contrat d'entrée (model_info.json) et ses métriques."""
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, settings.model_path)
    info = {
        "features": FEATURES,
        "target": TARGET,
        "threshold": threshold,
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sklearn_version": sklearn.__version__,
    }
    settings.info_path.write_text(json.dumps(info, indent=2), encoding="utf-8")
    settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m maintai.train")
    p.add_argument("--model", choices=["logreg", "forest"], default="logreg")
    p.add_argument("--C", type=float, default=1.0, help="régularisation de la régression logistique")
    p.add_argument("--threshold", type=float, default=None, help="seuil d'alerte (défaut : MAINTAI_THRESHOLD)")
    p.add_argument("--grid", action="store_true", help="cherche les meilleurs réglages (GridSearchCV)")
    p.add_argument("--scoring", default="average_precision",
                   help="critère de la grid search (ex. average_precision, recall, f1)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = parse_args(argv or [])
    settings = get_settings()
    threshold = args.threshold if args.threshold is not None else settings.threshold
    df = load_data(settings.data_path)
    X_train, X_test, y_train, y_test = split(df)
    if args.grid:
        model, meilleurs, score_cv = grid_search(args.model, X_train, y_train, args.scoring)
        print(f"Grid search ({args.scoring}) : meilleurs réglages {meilleurs}, score CV {score_cv}")
    else:
        model = build_model(args.model, args.C).fit(X_train, y_train)
    metrics = {
        "model": evaluate(model, X_test, y_test, threshold),
        "baseline": evaluate_baseline(X_train, y_train, X_test, y_test),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    save(model, metrics, settings, threshold)

    params = {"model": args.model, "threshold": threshold, "n_train": len(X_train)}
    run_metrics = {k: v for k, v in metrics["model"].items() if k != "threshold"}
    run_metrics["baseline_recall"] = metrics["baseline"]["recall"]
    if args.grid:
        params |= {"grid": True, "scoring": args.scoring} | {k: str(v) for k, v in meilleurs.items()}
        run_metrics["cv_score"] = score_cv
    elif args.model == "logreg":
        params["C"] = args.C
    run_id = log_run(
        params=params,
        metrics=run_metrics,
        model=model,
        X_example=X_train.head(3),
        data_path=settings.data_path,
    )
    print(json.dumps(metrics, indent=2))
    print(f"Modèle sauvegardé dans {settings.model_path}")
    print(f"Run MLflow : {run_id}")
    return metrics


if __name__ == "__main__":
    main(sys.argv[1:])