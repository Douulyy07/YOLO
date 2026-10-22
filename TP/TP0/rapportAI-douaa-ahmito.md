# TP : MaintAI et CantineAI

**Nom :** Douaa Ahmito · **Groupe :** G1

---

# Partie 1 : MaintAI

## Le problème

Prédire une panne à partir de 4 capteurs (température, vibration, charge, heures de fonctionnement) ; une panne manquée arrête une ligne.

## Résultats sur le jeu de test

| Modèle | Accuracy | Rappel | Précision |
|---|---|---|---|
| baseline | 0.824 | 0.000 | 0.000 |
| logistic | 0.839 | 0.847 | 0.527 |
| gradient_boosting | 0.888 | 0.608 | 0.713 |
| knn | 0.878 | 0.540 | 0.699 |
| random_forest | 0.882 | 0.540 | 0.720 |

## Mon choix, et pourquoi

Je retiens la régression logistique. Une panne manquée coûte une journée d'arrêt de ligne, contre une heure d'inspection pour une fausse alerte : le rappel est donc la métrique qui compte, pas l'accuracy. La baseline (ne jamais prédire de panne) a une accuracy de 0.824, mais un rappel de 0 : elle ne détecte aucune panne.

La régression logistique a le meilleur rappel (0.847, soit 84,7 % des pannes détectées), loin devant gradient boosting (0.608), knn et random forest (0.540). Elle a en revanche la plus faible accuracy (0.839) et la plus faible précision (0.527) parmi les modèles : environ une alerte sur deux est une fausse alerte. Ce coût est acceptable, car une fausse alerte coûte une heure d'inspection alors qu'une panne manquée coûte une journée.

## Le critère (rappel ≥ 0,75) est-il atteint ?

Oui, uniquement par la régression logistique : 0.847, soit 0.097 au-dessus du seuil de 0.75. Gradient boosting (0.608), knn (0.540) et random forest (0.540) ne l'atteignent pas, malgré une meilleure précision et une meilleure accuracy.

## Ce qui reste flou

- Si les modèles non linéaires (gradient boosting, random forest) atteindraient 0.75 de rappel en baissant leur seuil de décision (0.5 par défaut), et quelle précision ils garderaient.
- Le vrai rapport de coût entre panne manquée et fausse alerte : il fixerait le bon équilibre entre rappel et précision, et dirait si une précision de 0.527 est tolérable en pratique.
- La fiabilité d'un seul découpage test : le résultat pourrait varier avec une validation croisée.
- L'effet de `class_weight="balanced"` sur la régression logistique.
- Les données sont synthétiques : les performances en usine réelle peuvent différer.

---

# Partie 2 : CantineAI

## Le problème

Prédire le nombre de repas à commander pour le lendemain à partir de l'effectif inscrit, du menu, de la météo prévue, du calendrier (examens, sorties, veille de vacances) et des repas de la semaine précédente. Un repas en trop coûte environ 15 DH et du gaspillage ; un repas manquant laisse un élève sans déjeuner.

## Résultats sur le jeu de test

Découpage chronologique : les 20 % de jours les plus récents sont gardés pour le test.

| Modèle | MAE (repas) | RMSE (repas) | R² |
|---|---|---|---|
| baseline (`repas_semaine_precedente`) | 70.271 | 88.416 | -0.151 |
| régression linéaire / Ridge | 22.377 | 28.315 | 0.882 |
| gradient_boosting | 29.852 | 37.727 | 0.790 |
| random_forest | 31.825 | 41.647 | 0.745 |
| knn | 40.274 | 49.450 | 0.640 |

## Mon choix, et pourquoi

Je retiens la régression linéaire / Ridge. Elle a la plus faible MAE (22.4 repas), la plus faible RMSE et le meilleur R² (0.882) de tous les modèles. La MAE est la métrique principale car elle s'exprime en nombre de repas, donc lisible par le gestionnaire et directement liée au coût (environ 15 DH par repas en excédent).

La baseline, qui reprend la méthode actuelle du gestionnaire, se trompe en moyenne de 70 repas, et son R² est négatif : elle fait moins bien qu'une prédiction constante égale à la moyenne. Un modèle simple et linéaire bat aussi les modèles plus complexes, ce qui est cohérent avec seulement 340 jours de données.

## Le critère (MAE ≤ 20 repas et au moins 20 % meilleure que la baseline) est-il atteint ?

Non, partiellement.
- MAE du modèle sur le jeu de test : 22.377 repas, donc **au-dessus** du seuil de 20 (écart de 2.4 repas).
- MAE de la baseline : 70.271 repas.
- Amélioration relative : (70.271 − 22.377) / 70.271 = **68,2 %**, donc la condition des 20 % est largement satisfaite.

Le modèle est bien meilleur que la méthode actuelle, mais la condition MAE ≤ 20 n'est pas remplie.

## Ce qui reste flou

- Si on peut passer sous 20 repas de MAE en améliorant le modèle : réglage de `alpha` avec `RidgeCV`, encodage de `jour` et `menu`, variables tirées de `date` (mois), imputation des valeurs vides de `repas_semaine_precedente`.
- Si le seuil de 20 repas est le bon : c'est une proposition de départ, et un écart de 2.4 repas (environ 36 DH par jour si c'est un excédent) pourrait être acceptable pour le gestionnaire.
- Le coût réel d'un repas manquant n'est pas chiffré, alors que celui d'un excédent l'est (15 DH) : l'erreur n'est pas symétrique, donc la MAE seule masque la différence.
- Avec 340 jours, le jeu de test ne contient qu'environ 68 jours, donc le résultat est sensible à la période choisie.
- Les données sont synthétiques : les performances réelles peuvent différer.