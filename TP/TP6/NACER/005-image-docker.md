# ADR 005 : Le modèle arrive par un volume, pas dans l'image Docker

Date : 26/11/2026 · Auteurs : Mohamed Nacer Jouraai (G1)

## Contexte
MaintAI doit pouvoir tourner sur un serveur où personne ne prépare de `.venv`, avec les mêmes versions de bibliothèques que sur nos PC. Une image Docker emballe le système, Python, les bibliothèques et le code. Deux contraintes du projet pèsent sur ce qu'on y met : le modèle et les données changent sans nouveau code (séances 5 et 7 : ré-entraînement, nouvelles versions DVC), et l'API est protégée par une clé qui ne doit jamais sortir de nos mains.

## Options étudiées
**Décision 1 : où met-on le modèle ?**
1. **Le modèle dans l'image** (`COPY models ./models`) :
   - Ce que cette option ferait gagner : une image autonome, qui tourne avec une seule commande `docker run`, sans volume à penser ; le modèle et le code voyagent ensemble, donc impossible d'oublier le modèle (pas de 503 « Modèle non chargé »).
   - Ce qu'elle ferait perdre : il faut reconstruire et republier l'image à chaque ré-entraînement, même si le code n'a pas changé ; l'image grossit avec chaque modèle ; le modèle est figé dans l'image, donc plus difficile à remplacer ou à retirer.
2. **Le modèle monté par un volume au lancement** (`-v ./models:/app/models:ro`) :
   - Ce que cette option ferait gagner : une image légère et stable, qui change seulement quand le code ou les bibliothèques changent ; on change de modèle (un autre run MLflow, une autre version des données) sans reconstruire ; la même image sert pour tous les modèles.
   - Ce qu'elle ferait perdre : il faut penser au volume : sans lui, l'API démarre mais répond `"model_loaded":false` puis 503 (nous l'avons vérifié) ; il y a deux choses à livrer (l'image et le dossier `models/`) au lieu d'une.

**Décision 2 : qu'est-ce que `.dockerignore` laisse dehors ?**
1. **Tout copier dans l'image** (données, modèle, `.env`, MLflow, DVC, `.venv`) :
   - Ce que cette option ferait gagner : zéro configuration, l'image contient tout ce qu'il faut pour fonctionner ailleurs.
   - Ce qu'elle ferait perdre : la clé API et d'autres secrets seraient dans l'image, donc visibles par quiconque la reçoit ; l'image deviendrait énorme (`.venv`, `mlruns/`, `mlflow.db`, cache DVC) et le build plus lent ; des données potentiellement sensibles voyageraient avec.
2. **Laisser dehors** `.venv/`, `data/`, `models/`, `.env`, `mlflow.db`, `mlruns/`, `.dvc/`, `tests/`, `.git/` et les caches :
   - Ce que cette option ferait gagner : un secret qui n'entre jamais dans l'image (la clé arrive par `--env-file` ou `env_file:`) ; une image petite et reconstruite vite ; données et modèle qui restent sous le contrôle de DVC et de MLflow.
   - Ce qu'elle ferait perdre : l'image ne suffit pas seule ; il faut fournir la clé, le modèle et, pour l'interface, les données au lancement ; pas de tests dans l'image (on les lance sur le PC).

## Décision
Nous retenons **le modèle par un volume** (option 2 de la décision 1) et **un `.dockerignore` qui laisse dehors** les données, le modèle, le secret, les fichiers MLflow et DVC, l'environnement virtuel, les tests et le dépôt Git (option 2 de la décision 2). La raison principale est la contrainte du MLOps : le modèle et les données changent sans nouveau code, donc ils ne doivent pas être figés dans l'image ; et le secret n'entre jamais dans une image qu'on peut partager. L'image ne contient que le code (`maintai/`, `ui/`) et les bibliothèques de `requirements-docker.txt`, avec `scikit-learn==1.8.0`, la version qui a écrit le modèle.

## Conséquences
- **Ce que cette décision facilite** : ré-entraîner et changer de modèle sans reconstruire l'image ; builds rapides grâce au cache des couches (la 2e construction, après un changement de code, a pris environ 1,3 s) ; une image sans secret, qu'on peut partager ; le même démarrage partout avec `docker compose up`.
- **Ce qu'elle rend plus difficile** : il faut penser au volume `./models:/app/models:ro` (sans lui, 503) et à `--env-file .env` (sans lui, l'API n'a pas de clé) ; la clé est lue au démarrage du conteneur, donc modifier `.env` impose de recréer le conteneur ; le dossier `models/` doit arriver sur le serveur par un autre moyen (MLflow, copie, stockage partagé).
- **Ce qu'il faudra surveiller** : la version de scikit-learn de l'image doit rester celle du modèle (sinon `InconsistentVersionWarning`, voir TP4) ; la lecture seule (`:ro`) protège le modèle ; la liste de `.dockerignore` doit suivre l'ajout de nouveaux fichiers locaux ; `docker compose up` suppose un `.env` présent, hors de Git.
