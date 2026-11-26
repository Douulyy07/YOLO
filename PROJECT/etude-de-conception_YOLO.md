# Étude de conception – Comptage de véhicules par vision (YOLO pré-entraîné)
Groupe : DOUAA AHMITO, MOHAMED NACER JOURAAI, YASSIR OUAHLA · Version : finale · Date : 26/11/2026

## 1. Contexte et utilisateurs

- **Organisation ou situation :** le service mobilité d'une commune, ou le gestionnaire d'une voirie, qui veut connaître le trafic sur un axe pour régler les feux, ouvrir ou fermer des voies et planifier des travaux. Aujourd'hui, le comptage se fait à la main (un agent compte pendant quelques heures, une ou deux fois par an) ou avec des boucles magnétiques enterrées, chères à poser et difficiles à déplacer. Résultat : peu de données, souvent anciennes, et rarement séparées par type de véhicule.
- **Utilisateur principal (un rôle précis) :** l'ingénieur trafic de la commune. Il connaît la circulation, pas le deep learning. Il veut ouvrir un tableau de bord et lire des chiffres, pas lancer un script.

**Cadre que nous nous fixons.** Nous travaillons sur un jeu de données public de vidéos de trafic (section 4), filmées par des caméras fixes placées en hauteur au-dessus de routes urbaines, avec un plan large. Notre cible est le jour et le temps sec. La nuit et la pluie sont mesurées mais sans critère bloquant (sections 5 et 9). Nous utilisons un détecteur YOLO déjà entraîné, sans le réentraîner dans la version de base : le travail porte sur l'application complète (détection, suivi, comptage, évaluation, stockage, tableau de bord).

**Un usage type.** L'agent choisit une vidéo de la route, trace une ligne de comptage sur une image de la scène, puis lance le traitement. Le système compte ensuite les véhicules qui franchissent la ligne, par type et par sens, et enregistre un total par minute. Chaque matin, l'ingénieur ouvre le tableau de bord, compare avec la veille et la semaine précédente, et exporte un fichier CSV une fois par semaine pour son rapport. Si le traitement s'arrête, l'administrateur reçoit une alerte.

## 2. Problème et décision

- **Décision que l'utilisateur prend avec le système :** adapter la gestion du trafic selon les volumes mesurés : durée des phases de feux, ouverture d'une voie supplémentaire, choix des créneaux de travaux, justification d'un aménagement (voie de bus, rond-point).
- **Fréquence :** consultation du tableau de bord une fois par jour, rapport hebdomadaire avec export CSV, alerte si le traitement s'arrête. Les décisions d'aménagement, elles, tombent quelques fois par an et s'appuient sur plusieurs semaines de données.
- **Conséquence d'une erreur, et pour qui :**

| Erreur | Cause probable | Conséquence | Pour qui |
|---|---|---|---|
| Sous-comptage | Véhicule caché derrière un autre, camion non détecté, identifiant perdu avant la ligne | Trafic sous-estimé, feu ou voie mal dimensionné, embouteillage non anticipé | Usagers, commune |
| Sur-comptage | Même véhicule compté deux fois, piéton ou panneau pris pour un véhicule, ligne mal placée | Investissement inutile, mauvaise priorité donnée à un axe | Budget de la commune |
| Mauvais type | Bus classé camion, moto non vue, utilitaire classé voiture | Statistiques par catégorie fausses (poids lourds, transport collectif) | Ingénieur trafic |
| Panne silencieuse | Ligne décalée, cadrage modifié ou traitement arrêté sans que personne ne le voie | Plusieurs jours de données fausses | Tous |

La gravité reste moyenne : quelques pourcents d'erreur ne changent pas une décision, un biais systématique de plus de 20 % peut la changer. Le système aide à décider, il ne sert pas de preuve et ne verbalise personne.

**Ce que le système doit faire**

