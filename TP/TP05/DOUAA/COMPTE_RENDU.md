# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** G1 ·  **Membres :** Douaa Ahmito ·  **Date :** 19/11/2026 12:00

---

## 1. Mise en place (dans `TP/TP5`)

```
5 failed, 27 passed
```

Les 5 tests de `test_tracking.py` échouent (`aucun run MLflow : log_run n'a rien enregistré`) : `log_run` renvoie `""` sans rien enregistrer.

Avant `pip install -e .`, `maintai` pointait vers le dossier `TP4`. Après, il pointe vers `TP5`.

## 2. Sprint 1 : MLflow

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_param("data_md5", file_md5(data_path))
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES,
        )
    return run.info.run_id
```

```
32 passed
```

| Commande | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | 0.838 | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `--model forest --threshold 0.2` | 0.831 | 0.479 | 0.854 |

**Choix :** la régression logistique avec `--threshold 0.2`, qui a le meilleur recall (0.838) : on rate le moins de pannes, au prix de plus de fausses alertes. La forêt n'est pas meilleure : à seuil égal, son recall et sa precision sont plus bas.

**Version de scikit-learn :** `scikit-learn==1.8.0` dans le `requirements.txt` du modèle. Cela règle le problème du TP4 (`InconsistentVersionWarning`) : on sait avec quelle version recharger le modèle.

**Où sont les runs :** dans `mlflow.db` (paramètres, métriques) et `mlruns/` (modèles), dans `TP5`. Ils ne vont pas dans Git (`.gitignore`) : ce sont des résultats, lourds et propres à chaque PC.

## 3. Sprint 2 : DVC

```
outs:
- md5: 73e0b7cb3c6f795c70c3ddf970b99c15
  size: 126815
  hash: md5
  path: sensors.csv
```

**md5 et data_md5 :** ce sont les mêmes valeurs. Le run MLflow sait donc exactement sur quelles données il a été entraîné.

**Pourquoi le `.csv` ne va pas dans Git :** les données peuvent être lourdes, et Git garderait toutes les versions pour toujours. Git ne garde que le reçu `.dvc` (md5 et taille) ; le fichier va dans le cache et le stockage DVC.

```
data/sensors.csv.dvc:
	changed outs:
		modified:           data/sensors.csv
```

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---|
| v1 | `4357ee4` | 73e0b7cb | 5000 |
| v2 | `ef8e9a1` | 93fdeef2 | 8000 |

**Retour à la v1 :** `data/sensors.csv` contient 5000 lignes. Après le retour à la v2 : 8000.

**`dvc pull` :** le fichier est récupéré depuis le stockage (`1 file fetched and 1 file added`), avec ses 8000 lignes.

## 4. Relier modèle et données

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 | 73e0b7cb | 4000 | 0.750 | 0.622 |
| v2 | 93fdeef2 | 6400 | 0.741 | 0.650 |

On ne peut pas dire que le modèle v2 est meilleur (ni moins bon) : les deux modèles ne sont pas évalués sur les mêmes données de test. Les écarts sont petits et peuvent venir des données, pas du modèle. Pour comparer, il faut les mêmes données de test.

## 4 bis. Grid search (limitée à 25 combinaisons)

J'ai ajouté une option `--grid` à `train.py` : `GridSearchCV` essaie toutes les combinaisons d'une grille, en validation croisée (5 plis) sur les données d'entraînement seulement, et garde la meilleure. Le critère est `average_precision`, qui ne dépend pas du seuil ; le seuil règle ensuite le compromis recall/precision. Une vérification refuse toute grille de plus de 25 combinaisons.

```python
MAX_COMBINAISONS = 25
GRILLES = {
    "logreg": {"clf__C": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]},  # 6 combinaisons
    "forest": {
        "clf__n_estimators": [50, 100, 200],
        "clf__max_depth": [5, 10, None],
        "clf__min_samples_leaf": [1, 5],
    },  # 18 combinaisons
}
```

Résultats sur la v2 (`n_train = 6400`), seuil 0.2 :

| Run | Combinaisons | Meilleurs réglages | recall | precision | accuracy |
|---|---|---|---|---|---|
| `--grid --threshold 0.2` (`5dbe285b`) | 6 | C = 1.0 | 0.824 | 0.567 | 0.897 |
| `--model forest --grid --threshold 0.2` (`c69bf55d`) | 18 | 100 arbres, max_depth 10, min_samples_leaf 5 | 0.849 | 0.539 | 0.887 |

Sur la v2, la forêt optimisée détecte un peu plus de pannes, au prix d'un peu plus de fausses alertes et d'un modèle beaucoup plus lourd (plusieurs Mo contre environ 2 Ko). L'écart est faible. Ces runs sont sur la v2 : on ne peut pas les comparer directement aux runs de la section 2 (v1).

## 5. Décision : l'ADR 004

Voir `docs/adr/004-choix-du-modele.md` : régression logistique, seuil 0.2, run `8c640ad3eb8d4158996b6417295104ce`, `data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15`.

## 6. Questions de compréhension

1. Git versionne le code (et les reçus `.dvc`), DVC les fichiers de données, MLflow les entraînements (paramètres, métriques, modèle et versions).
2. `--local` écrit le chemin du stockage dans `.dvc/config.local`, qui ne va pas dans Git, car c'est un dossier de mon PC. Pour partager, il faudrait un stockage commun (S3, Google Drive, serveur) déclaré sans `--local`.
3. Le code (Git et le wheel), les données (DVC) et les versions exactes (le `requirements.txt` du modèle dans MLflow). Le modèle lui-même est dans MLflow, avec l'identifiant du run.

## 7. Le rendu Git

- Lien de la pull request : …
- Le tag `tp5` existe sur GitHub : oui / non
- `mlflow.db`, `mlruns/`, `data/sensors.csv` ou `.dvc/cache` dans `git status` : non

## 8. Ce qui reste flou

Sur mon PC, Windows bloquait certains fichiers compilés (`pip.exe`, `mlflow.exe`, `dvc.exe`, SQLAlchemy, pygit2). J'ai utilisé `python -m pip`, `python -m mlflow ui` et `python -m dvc`, et `dvc init --no-scm` (avec un `.dvc/.gitignore` écrit à la main), en faisant les `git add` et `git commit` moi-même.

…
