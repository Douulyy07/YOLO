# Compte rendu · TP6 : conteneuriser MaintAI (Docker, Docker Compose)

**Groupe :** …  ·  **Membres :** …  ·  **Date :** …

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP6.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP6`)

Sortie de `docker run hello-world` (première ligne) et de `docker version` (lignes Client et Server) :

```
(collez ici)
```

Dernière ligne de `python -m pytest` après la mise en place :

```
(collez ici)
```

## 2. Image et conteneur (pendant le premier build)

1. Quelle différence entre une image et un conteneur ?
   …
2. Pourquoi `COPY requirements-docker.txt` est-il placé avant `COPY maintai` ?
   …
3. Pourquoi `requirements-docker.txt` contient-il `scikit-learn==1.8.0` et pas `scikit-learn>=1.5` ?
   …
4. Pourquoi ni `mlflow`, ni `dvc`, ni `pytest` dans l'image ?
   …

## 3. Sprint 1 : le Dockerfile

Votre `Dockerfile` :

```dockerfile
(collez ici)
```

| Build | Durée | Taille de l'image (`docker images`) |
|---|---|---|
| premier build | | |
| après une modification de `maintai/predict.py` | | |

Que signifie `CACHED` dans le journal du second build ?

…

## 4. Sprint 1 : lancer un conteneur

Votre commande `docker run` :

```
(collez ici)
```

| Essai | Réponse |
|---|---|
| `GET /health` | |
| `POST /v1/predict` sans clé | |
| `POST /v1/predict` avec la clé | |

**Piège 1.** Sans l'option `-v ...models...`, que répondent `/health` et `/v1/predict` ? Pourquoi ?

…

**Piège 2.** Avec `--host 127.0.0.1`, que disent `docker logs test` et `http://localhost:8002/health` ? Pourquoi ?

…

## 5. Sprint 2 : Docker Compose

Votre `compose.yaml` :

```yaml
(collez ici)
```

Sortie de `docker compose ps` :

```
(collez ici)
```

Quelle URL affiche la barre latérale de l'interface ? D'où vient-elle ?

…

Résultat des deux commandes `docker compose exec ui ...` (avec `api` puis avec `localhost`). Pourquoi la seconde échoue-t-elle ?

```
(collez ici)
```

…

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
(collez ici)
```

## 6. Décision : l'ADR 005

Dans `docs/adr/005-image-docker.md`. Résumez ici votre décision en deux phrases :

…

## 7. Questions de compréhension

1. Qu'est-ce qui entre dans l'image, et qu'est-ce qui arrive au lancement ? Donnez le moyen pour chaque élément.
   …
2. Pourquoi la clé API n'est-elle jamais dans l'image ?
   …
3. Livrer un modèle (TP4, TP5) : qu'est-ce que Docker ajoute à la liste ?
   …

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp6` existe sur GitHub : oui / non
- `git status` avant le commit : `.env`, `models/` ou `data/*.csv` apparaissaient-ils ? oui / non

## 9. Ce qui reste flou

…
