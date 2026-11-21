# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** G1  ·  **Membres :** Yassir Ouahla  ·  **Date :** 21/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP4.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
========================= 2 failed, 25 passed in 1.84s =========================
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux tests qui échouent se trouvent dans `tests/test_package.py` :
- `test_installed_version_matches_the_code` : l'appel à `importlib.metadata.version("maintai")` lève une exception `PackageNotFoundError` car `maintai` est uniquement présent sous forme de dossier source et n'a pas encore été installé comme package dans l'environnement virtuel `.venv` (aucun dossier `.dist-info` n'existe dans `site-packages`).
- `test_command_is_declared` : l'inspection des points d'entrée `entry_points(group="console_scripts")` ne trouve pas `maintai-predict`, car `pip install -e .` n'a pas encore été exécuté pour enregistrer les métadonnées déclarées dans `pyproject.toml`.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Vos sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "numpy>=2.0",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "joblib>=1.4",
    "httpx>=0.27",
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?

La section `dependencies` ne doit lister que les bibliothèques strictement nécessaires au fonctionnement de base du package (`maintai.predict`, `maintai.cli`, `maintai.client`, `maintai.train`). `pytest` est un outil réservé au développement et à l'exécution des tests (placé dans `[project.optional-dependencies] dev`), tandis que `fastapi` (avec `uvicorn`) n'est utile que lorsqu'on souhaite exposer le service via l'API HTTP (placé dans `[project.optional-dependencies] api`). Cela évite d'alourdir l'installation pour un utilisateur qui souhaite seulement utiliser la commande CLI `maintai-predict` ou le module Python de prédiction.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
Name: maintai
Version: 0.2.0
Summary: Prédiction de panne de machines à partir de relevés de capteurs
Home-page:
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
============================== 27 passed in 1.76s ==============================
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

- La commande `maintai-predict 72 6 85 15000` affiche :
  `Probabilité de panne : 95 % (ALERTE)`
- La commande `python -c "import maintai; print(maintai.__file__)"` affiche :
  `C:\Users\Administrator\Desktop\TP4\maintai\__init__.py`
