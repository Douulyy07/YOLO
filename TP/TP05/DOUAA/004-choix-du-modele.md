# ADR 004 : choix du modèle et du seuil d'alerte de MaintAI

Date : 19/11/2026 12:00 · Auteurs : Douaa Ahmito

## Contexte
MaintAI doit prévenir avant une panne, et une panne manquée (arrêt de production, réparation en urgence) coûte beaucoup plus cher qu'une fausse alerte (un technicien qui vérifie pour rien). Il faut donc choisir le modèle et le seuil qui maximisent le **recall**, en gardant une precision acceptable, et pouvoir justifier ce choix par des runs MLflow sur une version connue des données (DVC).

## Options étudiées
Runs MLflow sur les données v1 (`data_md5 = 73e0b7cb…`, 5000 relevés, `n_train = 4000`) :

1. **Régression logistique, C = 1, seuil 0.3** (réglage par défaut) : recall 0.750, precision 0.622, accuracy 0.904. Avantages : modèle simple, léger (environ 2 Ko), explicable. Inconvénient : rate une panne sur quatre.
2. **Régression logistique, C = 0.01, seuil 0.3** : recall 0.691, precision 0.653, accuracy 0.908. Avantage : la meilleure precision. Inconvénient : le plus mauvais recall, donc le plus de pannes manquées.
3. **Régression logistique, C = 1, seuil 0.2** : recall **0.838**, precision 0.543, accuracy 0.882. Avantages : le meilleur recall sur la v1, même modèle simple et léger. Inconvénient : plus de fausses alertes.
4. **Forêt aléatoire, seuil 0.3 et 0.2** : recall 0.728 et 0.831, precision 0.562 et 0.479. Avantage : capte des relations non linéaires. Inconvénients : à seuil égal, recall et precision plus bas que la régression logistique ; modèle lourd (plusieurs Mo) et moins explicable.
5. **Grid search (au plus 25 combinaisons, validation croisée à 5 plis)**, sur la v2 (`n_train = 6400`), seuil 0.2 : régression logistique (meilleur C = 1.0) recall 0.824, precision 0.567 ; forêt (100 arbres, max_depth 10, min_samples_leaf 5) recall 0.849, precision 0.539. Avantage : réglages choisis automatiquement. Inconvénient : l'écart entre les deux modèles est faible, et la forêt reste beaucoup plus lourde.

## Décision
**Régression logistique (C = 1) avec un seuil d'alerte de 0.2** (option 3).

Raison principale : la contrainte du projet est de rater le moins de pannes possible. C'est le meilleur recall sur la v1 (84 % des pannes détectées). La forêt aléatoire n'est pas meilleure à seuil égal sur la v1, et sur la v2 son léger gain de recall (+2,5 points) ne compense pas un modèle des centaines de fois plus lourd et moins explicable. La grid search confirme d'ailleurs C = 1.0 sur la v2.

Traçabilité :
- Run MLflow : `8c640ad3eb8d4158996b6417295104ce`
- Données : `data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15` (même valeur que `data/sensors.csv.dvc` du commit `4357ee4`, « Données v1 »)
- Pour retrouver ces données : `git checkout 4357ee4 -- data/sensors.csv.dvc`, puis `dvc checkout` (ou `dvc pull`)

## Conséquences
- **Ce que cela facilite** : un modèle léger, rapide et explicable, facile à livrer (wheel du TP4) et à recharger grâce au `requirements.txt` enregistré par MLflow (`scikit-learn==1.8.0`).
- **Ce que nous acceptons en échange** : plus de fausses alertes. La precision passe de 0.62 à 0.54, soit environ une alerte sur deux qui n'est pas suivie d'une panne. L'accuracy baisse aussi (0.904 → 0.882), ce qui est secondaire ici.
- **À mettre en place** : `MAINTAI_THRESHOLD=0.2` dans la configuration de production.
- **À surveiller** : la dérive des données. Si de nouvelles données arrivent, les versionner avec DVC, ré-entraîner, comparer dans MLflow sur la même version de données, et revoir cette décision si la forêt dépasse nettement la régression logistique.