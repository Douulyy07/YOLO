# Compte rendu · TP6 : conteneuriser MaintAI (Docker, Docker Compose)

**Groupe :** G1  ·  **Membres :** Mohamed Nacer Jouraai  ·  **Date :** 26/11/2026 à 10h44

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP6.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP6`)

Sortie de `docker run hello-world` (première ligne) et de `docker version` (lignes Client et Server) :

```
Hello from Docker!
This message shows that your installation appears to be working correctly.

(docker version : COLLER ICI les lignes Client et Server de la commande docker version)
```

Dernière ligne de `python -m pytest` après la mise en place :

```
(COLLER ICI la dernière ligne du premier pytest : attendu 5 failed, 33 passed)
```

L'image de départ a été téléchargée une fois (`docker pull python:3.11-slim`, « Downloaded newer image »).

## 2. Image et conteneur (pendant le premier build)

1. Quelle différence entre une image et un conteneur ?

   Une **image** est le paquet figé et nommé (`maintai:0.4.0`) : le système, Python, les bibliothèques et le code, produit par `docker build` à partir du Dockerfile. Elle ne tourne pas. Un **conteneur** est une copie de cette image **qui tourne** (`docker run`), isolée, avec ses propres fichiers, son réseau et ses processus. On peut lancer autant de conteneurs qu'on veut à partir d'une même image (ici `api` et `ui`). Analogie du cours : l'image est la carte moulée, le conteneur est la carte sous tension.

2. Pourquoi `COPY requirements-docker.txt` est-il placé avant `COPY maintai` ?

   Chaque instruction du Dockerfile crée une **couche**, et Docker réutilise (`CACHED`) toutes les couches jusqu'à la première qui change. L'installation des bibliothèques (`pip install`) est lente et change rarement ; le code change souvent. En copiant d'abord seulement `requirements-docker.txt`, puis en installant, cette étape lente reste en cache tant que la liste ne change pas. Si on copiait le code avant, la moindre modification d'une ligne de code invaliderait la couche et relancerait tout le `pip install`.

3. Pourquoi `requirements-docker.txt` contient-il `scikit-learn==1.8.0` et pas `scikit-learn>=1.5` ?

   Un modèle doit être relu avec la version de scikit-learn qui l'a écrit (`models/model_info.json` garde `sklearn_version`). Avec `>=1.5`, pip installerait la dernière version, différente de celle de l'entraînement, ce qui provoque l'`InconsistentVersionWarning` vu au TP4 (modèle écrit en 1.8.0, relu en 1.9.1) et un risque de résultats faux. `==` fige la version et garantit que l'image relit le modèle comme il a été écrit.

4. Pourquoi ni `mlflow`, ni `dvc`, ni `pytest` dans l'image ?

   L'image sert seulement à **servir** MaintAI (API et interface), pas à entraîner, versionner ou tester. MLflow et DVC sont de gros paquets : les ajouter alourdirait l'image, ralentirait le build et agrandirait la surface d'attaque, pour rien. `pytest` est un outil de test qu'on lance sur le PC.

## 3. Sprint 1 : le Dockerfile

Votre `Dockerfile` :

```dockerfile
# Image de MaintAI : le code et ses bibliothèques, sans les données ni le modèle.
# Construire : docker build -t maintai:0.4.0 .

FROM python:3.11-slim

WORKDIR /app

# Les bibliothèques d'abord : cette étape lente reste en cache tant que requirements-docker.txt ne change pas
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Le code ensuite : il change souvent, donc il vient en dernier
COPY maintai ./maintai
COPY ui ./ui

# Où le modèle et les données seront montés au lancement (volumes)
ENV MAINTAI_MODELS_DIR=/app/models \
    MAINTAI_DATA_PATH=/app/data/sensors.csv

