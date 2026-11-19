# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** G1 ·  **Membres :** Mohamed Nacer Jouraai ·  **Date :** 19/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP5.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP5`)

Dernière ligne de `python -m pytest` après `pip install -r requirements.txt` et `pip install -e .` :

```
 5 failed, 27 passed
```

Quels tests échouent, et pourquoi ?

Les 5 tests de `tests/test_tracking.py` échouent. La fonction `log_run` de `maintai/tracking.py` n'est pas écrite : elle se contente de renvoyer une chaîne vide (`return ""`) et n'enregistre aucun run dans MLflow. Les tests cherchent un run (`mlflow.search_runs`), ses paramètres (`model`, `C`, `data_md5`), ses métriques (`recall`) et son modèle, et ne trouvent rien. Les 27 autres tests (ceux du TP4) passent.

Avant `pip install -e .`, où pointait le package `maintai` installé dans l'environnement ? Et après ?

Avant, le package installé dans l'environnement du TP4 était `maintai 0.2.0`, une installation éditable qui pointait vers le dossier `TP\TP4`. Après `pip install -e .` lancé dans `TP\TP5`, pip a désinstallé `maintai 0.2.0` et installé `maintai 0.3.0`, qui pointe maintenant vers `TP\TP5`. Sans cette réinstallation, le test `test_installed_version_matches_the_code` échoue, parce que la version installée (0.2.0) ne correspond pas à celle du code de TP5 (0.3.0).

Remarque : la première installation de `mlflow` et `dvc` a échoué avec `ReadTimeoutError ... files.pythonhosted.org : Read timed out` (téléchargement coupé). Il a fallu relancer `pip install --default-timeout=120 --retries 10 -r requirements.txt`.

## 2. Sprint 1 : MLflow

Votre fonction `log_run` (`maintai/tracking.py`) :

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_param("data_md5", file_md5(data_path))
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            model, name="model", input_example=X_example, skops_trusted_types=TRUSTED_TYPES
        )
    return run.info.run_id
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
 32 passed
```

Vos quatre entraînements du polycopié, relevés dans `mlflow ui` (mode « Model training », expérience `maintai`, « Runs ») :

| Commande | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | À RELEVER | À RELEVER | À RELEVER |
| `python -m maintai.train --C 0.01` | À RELEVER | À RELEVER | À RELEVER |
| `python -m maintai.train --threshold 0.2` | À RELEVER | À RELEVER | À RELEVER |
| `python -m maintai.train --model forest` | À RELEVER | À RELEVER | À RELEVER |

### Extension : recherche sur grille (25 runs)

Nous avons ajouté une option `--grid` à `maintai/train.py` : `python -m maintai.train --grid` entraîne la régression logistique pour 5 valeurs de `C` (0.001, 0.01, 0.1, 1, 10) et évalue chaque modèle à 5 seuils (0.1, 0.2, 0.3, 0.4, 0.5), soit **25 runs MLflow** (paramètre `grid = oui`). Chaque run garde aussi une métrique `f2`, une note qui compte le recall deux fois plus que la precision. La grille ne remplace pas `models/`. Les cinq meilleurs runs par `f2` (données v1) :

```
Classement par f2 (le recall compte deux fois plus que la precision) :
  C=0.1    seuil=0.1  recall=0.922  precision=0.445  f2=0.759  run=b814b73b5f1c49d9a560126b5b3cc238
  C=1.0    seuil=0.1  recall=0.907  precision=0.458  f2=0.758  run=cad769a0ec7e4404812e5164aeb4f631
  C=0.1    seuil=0.2  recall=0.829  precision=0.559  f2=0.756  run=80c75d3574884826882fd4fc0128168c
  C=1.0    seuil=0.2  recall=0.824  precision=0.567  f2=0.756  run=3e0a239243f84d67a9e75b734c9e988b
  C=10.0   seuil=0.2  recall=0.824  precision=0.567  f2=0.756  run=75d15d8cfaa846909f6708f11b4b5e82