- F1. Lire une séquence vidéo (fichier ou suite d'images).
- F2. Détecter voitures, motos, bus et poids lourds ou utilitaires.
- F3. Suivre chaque véhicule avec un identifiant stable.
- F4. Compter les franchissements d'une ligne virtuelle, par type et par sens.
- F5. Enregistrer les comptages par minute dans une base SQLite et les exporter en CSV.
- F6. Afficher un tableau de bord : totaux, courbe par heure, comparaison entre jours.
- F7. Régler la ligne, la zone d'intérêt et les seuils sans toucher au code.
- F8. Prévenir si le traitement s'arrête ou si le comptage reste anormalement à zéro.
- F9. Rejouer une séquence vidéo et comparer le résultat au comptage de référence (pour l'évaluation).
- F10. Marquer une plage horaire comme invalide (cadrage modifié, panne), avec trace de la correction.

**Contraintes**

- N1. Au moins 15 images par seconde traitées sur la machine cible (on peut ne traiter qu'une image sur deux).
- N2. Erreur de comptage inférieure à 10 % sur le total des séquences de test (voir section 5).
- N3. Aucune image ni plaque conservée en fonctionnement normal, seulement des compteurs.
- N4. Résultats reproductibles : versions des bibliothèques figées, graine fixée, évaluation lancée par un script.
- N5. Reprise du traitement après une interruption, sans perdre les comptages déjà enregistrés.

## 3. Approche par sous-problème

| Sous-problème | Approche (règles / ML / DL / LLM / RAG) | Pourquoi pas une approche plus simple |
|---|---|---|
| Détection des véhicules | DL : détecteur YOLO pré-entraîné sur COCO (YOLO26 d'Ultralytics, YOLO11 en repli), classes `car`, `motorcycle`, `bus`, `truck`. Nous comparons les tailles nano et small | La soustraction d'arrière-plan (OpenCV) réagit aux ombres et aux changements de lumière, ne donne pas le type et fusionne les véhicules proches. Entraîner un détecteur de zéro demanderait des milliers d'images annotées et un GPU |
| Suivi des véhicules | Algorithme de suivi ByteTrack (filtre de Kalman et association par IoU), comparé à BoT-SORT | Sans suivi, un même véhicule serait compté des dizaines de fois, une fois par image. Un simple « plus proche voisin » perd l'identité dès qu'un véhicule est caché quelques images |
| Comptage | Règles : test géométrique de franchissement d'une ligne, un identifiant ne compte qu'une fois | Rien à apprendre ici : c'est déterministe, on peut le vérifier à la main et le tester. Du ML ajouterait de l'incertitude pour rien |
| Zone de comptage | Règles : polygone d'intérêt et taille minimale des boîtes | Sans zone, les véhicules des voies voisines ou très éloignés faussent les totaux |
| Réglage (seuil de confiance, position de la ligne) | Essais sur des séquences de réglage séparées des séquences de test | Les valeurs par défaut dépendent de l'angle et de la hauteur de la caméra |
| Adaptation du modèle (seulement si besoin) | DL : fine-tuning sur 300 à 1 000 images tirées du jeu de données public | Coûteux en annotation, donc déclenché uniquement si les critères de la section 5 ne sont pas atteints |
| Restitution | Application web Streamlit et export CSV | Un fichier de log ne serait pas lisible pour l'ingénieur trafic |

**Échelle de décision appliquée.** Pour chaque sous-problème, nous sommes partis de la solution la plus simple et nous ne montons que si elle échoue. Le comptage reste au niveau des règles, parce qu'une ligne et un test géométrique suffisent. Le suivi passe au niveau algorithmique (Kalman et association), parce que de simples règles de distance perdent les véhicules cachés. La détection est le seul vrai besoin de DL, car aucune règle ni aucun modèle classique ne reconnaît un véhicule dans une image, et nous prenons un modèle déjà entraîné pour ne pas payer l'entraînement. Le fine-tuning n'est tenté que si les critères échouent.

Nous n'utilisons ni LLM ni RAG, aucun besoin de texte ou de documents ne le justifie. Nous ne faisons pas non plus de lecture de plaques, qui serait intrusive et hors sujet.

### 3.1 Comment le comptage fonctionne

Pour chaque image, le détecteur donne des boîtes avec leur type, le suivi leur attache un identifiant, puis :

```text
pour chaque véhicule suivi (id, boîte, type) :
    p = milieu du bord bas de la boîte          # point de contact avec la route
    si p est hors de la zone d'intérêt : on ignore
    si on connaît la position précédente q de cet id, et qu'il n'est pas déjà compté :
        si le segment [q, p] coupe la ligne [A, B] :
            sens = signe du produit vectoriel (B - A) x (p - q)
            compteur[type][sens] += 1
            on marque l'id comme compté
    position précédente de l'id = p
```

On prend le bord bas de la boîte plutôt que son centre, parce qu'il est plus proche du sol et dépend moins de la hauteur du véhicule. Le sens vient du signe du produit vectoriel, ce qui donne deux compteurs (aller et retour). Comme chaque identifiant n'est compté qu'une fois, un véhicule arrêté sur la ligne ne compte pas deux fois. Chaque passage est horodaté, ce qui nous permet plus tard de comparer passage par passage avec le comptage de référence. Les cas qui restent difficiles sont les véhicules cachés (le suivi garde la trace environ 30 images), les changements d'identifiant (nous les mesurons) et les véhicules collés l'un à l'autre (limite connue).

Ultralytics propose aussi un compteur prêt à l'emploi (`ObjectCounter`). Nous l'utiliserons comme point de comparaison, mais nous écrivons notre propre logique pour maîtriser l'anti-doublon, la zone d'intérêt et l'export des passages.

## 4. Données

Nous avons choisi le jeu de données UA-DETRAC, parce qu'il correspond à notre cas : des caméras fixes en hauteur sur des routes urbaines, des véhicules annotés image par image avec leur trajectoire et leur type, et des séquences étiquetées par conditions d'éclairage (nuageux, nuit, ensoleillé, pluvieux). Cela nous permet d'évaluer le comptage sans compter à la main des heures de vidéo.

| Jeu de données | Source et licence | Volume | Données personnelles ? |
|---|---|---|---|
| UA-DETRAC (vidéos de trafic annotées) | Benchmark public de l'université d'Albany (Wen et al., CVIU 2020), mis à disposition par ses auteurs. La page du jeu de données n'indique pas de licence précise et demande seulement de citer l'article, ce que nous faisons | 100 séquences vidéo (plus de 10 heures de trafic, 24 lieux), plus de 140 000 images annotées, 8 250 véhicules, 1,21 million de boîtes | Oui, possible : plaques et visages peuvent apparaître dans les images, même si ce n'est pas notre objet |
| Poids YOLO pré-entraînés | Ultralytics, sous AGPL-3.0 (usage académique) ou licence entreprise. Entraînés sur COCO (annotations CC BY 4.0, images soumises aux conditions Flickr d'origine) | Modèle nano ou small, 80 classes dont 4 utiles | Les images COCO contiennent des personnes, mais cela ne change rien pour notre usage |
| Comptage de référence | Calculé par nous à partir des annotations d'UA-DETRAC (voir ci-dessous) | Un fichier par séquence : instant, type et sens de chaque passage | Non |
| Images pour le fine-tuning (si besoin) | Extraites d'UA-DETRAC, annotations déjà fournies | 300 à 1 000 images | Idem UA-DETRAC |

**Comptage de référence.** Les annotations d'UA-DETRAC donnent, pour chaque véhicule, sa trajectoire (sa boîte dans chaque image) et son type. Nous appliquons à ces trajectoires annotées la même ligne virtuelle et le même test de franchissement que notre système. Nous obtenons ainsi, pour chaque séquence, la liste des passages réels (instant, type, sens). Pour vérifier que cette référence est juste, deux d'entre nous comptent à la main trois séquences et nous mesurons l'accord avec la référence automatique. Nous écartons aussi les zones que les auteurs ont exclues des annotations (véhicules trop petits pour être annotés). Les annotations ont leurs propres imperfections : c'est une limite que nous assumons (section 9).

**Types de véhicules.** UA-DETRAC annote quatre types (voiture, bus, camionnette et autres, ce dernier regroupant notamment camions et citernes), alors que YOLO prédit les classes COCO `car`, `motorcycle`, `bus` et `truck`. Pour comparer, nous regroupons en trois catégories : voitures et camionnettes (annotations « voiture » et « camionnette », classe `car`), bus (classe `bus`), et poids lourds et utilitaires (annotations « autres », classe `truck`). Une camionnette peut être classée `truck` par YOLO : cette confusion fait partie des erreurs que nous mesurons. Les motos n'ont pas de catégorie propre dans ce jeu, nous ne pouvons donc pas mesurer leur erreur de comptage.

**Découpage.** Nous séparons les séquences en veillant à ne pas mélanger les lieux : environ une séquence sur six sert uniquement à régler les seuils, la ligne et la zone d'intérêt, et toutes les autres servent au test final sans jamais servir au réglage. Si nous faisons un fine-tuning, nous séparons entraînement, validation et test par séquence et non par image, puisque des images voisines d'une même vidéo sont presque identiques.

**Conditions.** Les séquences étant étiquetées par conditions d'éclairage (nuageux, nuit, ensoleillé, pluvieux), nous mesurons l'erreur pour chacune. Les critères d'acceptation portent sur le jour et le temps sec (séquences nuageuses et ensoleillées), le reste est rapporté tel quel.

**Données personnelles.** Nous téléchargeons le jeu une seule fois, nous ne le redistribuons pas (ni sur Git, ni dans le rapport, sauf quelques captures floutées), nous le gardons sur nos machines et nous le supprimons à la fin du module. Pour un déploiement réel, la vidéo serait traitée en mémoire sans être enregistrée.

## 5. Métriques, baseline et critères d'acceptation

- **Baseline et son résultat :** nous comparons plusieurs versions, de la plus simple à la plus complète.
  - C0 : soustraction d'arrière-plan et comptage par ligne, sans type de véhicule.
  - C1 : YOLO nano pré-entraîné, seuil par défaut, sans suivi, comptage image par image. C'est notre baseline de référence. Nous attendons beaucoup de doublons, ce qui justifie le suivi.
  - C2 : C1 avec ByteTrack et anti-doublon.
  - C3 : C2 avec zone d'intérêt et seuils réglés, en comparant nano et small. C'est le système visé.
  - C4 : C3 avec un modèle affiné, seulement si C3 ne passe pas les critères.

  Résultats mesurés (erreur relative totale, par type, biais, débit) : à insérer dans un tableau après les essais sur nos séquences.
- **Métrique principale et pourquoi :** l'erreur relative de comptage, `|compté - réel| / réel`, calculée par séquence, par type et au total. C'est ce qui compte pour l'ingénieur trafic, qui veut un bon volume de trafic. Un bon score de détection ne dit pas si un véhicule est compté une fois ou trois. Nous suivons aussi le biais, `(compté - réel) / réel`, qui montre si le système se trompe toujours dans le même sens.
- **Métriques secondaires :** un total correct peut cacher des erreurs qui se compensent. Nous apparions donc chaque passage détecté avec un passage réel (même type, même sens, à plus ou moins 1 seconde) et calculons précision et rappel des passages. Nous mesurons aussi la qualité du suivi (score IDF1 et nombre de changements d'identifiant) sur une séquence, la précision et le rappel du détecteur sur 100 à 200 images annotées, le débit en images par seconde, et l'erreur selon les conditions (jour, nuit, pluie, trafic fluide ou dense).
- **Critères d'acceptation :**

| # | Critère | Seuil | Jeu de données et condition |
|---|---|---|---|
| A1 | Erreur de comptage total | 10 % maximum | Total des séquences de test, jour, temps sec |
| A1b | Erreur de comptage par séquence | 20 % maximum (effectifs faibles sur des séquences courtes) | Chaque séquence de test, jour, temps sec |
| A2 | Erreur par type | 15 % maximum pour les voitures, 25 % pour bus et poids lourds | Total des séquences de test, jour, temps sec |
| A3 | Biais | 5 % maximum en valeur absolue | Total des séquences de test, jour, temps sec |
| A4 | Rappel des passages | 90 % minimum | Séquences de test, appariement à 1 seconde |
| A5 | Vitesse de traitement | 15 images/s minimum | Notre machine cible, une image sur deux autorisée |
| A6 | Mieux que la baseline | Erreur de C3 inférieure à celle de C1 | Chaque séquence de test |

  Les motos n'ont pas de catégorie dans UA-DETRAC : leur erreur n'est pas mesurable avec ce jeu et n'a donc pas de critère. Si notre vérification à la main montre que la référence automatique s'écarte de plus de 5 % du comptage humain, nous relèverons les seuils A1 et A4 d'autant et nous le justifierons dans le rapport. Nuit et pluie sont rapportées sans seuil bloquant.

## 6. Architecture prévue (après la séance 5)

```text
  fichier vidéo
        │
        ▼
┌────────────────────┐
│ 1. Acquisition     │  OpenCV : lecture des images, saut d'images
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 2. Détection       │  YOLO pré-entraîné : boîtes, type, confiance
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 3. Suivi           │  ByteTrack : un identifiant par véhicule
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 4. Comptage        │  zone d'intérêt, ligne, sens, anti-doublon
└─────────┬──────────┘
          ▼
┌────────────────────┐         ┌──────────────────────┐
│ 5. Stockage        │ ──────▶ │ 6. Tableau de bord   │
│ SQLite + CSV       │         │ Streamlit + alertes  │
└────────────────────┘         └──────────────────────┘

 Hors ligne : 7. Évaluation (rejoue les séquences et compare au comptage de référence)
```

Chaque bloc est un module Python séparé, avec son test : lecture d'une séquence courte, détection sur une image connue, suivi sur une séquence fabriquée, comptage sur des cas écrits à la main (franchissement dans les deux sens, aller-retour, arrêt sur la ligne), stockage sur une base temporaire. La configuration est dans un fichier YAML :

```yaml
source: "data/ua-detrac/MVI_20011"      # une séquence
model: "yolo26n.pt"        # ou yolo26s.pt, yolo11n.pt en repli
tracker: "bytetrack.yaml"
conf: 0.35
iou: 0.5
frame_stride: 1            # 2 = une image sur deux
line: {A: [120, 480], B: [820, 470]}
roi: [[0, 300], [960, 300], [960, 540], [0, 540]]
```

La base SQLite contient une table `counts` (minute, source, type, sens, nombre), lue par le tableau de bord, et une table `health` (heure, images par seconde, état du traitement) pour l'alerte d'arrêt du traitement. Les passages individuels ne sont gardés que pendant l'évaluation. Le dépôt est organisé en `src/`, `app/`, `configs/`, `data/` (jeu UA-DETRAC et comptages de référence, non versionnés), `eval/`, `tests/` et `docs/`.

## 7. Choix technologiques (après la séance 5)

| Besoin | Outil | Justification |
|---|---|---|
| Détection | Ultralytics YOLO26 (YOLO11 en repli), poids COCO | Modèle prêt à l'emploi, détection et suivi dans la même bibliothèque, plusieurs tailles. La licence AGPL-3.0 convient à un projet académique, un usage commercial demanderait la licence entreprise |
| Taille du modèle | Nano comparé à small | Nous gardons le plus petit qui passe les critères, d'après nos mesures de précision et de vitesse |
| Suivi | ByteTrack (comparé à BoT-SORT) | Léger, gère bien les détections peu sûres, rien à entraîner |
| Vidéo et géométrie | OpenCV et NumPy | Standard, lit les fichiers vidéo et les suites d'images |
| Stockage | SQLite et export CSV | Pas de serveur à installer, un seul fichier, suffisant pour des totaux par minute |
| Interface | Streamlit | Un tableau de bord en peu de code, lisible par un non-informaticien |
| Évaluation | pandas, matplotlib, py-motmetrics | Tableaux, courbes d'erreur, calcul d'IDF1 |
| Reproductibilité | venv, requirements.txt figé, Git | Contrainte N4 |
| Tests | pytest | Vérifier le comptage sur des cas écrits à la main |

## 8. Risques, éthique, confidentialité

**1. Les données contiennent-elles des données personnelles ? Lesquelles ?**
Oui, possiblement. Les vidéos d'UA-DETRAC peuvent montrer des plaques d'immatriculation, qui permettent de remonter à un propriétaire, et des visages de conducteurs ou de passants. Les compteurs que le système stocke (date, heure, type, sens, nombre) ne contiennent aucune donnée personnelle.

**2. Peut-on s'en passer ou les anonymiser ?**
On peut presque totalement s'en passer, parce que notre besoin est un nombre et pas une identité. Mesures : nous ne redistribuons pas le jeu de données, les captures du rapport sont floutées, nous supprimons le jeu à la fin du module.

**3. Qui peut être lésé par une erreur ?**
Les usagers de la route, si un trafic sous-estimé conduit à un feu ou une voie mal dimensionnés. La commune, si un trafic surestimé justifie une dépense inutile. Les riverains, si un aménagement est décidé sur de mauvais chiffres. Et, en cas de fuite de vidéos, les personnes filmées. Mesure : nous mesurons et affichons l'erreur par type de véhicule, et le tableau de bord indique la marge d'erreur validée pour que personne ne prenne un chiffre pour exact.

**4. Les données couvrent-elles tous les cas d'usage (lieux, périodes, populations) ?**
Non, et nous le disons. UA-DETRAC vient de 24 sites filmés dans un autre contexte routier que celui du Maroc (types de véhicules, signalisation, comportements), et le modèle est entraîné sur COCO, qui contient surtout des véhicules de types courants dans d'autres pays : des véhicules locaux comme les triporteurs, les charrettes ou les petits utilitaires peuvent être mal détectés ou classés dans le mauvais type. Mesures : nous annonçons uniquement les conditions validées (jour, temps sec, jeu public), nous rapportons l'erreur par condition, nous revalidons sur chaque nouveau site, notamment sur une route marocaine avant tout déploiement réel, et nous prévoyons un fine-tuning si ces véhicules pèsent dans le trafic.

**5. Quelle erreur coûte le plus, et à qui ?**
Un sous-comptage systématique, surtout des poids lourds et des bus : le trafic réel est plus lourd que celui affiché, d'où des voies sous-dimensionnées, des embouteillages et un risque pour la sécurité, ce qui retombe sur les usagers et sur la commune. Une erreur isolée sur une séquence coûte peu. C'est pour cela que nous suivons le biais (critère A3) et pas seulement l'erreur absolue, et que le rappel des passages est exigé à 90 % (critère A4).

**6. Qui valide les décisions, et peut les corriger ?**
Le système ne décide rien : l'ingénieur trafic reste seul responsable de la décision, il lit les chiffres et choisit. Il peut marquer une plage horaire comme invalide dans le tableau de bord (cadrage modifié, panne, chantier), et la correction est enregistrée avec la date. L'administrateur technique peut retracer la ligne et refaire les réglages. Une fois par mois, une vérification visuelle d'une image avec la ligne tracée permet de repérer un cadrage qui a changé.

**7. Des données sortent-elles de l'organisation (API externe) ?**
Non. Tout le traitement se fait en local : le modèle et le jeu de données sont téléchargés une fois puis exécutés sur la machine, il n'y a ni API externe ni service dans le cloud, et la base SQLite reste sur place. Mesure : par défaut, Ultralytics envoie des statistiques d'usage anonymes et des rapports de plantage ; nous mettons `sync=False` dans ses paramètres et nous vérifions qu'aucune connexion sortante n'a lieu pendant le traitement. Le tableau de bord n'est accessible que sur le réseau interne et protégé par mot de passe.

**8. Comment le système pourrait-il être détourné ?**
Une caméra qui détecte les véhicules peut être réutilisée pour surveiller des personnes, lire les plaques et suivre des véhicules précis, ou verbaliser. Mesures : le système ne conserve aucune donnée individuelle, les passages individuels ne sont gardés que pendant l'évaluation, nous ne livrons pas de module de lecture de plaque, l'usage annoncé est limité au comptage agrégé et cela figure dans la documentation. Autres risques : un accès non autorisé à la base ou aux vidéos (accès protégé, tableau de bord non exposé sur Internet), et une dépendance à des poids ou à une bibliothèque qui changeraient ou disparaîtraient (versions figées, copie conservée). Côté légal, filmer la voie publique demande l'autorisation de l'autorité compétente (au Maroc, loi 09-08 et CNDP). Pour le projet, nous n'utilisons qu'un jeu de données public, uniquement pour l'évaluation. L'AGPL-3.0 d'Ultralytics convient à un projet académique, un usage commercial demanderait la licence entreprise.

## 9. Limites et hors périmètre

**Limites**

- Quand le trafic est très dense, des véhicules se cachent entre eux et le comptage baisse. Une caméra en hauteur, avec un angle plongeant, aide.
- Nuit, pluie et contre-jour : nous mesurons l'erreur sur les séquences concernées, sans critère bloquant. L'usage annoncé reste le jour par temps sec.
- Les motos et vélos sont petits et rapides, donc leur comptage est moins fiable, et UA-DETRAC n'a pas de catégorie moto : nous ne pouvons pas mesurer leur erreur avec ce jeu.
- La classe `truck` de COCO regroupe poids lourds et utilitaires, donc l'interface parle de « poids lourds et utilitaires ».
- Le modèle n'est pas calibré sur la scène de chaque site : l'erreur dépend de l'angle et de la hauteur de la caméra, d'où le réglage par site et le fine-tuning en option.
- COCO ne connaît pas certains véhicules locaux (triporteurs, charrettes), qui peuvent ne pas être comptés ou être mal classés.
- Le comptage suppose une caméra fixe : si le cadrage change, la ligne n'est plus à la bonne place.
- Tout est validé sur un jeu de données public, pas sur nos routes. Il faudra revalider sur un site réel avant tout déploiement.
- Notre comptage de référence vient des annotations d'UA-DETRAC, qui ont leurs propres imperfections (véhicules oubliés, zones ignorées). Nous le vérifions à la main sur trois séquences.

**Hors périmètre**

- Lecture de plaques d'immatriculation.
- Vitesse, infractions, verbalisation.
- Identification ou suivi de personnes.
- Entraînement d'un détecteur depuis zéro.
- Caméras mobiles (drone, véhicule).
- Déploiement industriel sur plusieurs sites.
- Prévision du trafic futur.

## Planning de travail

1. Téléchargement d'UA-DETRAC, choix des séquences, construction du comptage de référence et vérification à la main sur trois séquences : tous les trois.
2. Baselines C0 et C1 et script d'évaluation.
3. Pipeline de détection, suivi et comptage, avec les tests.
4. Réglage, évaluation complète sur les séquences de test, comparaison nano et small, comparaison des suiveurs.
5. Fine-tuning, seulement si les critères ne sont pas atteints.
6. Stockage, tableau de bord, alertes et export.
7. Version finale de l'étude, rapport et démonstration : tous les trois.

## Références

- Wen, L., Du, D., Cai, Z., Lei, Z., Chang, M.-C., Qi, H., Lim, J., Yang, M.-H., Lyu, S. « UA-DETRAC: A New Benchmark and Protocol for Multi-Object Detection and Tracking ». *Computer Vision and Image Understanding (CVIU)*, 2020.
- Lin, T.-Y. et al. « Microsoft COCO: Common Objects in Context ». ECCV, 2014.
- Zhang, Y. et al. « ByteTrack: Multi-Object Tracking by Associating Every Detection Box ». ECCV, 2022.
- Documentation Ultralytics (modèles YOLO, suivi, comptage d'objets, confidentialité) : https://docs.ultralytics.com
