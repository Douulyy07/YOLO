# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** G1 ·  **Membres :** DOUAA AHMITO  ·  **Date :** 12/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP4.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
2 failed, 25 passed
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux tests de tests/test_package.py échouent : maintai n'est pas encore installé comme package, donc pip ne connaît ni sa version ni la commande maintai-predict.

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

dependencies ne contient que ce dont le code de maintai/ a besoin pour fonctionner. pytest ne sert qu'aux tests (groupe dev), fastapi seulement à l'API (groupe api) : on les installe à la demande.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
Name: maintai
Version: 0.2.0
Summary: Prédiction de panne de machines à partir de relevés de capteurs
Home-page:
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
27 passed, 1 warning in 5.68s
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

Depuis un autre dossier : maintai-predict 72 6 85 15000 affiche Probabilité de panne : 95 % (ALERTE), et maintai.__file__ donne ...\TP\TP4\maintai\__init__.py. Python trouve le code dans mon dossier TP4, grâce au lien posé par pip install -e ..

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Modification de cli.py sans réinstaller : le changement est visible tout de suite. Avec -e (installation éditable), pip installe un lien vers mon dossier, pas une copie.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```
maintai-0.2.0-py3-none-any.whl
maintai-0.2.0.tar.gz
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

Ni le modèle, ni les tests, ni ui/ : packages.find n'inclut que le dossier maintai/. Le wheel contient seulement le code.
```

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | Modèle introuvable : ...\essai\.venv\Lib\site-packages\models\model.joblib|
| avec `MAINTAI_MODELS_DIR` vers vos `models` |InconsistentVersionWarning: Trying to unpickle estimator ... from version 1.8.0 when using version 1.9.1, puis Probabilité de panne : 95 % (ALERTE) |
| après `pip install scikit-learn==1.8.0` |Probabilité de panne : 95 % (ALERTE), sans avertissement |

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

InconsistentVersionWarning : le modèle a été enregistré avec scikit-learn 1.8.0, mais le wheel a installé la dernière version (car >=1.5). La ligne "sklearn_version": "1.8.0" de model_info.json l'explique.

## 4. Questions de compréhension

1. Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?
   requirements.txt fixe des versions exactes (==) pour reproduire mon environnement. dependencies donne des versions minimales (>=) pour que le package s'installe à côté d'autres.
2. Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?
   pip install -e . installe un lien vers mon dossier (pour développer). Le wheel installe une copie du code (pour livrer) : modifier TP4 ne la change plus.
3. Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?
   Un point d'entrée relie une commande à une fonction (maintai-predict → maintai.cli:main). pip crée maintai-predict.exe dans .venv\Scripts.
   
## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : oui / non
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? oui / non

## 6. Ce qui reste flou

…