```

Quel run choisiriez-vous pour MaintAI, et pourquoi ? (Rappel : une panne manquée coûte plus cher qu'une fausse alerte.)

Le critère principal est le **recall** (la part des vraies pannes détectées), mais pas au détriment de tout le reste. Dans la grille, les `f2` des cinq meilleurs runs sont presque égaux (0.756 à 0.759) et la valeur de `C` change peu le résultat : ce qui compte, c'est le **seuil**. Passer du seuil 0.2 au seuil 0.1 (avec `C = 1.0`) fait détecter environ 11 pannes de plus sur environ 136 dans le jeu de test (recall 0.824 vers 0.907), mais produit environ 60 fausses alertes de plus (precision 0.567 vers 0.458). Le seuil 0.1 ne vaut donc le coup que si une panne manquée coûte plus de 5 fois une fausse alerte. Faute d'estimation chiffrée du coût, nous avons retenu **`C = 1.0` et le seuil 0.2** (run `3e0a2392...`) : bon recall (0.824), sans noyer les techniciens de fausses alertes. La forêt aléatoire (`--model forest`) n'est pas meilleure : COMPLÉTER avec son recall et sa precision, comparés à la régression logistique avec le même seuil. Elle est plus complexe sans gain évident.

Limite : le classement est fait sur le même jeu de test que celui des 25 runs, donc le résultat est un peu optimiste.

Dans `mlflow ui`, ouvrez le modèle d'un run. Quelle version de scikit-learn est indiquée dans son `requirements.txt` ? Quel problème du TP4 cela règle-t-il ?

Le `requirements.txt` enregistré avec le modèle indique `scikit-learn==1.8.0` (À VÉRIFIER dans votre interface). Cela règle le problème de l'`InconsistentVersionWarning` du TP4 : on avait installé le wheel dans un environnement neuf, pip avait pris une version de scikit-learn plus récente (1.9.1) que celle qui avait écrit le modèle (1.8.0), et le modèle se relisait avec un avertissement. Maintenant, chaque run garde avec son modèle les **versions exactes** des bibliothèques : on peut recréer l'environnement qui l'a produit avant de relire le modèle.

Où MLflow enregistre-t-il les runs sur votre disque ? Ces fichiers vont-ils dans Git ? Pourquoi ?

MLflow écrit dans le dossier `TP5`, là où on lance les commandes : la base de données SQLite `mlflow.db` contient les paramètres, les métriques et les tags de chaque run, et le dossier `mlruns\` contient les artefacts (le modèle, son `requirements.txt`, etc.). Ces fichiers ne vont **pas** dans Git : le `.gitignore` les exclut (`mlflow.db`, `mlruns/`). Ce sont des fichiers locaux, qui grossissent à chaque entraînement et qui peuvent se régénérer en relançant les entraînements. Chaque membre du groupe a donc ses propres runs sur son PC.

## 3. Sprint 2 : DVC

Contenu de `data/sensors.csv.dvc` après `dvc add data/sensors.csv` :

```
outs:
- md5: 73e0b7cb3c6f795c70c3ddf970b99c15
  size: 126815
  hash: md5
  path: sensors.csv
