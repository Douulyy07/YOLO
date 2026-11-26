# Compte rendu · TP6 : conteneuriser MaintAI (Docker, Docker Compose)

**Groupe :** …  ·  **Membres :** …  ·  **Date :** …

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP6.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP6`)

Sortie de `docker run hello-world` (première ligne) et de `docker version` (lignes Client et Server) :

```
Hello from Docker!
This message shows that your installation appears to be working correctly.

Client:
 Version:           29.8.2

Server: Docker Desktop 4.95.0 (242831)
 Engine:
  Version:          29.8.2 
```

Dernière ligne de `python -m pytest` après la mise en place :

```
5 failed, 33 passed, 4 warnings in 39.79s
```

## 2. Image et conteneur (pendant le premier build)

1. Quelle différence entre une image et un conteneur ?
   L'image est le paquet figé construit à partir du Dockerfile (système, Python, bibliothèques, code). Le conteneur est une copie de l'image qui tourne, isolée (ses fichiers, son réseau). Une image peut lancer plusieurs conteneurs.
2. Pourquoi `COPY requirements-docker.txt` est-il placé avant `COPY maintai` ?
   Chaque instruction crée une couche, et Docker réutilise les couches jusqu'à la première qui change. Les bibliothèques (installation lente, changent rarement) passent avant le code (change souvent) : modifier le code ne relance pas `pip install`.
3. Pourquoi `requirements-docker.txt` contient-il `scikit-learn==1.8.0` et pas `scikit-learn>=1.5` ?
   Le modèle a été enregistré avec scikit-learn 1.8.0. Avec `>=1.5`, pip installerait la dernière version et on aurait le problème du TP4 (`InconsistentVersionWarning`). `==` rend l'image reproductible.
4. Pourquoi ni `mlflow`, ni `dvc`, ni `pytest` dans l'image ?
   L'image sert le modèle, elle n'entraîne pas et ne teste pas. Ces outils alourdiraient l'image sans servir.

## 3. Sprint 1 : le Dockerfile

Votre `Dockerfile` :

```dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY maintai ./maintai
COPY ui ./ui

ENV MAINTAI_MODELS_DIR=/app/models \
    MAINTAI_DATA_PATH=/app/data/sensors.csv

EXPOSE 8000
CMD ["uvicorn", "maintai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Build | Durée | Taille de l'image (`docker images`) |
|---|---|---|
| premier build | 5 min | 1.13GB |
| après une modification de `maintai/predict.py` | 10s | 1.13GB |

Que signifie `CACHED` dans le journal du second build ?
Docker réutilise une couche déjà construite au lieu de refaire l'étape. Au second build, `FROM`, `COPY requirements-docker.txt` et `RUN pip install` sont `CACHED` ; seules les couches à partir de `COPY maintai` sont refaites.

## 4. Sprint 1 : lancer un conteneur

Votre commande `docker run` :

```
docker run -d --name maintai-api -p 8000:8000 --env-file .env -v "${PWD}\models:/app/models:ro" maintai:0.4.0
```

| Essai | Réponse |
|---|---|
| `GET /health` | {
  "status": "string",
  "model_loaded": true
} |
| `POST /v1/predict` sans clé | 401 |
| `POST /v1/predict` avec la clé | {
  "failure_probability": 0.9553,
  "alert": true,
  "threshold": 0.3,
  "model_version": "2026-11-26T21:43:12Z"
} |

**Piège 1.** Sans l'option `-v ...models...`, que répondent `/health` et `/v1/predict` ? Pourquoi ?

`/health` répond `{"status":"ok","model_loaded":false}` et `/v1/predict` répond **503** `Modèle non chargé`.

**Piège 2.** Avec `--host 127.0.0.1`, que disent `docker logs test` et `http://localhost:8002/health` ? Pourquoi ?

`docker logs test` affiche `Uvicorn running on http://127.0.0.1:8000`, mais `http://localhost:8002/health` ne répond pas. Dans un conteneur, `127.0.0.1` veut dire « ce conteneur seulement » : les requêtes qui arrivent du PC par `-p` ne sont pas acceptées. Il faut écouter sur `0.0.0.0`.

## 5. Sprint 2 : Docker Compose

Votre `compose.yaml` :

```yaml
services:
  api:
    build: .
    image: maintai:0.4.0
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models:ro

  ui:
    image: maintai:0.4.0
    command: ["python", "-m", "streamlit", "run", "ui/app.py",
              "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
    environment:
      MAINTAI_API_URL: http://api:8000
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data:ro
    depends_on:
      - api
```

Sortie de `docker compose ps` :

```
NAME        IMAGE           COMMAND                  SERVICE   CREATED         STATUS         PORTS
tp6-api-1   maintai:0.4.0   "uvicorn maintai.api…"   api       2 minutes ago   Up 2 minutes   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
tp6-ui-1    maintai:0.4.0   "python -m streamlit…"   ui        2 minutes ago   Up 2 minutes   0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
```

Quelle URL affiche la barre latérale de l'interface ? D'où vient-elle ?

** `http://api:8000`. Elle vient de la variable `MAINTAI_API_URL` définie dans `compose.yaml`, lue par `os.getenv` dans `ui/app.py`. La prédiction fonctionne avec la clé de `.env`.

Résultat des deux commandes `docker compose exec ui ...` (avec `api` puis avec `localhost`). Pourquoi la seconde échoue-t-elle ?

```
avec `api`:{"status":"ok","model_loaded":true}
avec `localhost`:httpcore.ConnectError: [Errno 111] Connection refused

La seconde échoue car, dans le conteneur `ui`, `localhost` désigne le conteneur `ui` lui-même, où il n'y a pas d'API. Depuis le navigateur, `localhost:8000` marche car c'est le PC, et Docker relie son port 8000 au conteneur `api`. Entre conteneurs, on utilise le nom du service (`api`).
```

…

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
38 passed, 4 warnings in 39.44s 
```

## 6. Décision : l'ADR 005

Dans `docs/adr/005-image-docker.md`. Résumez ici votre décision en deux phrases :

Le modèle arrive par un volume en lecture seule, pour changer de modèle sans reconstruire l'image. `.dockerignore` laisse dehors ce qui est lourd, local ou secret (données, modèle, `.env`, MLflow, DVC, `.venv`) : la clé arrive avec `--env-file`, le modèle et les données par des volumes.

## 7. Questions de compréhension

1. Qu'est-ce qui entre dans l'image, et qu'est-ce qui arrive au lancement ? Donnez le moyen pour chaque élément.
   Dans l'image (`docker build`) : Linux, Python 3.11, les bibliothèques (`requirements-docker.txt`), `maintai/` et `ui/`. Au lancement : le modèle (`-v ./models`), les données (`-v ./data`) et la clé (`--env-file .env`).
2. Pourquoi la clé API n'est-elle jamais dans l'image ?
   Une image se partage (registre, collègues) et quiconque l'a peut lire ce qu'elle contient. Une clé dedans serait publique, et changer la clé obligerait à reconstruire l'image.
3. Livrer un modèle (TP4, TP5) : qu'est-ce que Docker ajoute à la liste ?
   Avant : le code (wheel), le modèle, les données (DVC) et les versions (`requirements.txt` de MLflow). Docker ajoute l'environnement complet (système et Python) : on livre l'image, plus le modèle et la clé au lancement.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp6` existe sur GitHub : oui / non
- `git status` avant le commit : `.env`, `models/` ou `data/*.csv` apparaissaient-ils ? oui / non

## 9. Ce qui reste flou

…
