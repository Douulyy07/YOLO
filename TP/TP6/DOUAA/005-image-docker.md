# ADR 005 : contenu de l'image Docker de MaintAI

Date : 26/11/2026 · Auteurs : Douaa Ahmito

## Contexte
MaintAI doit tourner sur un serveur où personne ne prépare de `.venv`. On l'emballe dans une image Docker (`maintai:0.4.0`) qui sert l'API et l'interface. Il faut décider ce qui entre dans l'image et ce qui arrive au lancement, sachant qu'une image se partage (registre, collègues) et que le modèle et les données changent plus souvent que le code (MLflow, DVC).

## Décision 1 : le modèle dans l'image, ou par un volume ?

### Options étudiées
1. **Volume** (`-v ./models:/app/models:ro`) : on change de modèle sans reconstruire l'image, une même image sert plusieurs modèles, et l'image reste plus légère. Inconvénient : si on oublie le volume, l'API démarre sans modèle (`model_loaded: false`, puis 503).
2. **Dans l'image** (`COPY models ./models`) : l'image est complète et autonome, impossible d'oublier le modèle. Inconvénients : chaque nouveau modèle oblige à reconstruire et redistribuer l'image ; on mélange le cycle du code et celui du modèle ; un modèle lourd (forêt : plusieurs Mo) alourdit chaque version.

### Décision
**Le modèle arrive par un volume, en lecture seule.** Le modèle change sans nouveau code (ré-entraînement, nouvelle version des données) : il suit son propre cycle (MLflow, DVC), comme le wheel du TP4 qui portait le code sans le modèle.

**Ce que l'autre option ferait gagner :** une image autonome, sans risque d'oubli du volume. **Ce qu'elle ferait perdre :** il faudrait reconstruire l'image à chaque nouveau modèle.

## Décision 2 : ce que `.dockerignore` laisse dehors

### Options étudiées
1. **Exclure** `.venv/`, `data/`, `models/`, `.env`, `mlflow.db`, `mlruns/`, `.dvc/`, `tests/`, `.git/` et les caches : image plus légère et build plus rapide (moins de fichiers envoyés à Docker), aucun secret dans l'image, pas de dépendance à mon PC (`.venv` Windows inutilisable sous Linux).
2. **Tout copier** : rien à écrire, mais l'image contiendrait la clé API (`.env`), les données, les runs MLflow et un `.venv` Windows inutile ; elle serait lourde et dangereuse à partager.

### Décision
**Exclure tout ce qui est lourd, local ou secret.** La clé arrive au lancement (`--env-file .env`), le modèle et les données par des volumes. Les outils d'entraînement (MLflow, DVC, pytest) ne sont ni copiés ni installés : l'image sert, elle n'entraîne pas.

**Ce que l'autre option ferait gagner :** un Dockerfile un peu plus simple. **Ce qu'elle ferait perdre :** la sécurité (secret dans une image partageable), la taille et la vitesse du build.

## Conséquences
- **Ce que cela facilite :** une image légère, partageable sans risque, qui tourne pareil sur tout PC et serveur ; un nouveau modèle se déploie en remplaçant `models/` et en redémarrant le conteneur.
- **Ce que cela rend plus difficile :** il faut toujours fournir le volume `models` et le fichier `.env` au lancement (Compose s'en charge).
- **À surveiller :** le modèle monté doit avoir été entraîné avec la même version de scikit-learn que l'image (`scikit-learn==1.8.0` dans `requirements-docker.txt`) ; mettre à jour les deux ensemble.