- Python trouve le code directement dans le répertoire de travail du projet (`TP4\maintai\`) même lorsqu'on exécute la commande depuis `%TEMP%`, car `pip install -e .` a créé dans `.venv\Lib\site-packages\` un fichier de liaison éditable (`__editable__.maintai-0.2.0.pth` associé à son *finder*) qui pointe vers le dossier source du projet.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Oui, le changement apparaît immédiatement dès l'appel suivant de `maintai-predict`, sans avoir besoin de relancer `pip install`. Comme le package est installé en mode éditable (`-e`), les fichiers `.py` n'ont pas été copiés dans `site-packages` : Python importe directement `maintai/cli.py` depuis le dossier source du dépôt à chaque exécution.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```
 Volume in drive C has no label.
 Volume Serial Number is 3CC2-B805

 Directory of C:\Users\Administrator\Desktop\TP4\dist

11/20/2026  09:22 PM    <DIR>          .
11/20/2026  09:22 PM    <DIR>          ..
11/20/2026  09:22 PM            11,622 maintai-0.2.0-py3-none-any.whl
11/20/2026  09:22 PM            12,262 maintai-0.2.0.tar.gz
               2 File(s)         23,884 bytes
               2 Dir(s)  178,916,966,400 bytes free
```

Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?

```
maintai/__init__.py
maintai/cli.py
maintai/client.py
maintai/config.py
maintai/data.py
maintai/dataset.py
maintai/predict.py
maintai/train.py
maintai/api/__init__.py
maintai/api/main.py
maintai/api/schemas.py
maintai/api/security.py
maintai-0.2.0.dist-info/METADATA
maintai-0.2.0.dist-info/WHEEL
maintai-0.2.0.dist-info/entry_points.txt
maintai-0.2.0.dist-info/top_level.txt
maintai-0.2.0.dist-info/RECORD
```

Non, ni le modèle (`models/`), ni les tests (`tests/`), ni le dossier `ui/` ne sont présents dans l'archive `.whl`. Dans `pyproject.toml`, la section `[tool.setuptools.packages.find]` spécifie `include = ["maintai*"]`, ce qui indique à `setuptools` de n'embarquer que le package Python `maintai` (et son sous-package `maintai.api`). C'est une bonne pratique : le wheel distribue uniquement le code applicatif réutilisable, tandis que le modèle binaire entraîné (`model.joblib`) a son propre cycle de vie et est fourni séparément en déploiement (via `MAINTAI_MODELS_DIR`).

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : C:\...\Temp\essai\Lib\site-packages\models\model.joblib`<br>`Entraînez-le (python -m maintai.train) ou indiquez son dossier dans MAINTAI_MODELS_DIR.` |
| avec `MAINTAI_MODELS_DIR` vers vos `models` | `InconsistentVersionWarning: Trying to unserialize estimator StandardScaler from version 1.8.0 when using version ...` (puis idem pour `LogisticRegression` et `Pipeline`), suivi de :<br>`Probabilité de panne : 95 % (ALERTE)` |
| après `pip install scikit-learn==1.8.0` | `Probabilité de panne : 95 % (ALERTE)` (sans aucun avertissement) |

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

Lorsqu'on installe le wheel dans un environnement neuf, `pip` résout la dépendance ouverte `scikit-learn>=1.5` de `pyproject.toml` et installe la version disponible dans cet environnement, qui peut différer de celle ayant servi à sauvegarder `model.joblib`. Au moment où `joblib.load()` désérialise le pipeline, `scikit-learn` compare sa version courante avec celle enregistrée dans l'objet pickle et émet `InconsistentVersionWarning` car la représentation interne d'un estimateur n'est garantie compatible qu'à version exacte identique.
La ligne de `models/model_info.json` qui permet de connaître la version exacte utilisée à l'entraînement est la ligne 11 :
`"sklearn_version": "1.8.0"`

## 4. Questions de compréhension

1. Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?
   `dependencies` dans `pyproject.toml` définit les dépendances abstraites du package avec des plages de versions minimales compatibles (`>=`), afin que la bibliothèque puisse s'installer aux côtés d'autres packages sans créer de conflits bloquants. À l'inverse, `requirements.txt` fige un environnement d'exécution reproductible avec des versions exactes (`==`, comme `scikit-learn==1.8.0`) et inclut tous les outils de l'environnement de travail (API, interface Streamlit, tests, packaging).
2. Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?
   `pip install -e .` réalise une installation **éditable** destinée au développement : elle place un lien dans `site-packages` pointant vers le dossier source du projet, de sorte que toute modification du code est active immédiatement. À l'inverse, `pip install dist\maintai-0.2.0-py3-none-any.whl` réalise une installation **standard figée** à partir de l'archive construite : les fichiers du package sont copiés dans `.venv\Lib\site-packages\maintai\`, indépendamment du dossier source initial.
3. Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?
   Un point d'entrée `[project.scripts]` associe un nom de commande système (`maintai-predict`) à une fonction Python précise (`module:fonction`, ici `maintai.cli:main`). Lors de l'installation du package sous Windows, `pip` génère automatiquement un exécutable lanceur `maintai-predict.exe` dans le dossier `.venv\Scripts\` de l'environnement virtuel actif (qui figure dans le `PATH` une fois l'environnement activé).

## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : oui
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? non (car `dist/`, `build/` et `*.egg-info/` sont ignorés dans `.gitignore`)

## 6. Ce qui reste flou

L'articulation en production entre le déploiement du code applicatif (via le fichier `.whl`) et la synchronisation de l'artefact modèle (`model.joblib` + `model_info.json`) lorsqu'une nouvelle version de `scikit-learn` nécessite un ré-entraînement du modèle.
