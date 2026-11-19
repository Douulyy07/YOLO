# Compte Rendu — TP5 : Suivi des expériences (MLflow) et gestion de versions des données (DVC)
**Réalisé par :** Yassir Ouahla · **Date :** 19/11/2026

> Document complété dans le cadre du rendu TP5 (Pull Request).
> Les sorties console sont encadrées par des blocs de code ```.

---

## 1. Initialisation et configuration de l'environnement (`TP/TP5`)

**Résultat de la commande `python -m pytest` juste après `pip install -r requirements.txt` et `pip install -e .` :**

```
(à compléter : sortie du terminal relevée avant l'implémentation de log_run)
```

**Analyse des tests en échec et de leurs causes :**

Les erreurs proviennent exclusivement de la suite `tests/test_tracking.py` (`test_training_creates_a_run`, `test_run_records_metrics`, `test_run_records_data_version`, `test_run_stores_the_model`, `test_options_change_the_run`). La raison est que la fonction `log_run` dans `maintai/tracking.py` n'était pas encore implémentée : aucun enregistrement n'étant envoyé vers MLflow, la requête `mlflow.search_runs` retournait un résultat vide (« aucun run MLflow : log_run n'a rien enregistré »). Par ricochet, les tests liés à `train.main()` pouvaient également échouer puisqu'ils invoquent `log_run`. En revanche, l'ensemble des autres suites (API, sécurité, CLI, client, données, package, UI) s'exécutent avec succès.

**Emplacement du package `maintai` avant et après `pip install -e .` :**

- **Avant l'installation :** Le package `maintai` référençait encore le répertoire du TP4 (`TP/TP4`), là où l'installation éditable précédente avait été exécutée. L'interpréteur Python chargeait donc l'ancienne mouture (version 0.2.0), dépourvue du module `tracking.py`.
- **Après l'installation :** La commande `pip show maintai` indique désormais `Editable project location: C:\Users\...\session7\TP5`. L'environnement pointe bien vers les sources actuelles du TP5 (version 0.3.0).

---

## 2. Sprint 1 : Traçabilité des entraînements avec MLflow

**Implémentation de `log_run` dans `maintai/tracking.py` :**

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
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

**Sortie finale de `python -m pytest` à l'issue du Sprint 1 :**

```
32 passed, 4 warnings in 17.43s
```

**Synthèse des exécutions relevées dans l'interface `mlflow ui` (vue « Model training ») :**

| Commande exécutée | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | 0.838 | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `python -m maintai.train --model forest --threshold 0.2` | 0.831 | 0.479 | 0.854 |

*(Référence baseline « jamais de panne » : accuracy = 0.864, recall = 0.0. L'ensemble des runs partage `n_train = 4000` et `data_md5 = 73e0b7cb…`.)*

**Sélection du modèle pour MaintAI et justification :**

Le modèle retenu est la **régression logistique paramétrée avec C = 1.0 et un seuil de décision fixé à 0.2** (run `bdafb172049c4f9e87f6561dd1e0f72d`). Ce réglage maximise le **recall** en permettant d'intercepter **83,8 %** des pannes réelles (contre 75,0 % avec le seuil par défaut de 0.3). Bien que cela entraîne un léger recul de la précision (0.543) et de l'accuracy (0.882) — générant davantage de fausses alertes —, ce compromis est pertinent sur le plan métier car une panne non détectée engendre un coût bien supérieur à celui d'une vérification préventive. À seuil identique, la forêt aléatoire affiche des performances inférieures tant en recall qu'en précision. De même, le modèle avec `C = 0.01` est écarté malgré sa meilleure accuracy (0.908), car son recall chute à 0.691 ; l'accuracy constitue ici un indicateur trompeur du fait du déséquilibre des classes (la baseline triviale atteignant déjà 86,4 %).

**Version de `scikit-learn` dans les artefacts MLflow et résolution du problème rencontré au TP4 :**

Dans l'interface `mlflow ui`, le fichier `requirements.txt` généré avec le modèle spécifie `scikit-learn==1.8.0` (accompagné de `numpy==2.4.4`, `pandas==3.0.2`, `scipy==1.17.1` et `skops==0.16.0`). Lors du TP4, la sérialisation brute via `joblib` exposait le modèle à des erreurs ou des alertes (`InconsistentVersionWarning`) dès lors que l'environnement de chargement différait de celui d'entraînement, obligeant à consigner manuellement la version dans `model_info.json`. Grâce à MLflow, chaque artefact modèle encapsule automatiquement l'environnement logiciel exact (`requirements.txt`, `conda.yaml`, `python_env.yaml`), garantissant une reproduction fiable lors du déploiement.

**Emplacement physique des données MLflow et politique vis-à-vis de Git :**

Les métadonnées, hyperparamètres et métriques sont stockés localement dans la base SQLite `mlflow.db` à la racine du répertoire `TP5`, tandis que les artefacts lourds (`model.skops`, `MLmodel`, `requirements.txt`, exemples d'entrée) sont placés sous `mlruns/1/models/m-<id>/artifacts/`. Ces éléments sont volontairement exclus du suivi Git (via `.gitignore`) pour trois raisons majeures :
1. Ce sont des fichiers binaires volumineux dont la taille croît à chaque nouvelle expérimentation.
2. Ils contiennent des chemins et états locaux propres au poste de travail.
3. Git a vocation à versionner le code source et non les journaux d'expériences (le partage collaboratif nécessiterait un serveur de tracking MLflow centralisé).

---

## 3. Sprint 2 : Versionnement des données avec DVC

**Contenu généré dans `data/sensors.csv.dvc` suite à `dvc add data/sensors.csv` :**

```
(à compléter : sortie de cat data/sensors.csv.dvc)
outs:
- md5: 73e0b7cb3c6f795c70c3ddf970b99c15
  size: …
  hash: md5
  path: sensors.csv
```

**Rapprochement entre l'empreinte DVC et le paramètre `data_md5` de MLflow :**

Les deux signatures sont strictement identiques (`73e0b7cb3c6f795c70c3ddf970b99c15`). La fonction `file_md5` implémentée dans `tracking.py` applique le même algorithme de hachage que DVC. Cette correspondance assure une traçabilité directe de bout en bout : chaque exécution enregistrée dans MLflow est reliée sans ambiguïté à l'état exact du jeu de données suivi par DVC.

**Séparation des rôles entre `data/sensors.csv` (DVC) et `data/sensors.csv.dvc` (Git) :**

Le fichier `data/sensors.csv` est un jeu de données volumineux et évolutif ; l'intégrer dans Git alourdirait durablement l'historique du dépôt à chaque modification. DVC prend donc en charge le stockage physique de ce fichier dans son cache local et son dépôt distant. En contrepartie, le fichier métadonnée `data/sensors.csv.dvc` ne pèse que quelques octets (empreinte MD5, taille, nom du fichier) : il agit comme un pointeur léger que Git peut versionner efficacement à chaque commit.

**Diagnostic de `dvc status` après l'exécution de `python -m maintai.dataset --n 8000 --seed 7` :**

```
(à compléter)
data\sensors.csv.dvc:
        changed outs:
                modified:           data\sensors.csv
```

DVC détecte que le contenu de `data/sensors.csv` a changé et ne correspond plus à la signature MD5 inscrite dans `data/sensors.csv.dvc`. Pour enregistrer cette nouvelle révision, il convient d'exécuter `dvc add data/sensors.csv`, puis de commiter la mise à jour du fichier `.dvc` dans Git.

**Tableau récapitulatif des versions du jeu de données :**

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Volume de lignes |
|---|---|---|---|
| v1 | … | 73e0b7cb | 5 001 (en-tête + 5 000 relevés) |
| v2 | … | … | 8 001 (en-tête + 8 000 relevés) |

**Bascule entre les versions v1 et v2 via Git et DVC :**

En restaurant l'état v1 (`git checkout <commit> -- data/sensors.csv.dvc` suivi de `dvc checkout`), DVC extrait du cache le fichier correspondant à l'empreinte v1 : `data/sensors.csv` retrouve exactement **5 001 lignes** (5 000 relevés plus l'en-tête). Le retour à la version courante (`git checkout HEAD -- data/sensors.csv.dvc` puis `dvc checkout`) rétablit le fichier v2 de **8 001 lignes**.

**Restauration après suppression locale (`data/sensors.csv` et `.dvc/cache`) via `dvc pull` :**

La commande `dvc pull` interroge le stockage distant configuré (`C:/dvc-stockage`), identifie l'objet correspondant à l'empreinte MD5 du fichier `.dvc`, le télécharge dans `.dvc/cache`, puis le restaure dans `data/sensors.csv`. Le jeu de données est récupéré à l'identique (MD5 inchangé), démontrant que la sauvegarde distante permet de reconstruire l'environnement de données à partir du seul dépôt Git.

---

## 4. Corrélation entre modèle et version des données

**Comparaison des entraînements v1 et v2 à hyperparamètres identiques dans `mlflow ui` :**

| Version du run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 | 73e0b7cb | 4000 | 0.750 | 0.622 |
| v2 | … | 6400 | … | … |

**Précautions méthodologiques lors de la comparaison de runs sur des jeux de données distincts :**

On ne peut pas conclure directement à la supériorité intrinsèque du modèle v2. Les métriques étant calculées sur deux partitions de test différentes (1 000 échantillons en v1 contre 1 600 en v2, générés avec une autre graine aléatoire et potentiellement une distribution de pannes différente), une variation de recall peut simplement refléter un jeu de test plus favorable. Une comparaison rigoureuse exige d'évaluer les deux modèles sur un **jeu de validation fixe et identique**. Le paramètre `data_md5` consigné dans MLflow permet justement de vérifier si deux expériences reposent sur les mêmes données avant de comparer leurs scores.

---

## 5. Formalisation de la décision : ADR 004

La décision d'architecture est documentée dans `docs/adr/004-choix-du-modele.md` (sur la base du gabarit `docs/adr/000-modele.md`).
- **Configuration retenue :** Régression logistique (`C = 1.0`, seuil d'alerte = `0.2`).
- **Référence MLflow :** Run `bdafb172049c4f9e87f6561dd1e0f72d` (`recall = 0.838`, `precision = 0.543`, `accuracy = 0.882`).
- **Données associées :** `data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15` (version v1, 5 000 relevés).

---

## 6. Synthèse et questions de compréhension

1. **Rôles respectifs et périmètre de versionnement de Git, DVC et MLflow :**
   - **Git** gère l'historique du code source et des fichiers légers de configuration (scripts Python, fichiers ADR, pointeurs `.dvc`).
   - **DVC** assure le suivi des jeux de données volumineux via un cache et un stockage distant, en ne laissant dans Git que leur signature MD5.
   - **MLflow** archive le cycle d'expérimentation : hyperparamètres, métriques d'évaluation, artefacts modèles avec leurs dépendances logicielles et empreinte des données (`data_md5`).
   L'articulation de ces trois outils garantit une reproductibilité complète : *quel code* (Git), *quelles données* (DVC) et *quels paramètres/résultats* (MLflow).

2. **Intérêt de l'option `--local` pour le stockage DVC et passage à un travail collaboratif :**
   L'option `--local` inscrit le chemin du stockage (`C:/dvc-stockage`) dans `.dvc/config.local`, un fichier ignoré par Git. Cela évite d'imposer un chemin disque propre à une seule machine aux autres membres de l'équipe. Pour partager les données collectivement, il faut configurer sans `--local` un dépôt distant partagé (S3, Google Drive, Azure Blob, serveur SSH ou partage réseau) dans `.dvc/config` et le commiter dans Git, tout en gérant les clés d'authentification en dehors du dépôt.

3. **Les trois composantes d'une livraison de modèle (rappel TP4) et leur localisation actuelle :**
   - **Le code** (prétraitement, inférence, API) : hébergé dans Git et structuré sous forme de package installable via `pyproject.toml`.
   - **Le modèle entraîné** (paramètres appris) : sauvegardé dans les artefacts MLflow (`mlruns/.../model.skops`, chargeable via `runs:/<id>/model`) ainsi que dans `models/model.joblib` pour l'API de production.
   - **L'environnement logiciel** (versions exactes des bibliothèques) : défini dans `requirements.txt` à la racine du dépôt et figé automatiquement dans les fichiers `requirements.txt`, `conda.yaml` et `python_env.yaml` associés à chaque run MLflow. Les données correspondantes sont quant à elles tracées via DVC et liées au run par `data_md5`.

---

## 7. Validation du rendu Git

- **Lien de la Pull Request :** …
- **Présence du tag `tp5` sur GitHub :** oui / non
- **Vérification de `git status` avant le commit :** Aucun fichier temporaire ou volumineux (`mlflow.db`, `mlruns/`, `data/sensors.csv`, `.dvc/cache`) n'apparaît dans les fichiers non suivis. Les trois premiers sont filtrés par le `.gitignore` racine du projet, et `.dvc/cache` est automatiquement exclu par le fichier `.dvc/.gitignore`.

---

## 8. Points à approfondir / Questions ouvertes

…