EXPOSE 8000
CMD ["uvicorn", "maintai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore` (ajouts) : `data/`, `models/`, `.env`, `mlflow.db`, `mlruns/`, `.dvc/`.

| Build | Durée | Taille de l'image (`docker images`) |
|---|---|---|
| premier build | plusieurs minutes (le `pip install` télécharge pandas, scikit-learn, streamlit...) | (COLLER ICI la taille de `docker images`) |
| après une modification du code (`docker compose up --build`) | 1,3 s | identique |

Que signifie `CACHED` dans le journal du second build ?

Docker a reconnu que cette couche n'a pas changé depuis le build précédent et la **réutilise** au lieu de la refaire. Dans notre journal, les étapes `WORKDIR`, `COPY requirements-docker.txt`, `RUN pip install` et `COPY maintai` sont `CACHED`; seule `COPY ui` a été refaite, parce que `ui/app.py` avait changé. Le `pip install`, la partie lente, n'a donc pas été relancé.

## 4. Sprint 1 : lancer un conteneur

Votre commande `docker run` :

```
docker run -d --name maintai-api -p 8000:8000 --env-file .env -v "%cd%\models:/app/models:ro" maintai:0.4.0
```

| Essai | Réponse |
|---|---|
| `GET /health` | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict` sans clé | HTTP 401, `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict` avec la clé | HTTP 200, `{"failure_probability":0.9475,"alert":true,"threshold":0.3,"model_version":"2026-11-26T10:33:45Z"}` |

Essai supplémentaire : avec `releve.json` (température 500, hors limite), l'API répond HTTP 422 (`Input should be less than or equal to 150`).

**Piège 1.** Sans l'option `-v ...models...`, que répondent `/health` et `/v1/predict` ? Pourquoi ?

Sans le volume, l'API démarre mais **ne trouve pas le modèle** : `/health` indique `"model_loaded":false`, et `/v1/predict` (avec la bonne clé) répond HTTP 503 : `{"detail":"Modèle non chargé : lancez python -m maintai.train puis redémarrez l'API"}`. La raison : l'image ne contient que le code et les bibliothèques ; le modèle est volontairement dehors et arrive au lancement par le volume.

**Piège 2.** Avec `--host 127.0.0.1`, que disent `docker logs test` et `http://localhost:8002/health` ? Pourquoi ?

`docker logs test` affiche que tout va bien : `Uvicorn running on http://127.0.0.1:8000`. Mais `curl http://localhost:8002/health` échoue : `curl: (52) Empty reply from server`. Dans un conteneur, `127.0.0.1` veut dire « ce conteneur seulement » : uvicorn n'écoute que sur l'interface interne et refuse ce que Docker relie depuis le PC. Avec `0.0.0.0` (« toutes les interfaces »), y compris celle que Docker relie au port publié, l'API est joignable.

## 5. Sprint 2 : Docker Compose

Votre `compose.yaml` :

```yaml
# MaintAI en deux conteneurs : l'API et l'interface Streamlit.
# Lancer : docker compose up --build      Arrêter : docker compose down

services:
  api:
    build: .
    image: maintai:0.4.0
    env_file: .env                     # MAINTAI_API_KEY, comme au TP2
    ports:
      - "8000:8000"                    # PC:conteneur
    volumes:
      - ./models:/app/models:ro        # le modèle vient du PC, en lecture seule

  ui:
    image: maintai:0.4.0               # la même image que l'API, avec une autre commande
    command: ["python", "-m", "streamlit", "run", "ui/app.py",
              "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
    environment:
      MAINTAI_API_URL: http://api:8000 # l'API vue depuis ce conteneur : le nom du service
    ports:
      - "8501:8501"                    # PC:conteneur
    volumes:
      - ./data:/app/data:ro            # les données du PC, en lecture seule
    depends_on:
      - api
```

Sortie de `docker compose ps` :

```
NAME        IMAGE           COMMAND                  SERVICE   CREATED         STATUS         PORTS
tp6-api-1   maintai:0.4.0   "uvicorn maintai.api…"   api       5 seconds ago   Up 4 seconds   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
tp6-ui-1    maintai:0.4.0   "python -m streamlit…"   ui        5 seconds ago   Up 4 seconds   0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
```

Quelle URL affiche la barre latérale de l'interface ? D'où vient-elle ?

La barre latérale affiche `http://api:8000`. Elle vient de la variable d'environnement `MAINTAI_API_URL`, définie dans `compose.yaml` pour le service `ui`, et lue par `ui/app.py` avec `os.getenv("MAINTAI_API_URL", "http://localhost:8000")`. Hors Docker, la variable n'existe pas et l'interface garde `http://localhost:8000`. Depuis l'interface, après saisie de la clé, l'onglet « Prédiction » donne environ 95 % et l'alerte (comme l'API : 0.9475).

Résultat des deux commandes `docker compose exec ui ...` (avec `api` puis avec `localhost`). Pourquoi la seconde échoue-t-elle ?

```
> docker compose exec ui python -c "import httpx; print(httpx.get('http://api:8000/health').text)"
{"status":"ok","model_loaded":true}

> docker compose exec ui python -c "import httpx; print(httpx.get('http://localhost:8000/health').text)"
httpcore.ConnectError: [Errno 111] Connection refused
httpx.ConnectError: [Errno 111] Connection refused
```

Compose place les services sur un même réseau (`tp6_default`), où chacun se joint par **son nom** : `api` désigne le conteneur de l'API. Dans le conteneur `ui`, `localhost` veut dire « ce conteneur-ci », et il n'y a pas d'API dedans : la connexion est refusée. Dans notre navigateur, `http://localhost:8000` marche parce que le navigateur est sur le PC, où Docker relie le port 8000 du PC à l'API.

`docker compose down` a affiché :

```
 ✔ Container tp6-ui-1  Removed
 ✔ Container tp6-api-1 Removed
 ✔ Network tp6_default Removed
```
Elle supprime les **conteneurs** et le **réseau** créés par Compose. Elle ne supprime pas l'image `maintai:0.4.0` (elle sert au prochain `docker compose up`) ni les fichiers du PC (`models/`, `data/`).

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
=========================================================== 38 passed, 4 warnings in 32.97s ============================================================
```

## 6. Décision : l'ADR 005

Dans `docs/adr/005-image-docker.md`. Résumez ici votre décision en deux phrases :

Le modèle n'est pas dans l'image : il arrive au lancement par un volume en lecture seule (`./models:/app/models:ro`), parce qu'il change sans nouveau code (ré-entraînement, MLflow, DVC). Le `.dockerignore` laisse dehors les données, le modèle, le secret `.env`, MLflow et DVC : la clé arrive par `env_file`, jamais dans l'image.

## 7. Questions de compréhension

1. Qu'est-ce qui entre dans l'image, et qu'est-ce qui arrive au lancement ? Donnez le moyen pour chaque élément.

   **Dans l'image** (`docker build`) : le système Linux et Python 3.11 (`FROM python:3.11-slim`), les bibliothèques de `requirements-docker.txt` (`RUN pip install`), et le code `maintai/` et `ui/` (`COPY`). **Au lancement**, hors de l'image : le **modèle** `models/` (volume `-v ./models:/app/models:ro`), les **données** `data/` pour l'interface (volume `./data:/app/data:ro`), et la **clé API** `.env` (`--env-file .env` ou `env_file: .env`). L'URL de l'API pour l'interface arrive aussi au lancement, par la variable `MAINTAI_API_URL`.

2. Pourquoi la clé API n'est-elle jamais dans l'image ?

   Une image se partage (registre, serveur, collègue) : tout ce qu'elle contient est lisible par quiconque la reçoit, même en supprimant un fichier dans une couche ultérieure. Un secret dans l'image est donc un secret exposé. La clé est donc donnée au conteneur **au lancement** (`--env-file`), et `.env` est dans `.dockerignore` et dans `.gitignore`. Cela permet aussi de changer la clé sans reconstruire l'image (en recréant le conteneur).

3. Livrer un modèle (TP4, TP5) : qu'est-ce que Docker ajoute à la liste ?

   Au TP4 : le code (wheel), le modèle (`models/`) et les versions exactes. Au TP5 : les données (DVC) et le run MLflow. Docker ajoute **le système et l'environnement d'exécution complets** : Python, les bibliothèques en versions figées et le code, emballés dans une image qui tourne de la même façon sur tout PC ou serveur où Docker est installé. Il règle le « ça marche chez moi » : plus besoin de préparer un `.venv`. Le modèle et les données restent livrés à part, par volume.

## 8. Le rendu Git

- Lien de la pull request : À COMPLÉTER
- Le tag `tp6` existe sur GitHub : À COMPLÉTER (oui / non)
- `git status` avant le commit : `.env`, `models/` ou `data/*.csv` apparaissaient-ils ? À COMPLÉTER (oui / non)

## 9. Ce qui reste flou

À COMPLÉTER avec vos propres mots (par exemple : la différence entre un volume `-v` et `COPY`, ou le rôle exact de `depends_on`).