```

Historique Git après la v1 :

```
c3baa02 (HEAD -> master) Données v1
310dc5c DVC : init
fdd98cb TP5 : starter + tracking MLflow
```

`dvc push` a affiché « 1 file pushed ».

Comparez la valeur `md5` de ce fichier au paramètre `data_md5` de votre dernier run MLflow. Que constatez-vous ?

Pour les runs entraînés sur la v1 des données, le paramètre `data_md5` est identique au `md5` du fichier `.dvc` (`73e0b7cb...`). C'est voulu : `file_md5()` de `tracking.py` calcule la même empreinte que DVC. Cela relie chaque run à une version précise des données : à partir d'un run, on lit son `data_md5`, on retrouve le commit Git qui contenait ce reçu `.dvc`, et `dvc checkout` ramène exactement les données utilisées. (À VÉRIFIER dans votre `mlflow ui`.)

Pourquoi `data/sensors.csv` ne va pas dans Git, alors que `data/sensors.csv.dvc` y va ?

Un fichier de données peut peser très lourd (100 Mo ou plus) : Git le gère mal et garde chaque version pour toujours, ce qui fait grossir le dépôt. DVC garde le fichier hors de Git, dans un cache sur le PC puis dans un stockage partagé. Dans Git, il ne met qu'un petit **reçu** (le fichier `.dvc` de quelques lignes : le md5, la taille et le chemin). Le `.gitignore` exclut `data/*.csv`, et `git add data/sensors.csv` est d'ailleurs refusé.

Après `python -m maintai.dataset --n 8000 --seed 7`, que dit `dvc status` ?

```
 modified: data\sensors.csv
```

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---|
| v1 | c3baa02 | 73e0b7cb | 5000 |
| v2 | À COMPLÉTER | À COMPLÉTER | 8000 |

Revenez à la v1 (`git checkout <commit> -- data/sensors.csv.dvc`, puis `dvc checkout`). Combien de lignes contient `data/sensors.csv` ? Puis revenez à la v2.

Après `git checkout c3baa02 -- data/sensors.csv.dvc` puis `dvc checkout`, le fichier `data/sensors.csv` contient **5000** lignes (la v1). Git a remis l'ancien reçu, et DVC a ramené depuis le cache le fichier qui lui correspond. Après `git checkout HEAD -- data/sensors.csv.dvc` puis `dvc checkout`, le fichier contient de nouveau **8000** lignes (la v2). (À VÉRIFIER avec vos propres résultats.)

Supprimez `data/sensors.csv` et le dossier `.dvc/cache`, puis lancez `dvc pull`. Que se passe-t-il ?

``
```

`dvc pull` récupère le fichier depuis le stockage (`%USERPROFILE%\dvc-stockage`) : il le télécharge d'abord dans le cache (`fetch`), puis le remet dans `data\` (`checkout`). Le fichier `data/sensors.csv` est revenu, avec 8000 lignes. C'est ce que ferait un coéquipier qui n'a pas les données : il clone le dépôt, obtient le reçu `.dvc` par Git, puis fait `dvc pull`.

## 4. Relier modèle et données

Entraînez un modèle sur la v2. Dans `mlflow ui`, comparez ce run à celui de la v1 avec les mêmes réglages :

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 (`python -m maintai.train`) | 73e0b7cb | À RELEVER | À RELEVER | À RELEVER |
| v2 (`python -m maintai.train`) | À RELEVER | À RELEVER | À RELEVER | À RELEVER |

Peut-on dire que le modèle v2 est « meilleur » ? Pourquoi faut-il être prudent en comparant deux runs entraînés sur des données différentes ?

Non, on ne peut pas conclure que le modèle v2 est meilleur, même si son recall est plus élevé. Les deux runs n'utilisent pas les mêmes données : la v2 a 8000 relevés au lieu de 5000 et vient d'une autre graine aléatoire, donc l'entraînement **et le jeu de test** sont différents. Une différence de recall peut venir du hasard de l'échantillon (le nombre de vraies pannes dans le test n'est pas le même) ou de la difficulté des données, pas de la qualité du modèle. Pour comparer deux modèles honnêtement, il faut les évaluer sur **le même jeu de test**. C'est justement ce que `data_md5` permet de contrôler : deux runs avec des `data_md5` différents ne sont pas directement comparables.

## 5. Décision : l'ADR 004

L'ADR est dans `docs/adr/004-choix-du-modele.md`.

- Modèle et seuil retenus : **régression logistique, `C = 1.0`, seuil 0.2** (recall 0.824, precision 0.567).
- Identifiant du run : `3e0a239243f84d67a9e75b734c9e988b`
- `data_md5` de la version des données utilisée : `73e0b7cb3c6f795c70c3ddf970b99c15` (v1 ; À VÉRIFIER dans `mlflow ui`)

## 6. Questions de compréhension

1. Quelle différence entre Git, DVC et MLflow ? Que versionne chacun ?

   **Git** versionne le **code** (`maintai/*.py`, tests, `pyproject.toml`, `requirements.txt`) et, pour les données, un petit reçu (`.dvc`) de quelques lignes. **DVC** versionne les **fichiers de données** : il les garde dans un cache et un stockage, hors de Git. **MLflow** garde la trace de chaque **entraînement** : paramètres, empreinte des données, métriques, et le modèle avec ses versions de bibliothèques. L'image du cours : MLflow est le cahier de manip, DVC est l'étiquette de l'échantillon.

2. Pourquoi le stockage DVC est-il ajouté avec `--local` dans ce TP ? Que faudrait-il pour que tout le groupe partage les mêmes données ?

   `--local` écrit le chemin du stockage dans `.dvc/config.local`, un fichier ignoré par Git. C'est nécessaire parce que le stockage du TP est un dossier de **mon PC** (`%USERPROFILE%\dvc-stockage`) : ce chemin n'existe pas chez les autres et ne doit pas aller dans Git. Pour que tout le groupe partage les mêmes données, il faudrait un **stockage commun et accessible à tous** (un serveur, S3, Google Drive, etc.), déclaré dans la configuration versionnée par Git, avec les identifiants de chacun gardés en local.

3. Livrer un modèle, c'est trois choses (TP4). Lesquelles, et où sont-elles maintenant ?

   Le **code**, le **modèle** et les **versions exactes**. Le code est dans Git (et le wheel du TP4). Le modèle est dans MLflow : un run, identifié par son `run_id`. Les versions exactes sont dans le `requirements.txt` enregistré avec le modèle dans MLflow. En plus, les **données** sont dans DVC : le reçu `.dvc` dans Git et le fichier dans le stockage.

