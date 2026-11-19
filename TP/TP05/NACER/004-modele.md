# ADR 004 : Choix du modèle et du seuil d'alerte pour MaintAI

Date : 19/11/2026 12:00 · Auteurs : Mohamed Nacer Jouraai

## Contexte
MaintAI prédit la panne d'une machine à partir de relevés de capteurs (température, vibration, charge, heures de fonctionnement), et le technicien de maintenance décide d'intervenir quand la probabilité dépasse un seuil. Une panne manquée coûte plus cher qu'une fausse alerte (arrêt de production, réparation en urgence), donc la contrainte du projet est de **détecter le plus de pannes possible** : le critère principal est le **recall**, la precision passe en second. Les entraînements sont enregistrés dans MLflow (expérience `maintai`) et reliés à leurs données par DVC : le choix s'appuie sur des chiffres comparables, sur des données connues.

## Options étudiées
Nous avons lancé une **recherche sur grille** (`python -m maintai.train --grid`) : 5 valeurs de `C` (0.001, 0.01, 0.1, 1, 10) × 5 seuils (0.1, 0.2, 0.3, 0.4, 0.5), soit **25 runs MLflow** (paramètre `grid = oui`), tous sur la **v1 des données** (5000 relevés). Nous les avons classés par `f2`, une note qui compte le recall deux fois plus que la precision. Les cinq meilleurs :

| Option | C | seuil | recall | precision | f2 | run MLflow |
|---|---|---|---|---|---|---|
| A | 0.1 | 0.1 | 0.922 | 0.445 | 0.759 | b814b73b5f1c49d9a560126b5b3cc238 |
| B | 1.0 | 0.1 | 0.907 | 0.458 | 0.758 | cad769a0ec7e4404812e5164aeb4f631 |
| C | 0.1 | 0.2 | 0.829 | 0.559 | 0.756 | 80c75d3574884826882fd4fc0128168c |
| D | 1.0 | 0.2 | 0.824 | 0.567 | 0.756 | 3e0a239243f84d67a9e75b734c9e988b |
| E | 10.0 | 0.2 | 0.824 | 0.567 | 0.756 | 75d15d8cfaa846909f6708f11b4b5e82 |

Observations :
- Les `f2` des cinq options sont presque égaux (0.756 à 0.759) : la note ne les départage pas. Les valeurs de `C` entre 0.1 et 10 donnent des résultats presque identiques, donc `C` compte peu ici.
- Ce qui change vraiment le résultat, c'est le **seuil**. Passer du seuil 0.2 au seuil 0.1 (avec `C = 1.0`, options D et B) fait gagner environ 11 pannes détectées sur environ 136 dans le jeu de test (recall 0.824 vers 0.907), mais produit environ 60 fausses alertes de plus (precision 0.567 vers 0.458). Le seuil 0.1 est donc préférable seulement si une panne manquée coûte plus de 5 fois une fausse alerte (60 / 11 ≈ 5,5).
- La forêt aléatoire (`--model forest`) a aussi été essayée au sprint 1 : modèle plus complexe et plus lourd à entraîner, sans gain de recall par rapport à la régression logistique avec un seuil plus bas. Nous ne l'avons pas retenue.

## Décision
Nous retenons la **régression logistique avec `C = 1.0` (valeur par défaut) et le seuil 0.2** (option D), de recall 0.824 et de precision 0.567. La raison est la contrainte du projet : détecter le plus de pannes possible, sans que les techniciens soient noyés de fausses alertes. Nous ne disposons pas d'une estimation chiffrée du coût d'une panne manquée ; sans raison de penser qu'il dépasse 5 fois celui d'une fausse alerte, le seuil 0.2 est le compromis le plus prudent. `C = 1.0` est préféré à `C = 0.1` : l'écart de recall est négligeable (0.005), et la valeur par défaut est plus simple à justifier.

- **Identifiant du run MLflow retenu** : `3e0a239243f84d67a9e75b734c9e988b`
- **`data_md5` des données utilisées** : `73e0b7cb3c6f795c70c3ddf970b99c15` (v1, 5000 relevés ; commit Git « Données v1 » : `c3baa02`) (À VÉRIFIER dans `mlflow ui` : le paramètre `data_md5` de ce run)

Pour retrouver ces données : `git checkout c3baa02 -- data/sensors.csv.dvc`, puis `dvc checkout` (ou `dvc pull` sur un autre PC). Pour installer ce modèle dans `models/` : `python -m maintai.train --C 1.0 --threshold 0.2`.

**Alternative si le groupe estime qu'une panne manquée coûte beaucoup plus cher** (plus de 5 fois une fausse alerte) : option B (`C = 1.0`, seuil 0.1, run `cad769a0ec7e4404812e5164aeb4f631`), de recall 0.907.

## Conséquences
- **Ce que la décision facilite** : plus de pannes détectées avant qu'elles arrivent, avec un choix traçable : le run MLflow donne les réglages, les métriques et le modèle avec ses versions exactes de bibliothèques, et le `data_md5` permet de retrouver les données exactes avec DVC.
- **Ce que nous acceptons en échange** : environ 43 % des alertes seront de fausses alertes (precision 0.567), donc des interventions inutiles pour les techniciens. Si les fausses alertes sont trop nombreuses, les techniciens risquent de moins prendre les alertes au sérieux.
- **Une limite de la méthode** : nous avons choisi la combinaison qui marche le mieux **sur le même jeu de test** que celui utilisé pour comparer les 25 runs. Le chiffre est donc un peu optimiste. Une vraie validation garderait un troisième jeu de données (validation croisée ou jeu de test à part) pour la décision finale.
- **Une limite sur les données** : le run entraîné sur la v2 des données (8000 relevés, autre graine) n'est pas directement comparable à ceux de la v1, parce que le jeu de test n'est pas le même.
- **Ce qu'il faudra surveiller** : la proportion de fausses alertes et le coût réel des interventions, pour réajuster le seuil. Le modèle peut aussi se dégrader si les données changent (dérive des données) : il faudra ré-entraîner sur des données connues et versionnées avec DVC.
- **À mettre en cohérence** : le seuil retenu (0.2) doit être appliqué par l'API et par `maintai-predict` (variable `MAINTAI_THRESHOLD` et fichier `models/model_info.json` produit par l'entraînement).