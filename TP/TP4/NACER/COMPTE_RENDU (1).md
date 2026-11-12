# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** À COMPLÉTER  ·  **Membres :** À COMPLÉTER  ·  **Date :** 12/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP4.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
COLLER ICI la dernière ligne de pytest (attendu : 2 failed, 25 passed)
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux tests de `tests/test_package.py` échouent : `test_installed_version_matches_the_code` et `test_command_is_declared`. Le package `maintai` n'est pas encore installé dans l'environnement : `importlib.metadata.version("maintai")` ne trouve aucune installation, et la commande `maintai-predict` n'est déclarée nulle part (`entry_points` ne la contient pas). Les autres tests passent parce que `pytest` ajoute le dossier du projet à la liste où Python cherche les modules, donc `import maintai` fonctionne depuis le dossier, sans installation.

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

`dependencies` ne contient que ce dont le code de `maintai/` a besoin pour fonctionner, quel que soit l'usage : numpy (`dataset.py`), pandas (`data.py`, `predict.py`), scikit-learn (`train.py`), joblib (`predict.py`, `train.py`) et httpx (`client.py`). `pytest` sert seulement à tester le projet : il est dans le groupe optionnel `dev`. `fastapi` ne sert que pour faire tourner l'API : il est dans le groupe `api` (et `streamlit` dans `ui`). Ainsi, quelqu'un qui veut seulement la commande `maintai-predict` n'installe pas tout cela.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
COLLER ICI les 4 premières lignes de pip show maintai (Name: maintai, Version: 0.2.0, ...)
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
COLLER ICI la dernière ligne de pytest (attendu : 27 passed)
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

```
COLLER ICI les deux sorties (attendu : "Probabilité de panne : 95 % (ALERTE)", puis un chemin ...\TP\TP4\maintai\__init__.py)
```

La commande fonctionne même depuis un autre dossier, et `maintai.__file__` pointe vers `...\TP4\maintai\__init__.py`. Python trouve le code grâce à l'installation éditable : pip a placé dans `.venv\Lib\site-packages` un lien vers le dossier `TP4`, donc `maintai` est trouvé partout, quel que soit le dossier courant.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Oui, le changement est visible immédiatement, sans réinstaller. L'installation éditable (`pip install -e .`) ne copie pas le code : elle crée un lien vers le dossier `TP4`. Chaque lancement relit donc le fichier `maintai/cli.py` modifié.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```
COLLER ICI la sortie de dir dist (maintai-0.2.0-py3-none-any.whl et maintai-0.2.0.tar.gz)
```

Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?

```
COLLER ICI la sortie de tar -tf (maintai/__init__.py, cli.py, client.py, config.py, data.py, dataset.py, predict.py, train.py, maintai/api/..., maintai-0.2.0.dist-info/...)
```

Le wheel ne contient **ni le modèle (`models/`), ni les tests, ni `ui/`**. Il contient seulement le dossier `maintai/` (le code) et les métadonnées (`dist-info`, dont `entry_points.txt` qui déclare la commande). La raison est `[tool.setuptools.packages.find]` avec `include = ["maintai*"]` : seul le dossier `maintai/` entre dans le package. Les tests et l'interface n'ont pas besoin d'être livrés, et le modèle n'est pas du code Python.

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : C:\Users\medna\AppData\Local\Temp\essai\.venv\Lib\site-packages\models\model.joblib` puis `Entraînez-le (python -m maintai.train) ou indiquez son dossier dans MAINTAI_MODELS_DIR.` |
| avec `MAINTAI_MODELS_DIR` vers vos `models` | 3 avertissements `InconsistentVersionWarning` (StandardScaler, LogisticRegression, Pipeline : « from version 1.8.0 when using version 1.9.1 »), puis `Probabilité de panne : 95 % (ALERTE)` |
| après `pip install scikit-learn==1.8.0` | `Probabilité de panne : 95 % (ALERTE)`, sans avertissement |

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

Le modèle a été entraîné et sauvegardé avec scikit-learn 1.8.0 (la version de `requirements.txt` dans le `.venv` du TP4). Dans l'environnement neuf, `pip install` du wheel a installé la **dernière** version de scikit-learn (1.9.1), car `pyproject.toml` demande seulement `scikit-learn>=1.5` (« au moins »). Quand scikit-learn relit le fichier `model.joblib`, il voit que la version qui l'a écrit (1.8.0) n'est pas celle qui le lit (1.9.1) et prévient que le résultat peut être faux. La ligne `"sklearn_version": "1.8.0"` de `models/model_info.json` donne la version qui a écrit le modèle. En installant exactement `scikit-learn==1.8.0`, l'avertissement disparaît.

## 4. Questions de compréhension

1. Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?

   `requirements.txt` fixe des versions **exactes** (`==`) : il décrit l'environnement précis dans lequel le projet et son modèle fonctionnent, pour le reproduire à l'identique. `dependencies` donne des versions **minimales** (`>=`) : elle décrit ce dont le package a besoin pour s'installer à côté d'autres bibliothèques, sans conflit. Un modèle doit être relu avec la version qui l'a écrit, d'où le besoin de livrer aussi les versions exactes.

2. Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?

   `pip install -e .` (éditable) pose un **lien** vers le dossier du projet : les modifications du code sont visibles tout de suite, sans réinstaller. On l'utilise pendant le développement. L'installation du wheel fait une **copie** du code dans `site-packages` : modifier le dossier `TP4` ne change plus rien, il faut reconstruire et réinstaller. On l'utilise pour livrer le package à quelqu'un d'autre.

3. Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?

   Un point d'entrée relie un nom de commande à une fonction Python : `maintai-predict = "maintai.cli:main"` veut dire « la commande `maintai-predict` appelle la fonction `main` du module `maintai.cli` ». À l'installation, pip crée un petit exécutable `maintai-predict.exe` dans le dossier `Scripts` de l'environnement (`.venv\Scripts`).

## 5. Le rendu Git

- Lien de la pull request : À COMPLÉTER
- Le tag `tp4` existe sur GitHub : À COMPLÉTER (oui / non)
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? À COMPLÉTER (oui / non)

## 6. Ce qui reste flou

À COMPLÉTER avec vos propres mots (par exemple : la différence entre installation éditable et wheel, ou pourquoi le dossier `models` est cherché dans `site-packages`).
