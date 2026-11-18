# Étude de conception – Comptage de véhicules par vision (YOLO pré-entraîné)
Groupe : DOUAA AHMITO · MOHAMED NACER JOURAAI · YASSIR OUAHLA  ·  Version : finale  ·  Date : 18/11/2026

**Module :** Développement d'applications intelligentes

> **Points arrêtés par le groupe pour cette étude** (modifiables, tout le document en dépend) :
> 1. **Site :** un axe urbain à deux sens, filmé par une caméra fixe en hauteur (passerelle, balcon ou toit d'immeuble), en plan large.
> 2. **Conditions couvertes :** jour, temps sec. La nuit et la forte pluie sont **hors périmètre** (voir section 9).
> 3. **Vidéos de test :** tournées par le groupe (au moins 8 clips de 5 minutes, à des heures différentes), comptées à la main par les trois membres.
> 4. **Machine cible :** un ordinateur portable du groupe (GPU ou CPU, mesuré en section 5).
> 5. **Modèle :** YOLO pré-entraîné d'Ultralytics, **sans réentraînement** dans la version de base.

---

## 1. Contexte et utilisateurs

### 1.1 Organisation ou situation
- **Organisation :** le service mobilité d'une commune (ou le gestionnaire d'une voirie) qui doit connaître le trafic sur un axe pour dimensionner feux, voies et travaux.
- **Situation actuelle :** le comptage se fait soit à la main (un agent sur place quelques heures par an), soit par des capteurs enterrés (boucles magnétiques), coûteux à installer et peu souples. Les données sont rares, anciennes et sans détail par type de véhicule.
- **Besoin :** un comptage continu, par **type de véhicule** (voiture, moto, bus, poids lourd / utilitaire) et par **sens de circulation**, à partir d'une simple caméra fixe.
- **Cadre du projet :** on réutilise un détecteur **pré-entraîné**. Le travail du groupe porte sur l'application complète : suivi, comptage, protocole d'évaluation, stockage et restitution. Il ne porte pas sur l'entraînement d'un nouveau réseau.

### 1.2 Utilisateur principal
- **Rôle précis :** **ingénieur trafic / responsable mobilité** de la commune.
- **Compétences :** connaît le trafic routier, pas le deep learning. Il lit un tableau de bord, il n'ouvre pas un terminal.
- **Autres acteurs :** l'**agent d'installation** (pose la caméra, trace la ligne de comptage) et l'**administrateur technique** (déploie, met à jour, surveille).

### 1.3 Scénarios d'usage
| # | Acteur | Scénario | Résultat attendu |
|---|---|---|---|
| S1 | Agent d'installation | Fixe la caméra, ouvre l'interface, trace la ligne de comptage sur une image de la scène, lance le traitement | Ligne enregistrée dans le fichier de configuration, compteurs à zéro |
| S2 | Système | Traite le flux en continu et incrémente les compteurs par classe et par sens | Un enregistrement par minute dans la base |
| S3 | Ingénieur trafic | Ouvre le tableau de bord chaque matin, compare avec la veille et la semaine précédente | Décision de réglage ou de planification |
| S4 | Ingénieur trafic | Exporte le CSV hebdomadaire pour un rapport | Fichier horodaté par heure, classe, sens |
| S5 | Administrateur | Reçoit une alerte si le flux vidéo est coupé ou si les comptages tombent anormalement à zéro | Redémarrage ou intervention sur la caméra |

---

## 2. Problème et décision

- **Décision que l'utilisateur prend avec le système :** adapter la gestion du trafic selon les volumes mesurés : durée des phases de feux, ouverture ou fermeture d'une voie, choix des créneaux de travaux, justification d'un aménagement (voie de bus, rond-point).
- **Fréquence :**
  - consultation du tableau de bord : **une fois par jour** ;
  - rapport avec export CSV : **une fois par semaine** ;
  - alerte quasi immédiate : si le flux vidéo s'interrompt ou si un seuil de débit est dépassé ;
  - décisions d'aménagement : quelques fois par an, sur des données agrégées de plusieurs semaines.
- **Conséquence d'une erreur, et pour qui :**

| Erreur | Cause typique | Conséquence | Pour qui |
|---|---|---|---|
| Sous-comptage | Véhicule masqué par un autre, camion non détecté, perte d'identifiant avant la ligne | Trafic sous-estimé, feu ou voie mal dimensionné, congestion non anticipée | Usagers de la route, commune |
| Sur-comptage | Même véhicule compté deux fois (changement d'identifiant), piéton ou panneau pris pour un véhicule, ligne mal placée | Investissement inutile, mauvaise priorisation | Budget de la commune |
| Mauvais type | Bus classé camion, moto non vue, utilitaire classé voiture | Statistiques par catégorie faussées (poids lourds, transport collectif) | Ingénieur trafic, études environnementales |
| Panne silencieuse | Caméra déplacée, flux coupé, ligne décalée sans que personne ne le voie | Plusieurs jours de données fausses | Tous |

- **Gravité globale : moyenne.** Une erreur de quelques pourcents ne change pas une décision ; un biais systématique de plus de 20 % peut la changer. Le système est une **aide à la décision**, jamais une preuve juridique : pas de verbalisation, pas d'identification d'individus.

### 2.1 Exigences fonctionnelles
| ID | Exigence | Priorité |
|---|---|---|
| F1 | Lire un fichier vidéo ou un flux de caméra (RTSP) | Indispensable |
| F2 | Détecter voitures, motos, bus et poids lourds / utilitaires | Indispensable |
| F3 | Suivre chaque véhicule avec un identifiant stable | Indispensable |
| F4 | Compter les franchissements d'une ligne virtuelle, par classe et par sens | Indispensable |
| F5 | Enregistrer les comptages horodatés (base SQLite) et exporter en CSV | Indispensable |
| F6 | Tableau de bord : totaux, courbe par heure, comparaison de jours | Indispensable |
| F7 | Configurer la ligne, la zone d'intérêt et les seuils sans modifier le code | Important |
| F8 | Alerte si flux coupé ou comptage anormalement nul | Souhaitable |
| F9 | Mode évaluation : rejouer une vidéo et comparer à la vérité terrain | Indispensable (pour le rapport) |

### 2.2 Exigences non fonctionnelles
| ID | Exigence | Valeur cible |
|---|---|---|
| N1 | Débit de traitement | ≥ 15 images/s sur la machine cible (saut d'une image sur deux autorisé) |
| N2 | Précision de comptage | Erreur relative ≤ 10 % par vidéo (détail section 5.4) |
| N3 | Vie privée | Aucune image ni plaque conservée en production ; seuls les comptages agrégés sont stockés |
| N4 | Reproductibilité | Versions des bibliothèques et des poids figées, graine fixée, protocole d'évaluation rejouable par un script |
| N5 | Robustesse | Reprise automatique si le flux se coupe (nouvelle tentative toutes les 10 s) |
| N6 | Maintenabilité | Modules séparés et testés (pytest), configuration externe |

---

## 3. Approche par sous-problème

| Sous-problème | Approche (règles / ML / DL / LLM / RAG) | Pourquoi pas une approche plus simple |
|---|---|---|
| **Détection** des véhicules (position et type dans chaque image) | **DL** : détecteur YOLO pré-entraîné sur COCO (famille Ultralytics YOLO26, avec YOLO11 en solution de repli stable), classes COCO `car` (2), `motorcycle` (3), `bus` (5), `truck` (7). Tailles nano et small comparées | La soustraction d'arrière-plan (OpenCV MOG2) réagit aux ombres, aux changements de lumière et aux arrêts, ne donne pas le type et fusionne les véhicules proches. Entraîner un détecteur de zéro demanderait des milliers d'images annotées et un GPU |
| **Suivi** (même véhicule = même identifiant d'une image à l'autre) | **Algorithmique / ML léger** : ByteTrack (filtre de Kalman + association par IoU, gère les détections peu confiantes). Comparé à BoT-SORT et au suiveur par défaut d'Ultralytics | Sans suivi, compter les détections image par image compterait un même véhicule des dizaines de fois. Un « plus proche voisin » simple perd l'identité dès qu'un véhicule est masqué quelques images |
| **Comptage** (un véhicule a-t-il franchi la ligne, dans quel sens) | **Règles** : géométrie du franchissement de segment, un identifiant ne compte qu'une fois | Déterministe, explicable, testable à la main. Du ML n'ajouterait que de l'incertitude |
| **Délimitation de la scène** (ignorer les voies voisines, trottoirs) | **Règles** : zone d'intérêt polygonale, filtre sur la taille minimale des boîtes | Sans zone d'intérêt, des véhicules hors voie ou très lointains polluent le comptage |
| **Réglage** (seuil de confiance, NMS, position de la ligne) | **Validation empirique** sur une vidéo de réglage distincte des vidéos de test | Les valeurs par défaut dépendent de l'angle et de la hauteur de la caméra |
| **Adaptation du modèle** (si les critères ne sont pas atteints) | **DL : fine-tuning** sur 300 à 1 000 images annotées de la scène réelle | Déclenché uniquement sur constat mesuré : coûteux en annotation et en calcul |
| **Évaluation** | **Scripts** : erreur de comptage, appariement des événements, IDF1 | Un simple « ça a l'air de marcher » ne prouve rien |
| **Restitution** | **Application web** (Streamlit) + export CSV | Un fichier de log ne serait pas exploitable par l'ingénieur trafic |

**Volontairement non utilisés :** LLM et RAG (aucun besoin textuel ou documentaire), reconnaissance de plaques (hors périmètre et intrusive), réseaux de segmentation (inutiles pour compter).

### 3.1 Algorithme de comptage
Principe, pour chaque image :

```text
détections = yolo.track(image, persist=True, tracker="bytetrack.yaml",
                        classes=[2, 3, 5, 7], conf=0.35, iou=0.5)
pour chaque (id, boîte, classe) dans détections :
    p = (centre_x, bas_y)                  # point de contact avec la chaussée
    si p n'est pas dans la zone d'intérêt : ignorer
    si id a une position précédente q et id pas déjà compté :
        si le segment [q, p] coupe la ligne [A, B] :
            sens = signe( produit_vectoriel(B - A, p - q) )
            compteurs[classe][sens] += 1
            marquer id comme compté
    position_précédente[id] = p
```

- **Point de référence :** centre du bord inférieur de la boîte, plus proche du sol et moins sensible à la hauteur du véhicule que le centre.
- **Ligne virtuelle :** segment défini par deux points A et B (coordonnées image), enregistré dans la configuration.
- **Sens :** signe du produit vectoriel, deux compteurs (aller / retour).
- **Anti-doublon :** ensemble des identifiants déjà comptés ; un véhicule arrêté sur la ligne ne compte pas deux fois.
- **Cas difficiles :** véhicule masqué (le suiveur garde la trace ~30 images), changement d'identifiant (mesuré par IDF1 et par le nombre de *switches*), deux véhicules collés (limite connue, section 9).
- **Horodatage :** chaque événement est horodaté (instant de l'image), ce qui permet l'appariement avec la vérité terrain (section 5.3).

*Remarque :* Ultralytics fournit une solution de comptage prête à l'emploi (`ObjectCounter`, ligne à deux points ou région). Le groupe l'utilise comme **point de comparaison** et écrit sa propre logique, afin de maîtriser l'anti-doublon, la zone d'intérêt et l'export des événements.

---

## 4. Données

| Jeu de données | Source et licence | Volume | Données personnelles ? |
|---|---|---|---|
| **Poids YOLO pré-entraînés** | Ultralytics. Code et modèles sous **AGPL-3.0** (usage académique) ou **licence entreprise** (usage commercial). Entraînés sur COCO (annotations sous CC BY 4.0, images soumises aux conditions Flickr d'origine) | Modèle nano ou small, 80 classes dont 4 utiles | Les images COCO contiennent des personnes, hors de notre contrôle ; aucun impact sur notre usage |
| **Vidéos de test** (corpus principal) | Tournées par le groupe, propriété du groupe, usage académique | ≥ 8 clips de 5 min, soit au moins ~1 000 véhicules à compter ; heures et densités variées (fluide, dense, deux sens) | **Oui, potentiellement** : plaques et visages visibles selon le cadrage |
| **Vidéo de réglage** | Idem, clip distinct des clips de test | 1 clip de 5 min | Idem |
| **Vérité terrain** | Produite par le groupe (voir 4.1) | Un fichier par clip : instants de passage, classe, sens | Non (aucune image) |
| **Jeu d'affinage** (seulement si besoin) | Annotation maison (CVAT ou Roboflow) ou jeu public de trafic (licence à vérifier avant usage) | 300 à 1 000 images annotées | Idem vidéos |

### 4.1 Construction de la vérité terrain
1. Chaque clip est visionné et compté **indépendamment par deux membres** : instant de passage, classe, sens, avec un outil de lecture image par image.
2. Le **troisième membre arbitre** les écarts. On conserve le comptage consensuel.
3. Un fichier CSV par clip : `timestamp_s, classe, sens`. Ce fichier permet de comparer le total et aussi de localiser chaque erreur.
4. On mesure l'**accord entre les deux premiers compteurs** (nombre de passages identiques). Il donne l'ordre de grandeur de l'erreur « humaine » : on ne peut pas exiger du système plus de précision que la référence.

### 4.2 Découpage
| Ensemble | Contenu | Usage |
|---|---|---|
| Réglage | 1 clip | Choix des seuils, de la ligne, de la zone d'intérêt, du suiveur |
| Test | Les autres clips | Évaluation finale, **jamais utilisés pour régler** |
| Affinage (option) | Images extraites de clips séparés | Entraînement, validation, test séparés **par clip**, pas par image (images voisines quasi identiques) |

### 4.3 Données personnelles : mesures prises
- Cadrage en **plan large**, caméra en hauteur : le texte des plaques n'est pas lisible.
- **Production :** le flux est traité en mémoire, **aucune vidéo n'est enregistrée**. Seuls sont stockés : date et heure, classe, sens, nombre.
- **Corpus de test :** clips conservés en résolution réduite, accès limité aux trois membres et à l'encadrant, **suppression en fin de module**. Les captures d'écran du rapport sont floutées (bas des véhicules, visages).

---

## 5. Métriques, baseline et critères d'acceptation

### 5.1 Baseline et son résultat
| Configuration | Description | Résultat |
|---|---|---|
| **C0 – baseline simple** | Soustraction d'arrière-plan (MOG2), contours, comptage par ligne, sans type | Erreur de comptage mesurée sur les clips de test : à reporter au tableau final |
| **C1 – baseline de référence** | `YOLO nano` pré-entraîné, seuil par défaut, **sans suivi** : comptage image par image | Idem : attendu fort sur-comptage (doublons), ce qui justifie le suivi |
| **C2 – suivi** | C1 + ByteTrack + anti-doublon | Idem |
| **C3 – système cible** | C2 + zone d'intérêt, seuils réglés sur la vidéo de réglage, comparaison nano / small | Idem |
| **C4 – option** | C3 + modèle affiné | Seulement si C3 ne passe pas les critères |

Le tableau final du rapport donne, pour chaque configuration, l'erreur relative totale, par classe, le biais et le débit. Il montre l'**apport de chaque composant** (suivi, zone d'intérêt, taille du modèle).

### 5.2 Métrique principale et pourquoi
- **Erreur relative de comptage :** `|C − R| / R`, où C est le nombre compté et R le nombre réel, calculée par clip, par classe et au total.
- **Pourquoi :** c'est ce qui compte pour l'utilisateur, qui veut un bon volume de trafic. Le score de détection (mAP) ne dit pas si un véhicule est compté une fois ou trois.
- **Biais signé :** `(C − R) / R`. Il distingue une erreur qui s'annule en moyenne d'une erreur qui va toujours dans le même sens (sous-estimation par exemple).

### 5.3 Métriques secondaires
| Métrique | Définition | Question à laquelle elle répond |
|---|---|---|
| **Précision / rappel des événements** | On apparie chaque passage détecté à un passage réel de même classe et de même sens, à ± 1 s. Rappel = appariés / réels ; précision = appariés / détectés | Le total est-il juste **parce que** les passages sont justes, ou par compensation d'erreurs ? |
| **IDF1 et nombre de changements d'identifiant** | Sur un clip annoté image par image (un seul clip) | Le suivi est-il en cause ? |
| **Précision, rappel, mAP@0,5** du détecteur | Sur 100 à 200 images annotées | Le détecteur est-il en cause ? (comparaison nano / small) |
| **Débit** | Images traitées par seconde, latence moyenne | Le temps réel est-il tenu ? |
| **Erreur par condition** | Erreur relative selon fluide / dense / ombre / sens | Où le système échoue-t-il ? |

### 5.4 Critères d'acceptation
Le système est accepté si **toutes** les conditions suivantes sont remplies :

| # | Critère | Seuil | Jeu et condition |
|---|---|---|---|
| A1 | Erreur relative de comptage total | ≤ **10 %** sur chaque clip de test | Clips jamais vus au réglage, jour, temps sec |
| A2 | Erreur relative par classe | ≤ **15 %** pour les voitures, ≤ **25 %** pour poids lourds et bus | Total cumulé des clips de test |
| A3 | Biais moyen | Biais absolu ≤ 5 % | Total cumulé |
| A4 | Rappel des événements | ≥ **90 %** | Appariement à ± 1 s |
| A5 | Débit | ≥ **15 images/s** | Machine cible, saut d'une image sur deux autorisé |
| A6 | Vie privée | Aucune image stockée en production | Vérification du dossier de sortie |
| A7 | Meilleur que la baseline | Erreur de C3 strictement inférieure à C1 sur chaque clip | Tableau 5.1 |

**Cas des motos :** petites et souvent masquées, elles sont rapportées avec leur erreur mesurée, **sans seuil bloquant**.
**Référence humaine :** si l'accord entre les deux compteurs humains est lui-même inférieur à 95 %, les seuils A1 et A4 sont relevés d'autant et le groupe le justifie dans le rapport.

---

## 6. Architecture prévue (après la séance 5)

```text
 Caméra fixe / fichier vidéo
        │  (RTSP ou fichier)
        ▼
┌────────────────────┐
│ 1. Acquisition     │  OpenCV : lecture, redimensionnement, saut d'images
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 2. Détection       │  YOLO pré-entraîné → boîtes, classe, confiance
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 3. Suivi           │  ByteTrack → identifiant stable par véhicule
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 4. Comptage        │  zone d'intérêt, ligne virtuelle, sens, anti-doublon
└─────────┬──────────┘
          ▼
┌────────────────────┐         ┌──────────────────────┐
│ 5. Stockage        │ ──────▶ │ 6. Tableau de bord   │  Streamlit : totaux,
│ SQLite + CSV       │         │ + alertes + export   │  courbes, alertes
└────────────────────┘         └──────────────────────┘

        Hors ligne : 7. Évaluation (rejoue les clips, compare à la vérité terrain)
```

### 6.1 Modules et responsabilités
| Module | Rôle | Entrée → sortie | Test unitaire |
|---|---|---|---|
| `acquisition` | Lire les images, gérer la reconnexion | source → images | Fichier vidéo court |
| `detection` | Appeler YOLO, filtrer les classes et la confiance | image → liste de boîtes | Image de référence |
| `tracking` | Associer les boîtes dans le temps | boîtes → boîtes + identifiants | Séquence synthétique |
| `counting` | Zone d'intérêt, franchissement, sens, anti-doublon | pistes → événements | **Cas construits à la main** (franchissement, aller-retour, arrêt sur la ligne) |
| `storage` | Agréger par minute, écrire en base, exporter | événements → SQLite / CSV | Base temporaire |
| `dashboard` | Afficher et exporter | base → pages | Test manuel |
| `evaluation` | Comparer aux vérités terrain, produire les tableaux | événements + CSV de référence → métriques | Cas minuscules vérifiés à la main |

### 6.2 Configuration (extrait)
```yaml
source: "clips/test_01.mp4"
model: "yolo26n.pt"        # ou yolo26s.pt, yolo11n.pt en repli
tracker: "bytetrack.yaml"
classes: {car: 2, motorcycle: 3, bus: 5, truck: 7}
conf: 0.35
iou: 0.5
frame_stride: 1            # 2 = une image sur deux
line: {A: [120, 480], B: [820, 470]}
roi: [[0, 300], [960, 300], [960, 540], [0, 540]]
```

### 6.3 Modèle de données (SQLite)
| Table | Colonnes | Remarque |
|---|---|---|
| `counts` | `ts_minute`, `camera_id`, `classe`, `sens`, `n` | Une ligne par minute, classe et sens ; seule table lue par le tableau de bord |
| `events` (mode évaluation seulement) | `ts_s`, `track_id`, `classe`, `sens` | Pour l'appariement avec la vérité terrain ; non conservée en production |
| `health` | `ts`, `fps`, `etat_flux` | Alimente l'alerte « flux coupé » |

### 6.4 Arborescence du dépôt
`src/` (acquisition, detection, tracking, counting, storage, evaluation) · `app/` (tableau de bord) · `configs/` · `data/` (clips et vérités terrain, **non versionnés**) · `eval/` (scripts et résultats) · `tests/` · `docs/etude-de-conception.md` · `requirements.txt` (versions figées)

---

## 7. Choix technologiques (après la séance 5)

| Besoin | Outil | Justification |
|---|---|---|
| Détection | **Ultralytics YOLO26** (YOLO11 en repli stable), poids COCO pré-entraînés | Modèle prêt à l'emploi, détection et suivi dans la même API, plusieurs tailles. **Licence :** AGPL-3.0 acceptable pour un projet académique ; une licence entreprise serait nécessaire pour un produit commercial |
| Taille du modèle | `n` (rapide) comparé à `s` (plus précis) | Choix tranché par la mesure (débit et erreur) sur la machine du groupe : on garde le plus petit qui passe les critères |
| Suivi | **ByteTrack** (comparé à BoT-SORT et au suiveur par défaut) | Léger, robuste aux détections peu confiantes, aucun apprentissage supplémentaire |
| Lecture vidéo, tracé, géométrie | **OpenCV** + **NumPy** | Standard, gère fichiers et flux RTSP |
| Stockage | **SQLite** + export CSV | Sans serveur, suffisant pour des comptages agrégés, livrable dans un seul fichier |
| Interface | **Streamlit** | Tableau de bord en peu de code, adapté à un utilisateur non technique |
| Évaluation | **pandas**, **matplotlib**, **py-motmetrics** | Tableaux, courbes d'erreur, calcul d'IDF1 |
| Annotation (option) | **CVAT** ou **Roboflow** | Annoter les images de fine-tuning |
| Reproductibilité | **venv**, `requirements.txt` figé, **Git** | Exigence N4 |
| Tests | **pytest** | Tests unitaires du comptage (cas construits à la main) |
| Exécution | Ordinateur du groupe ; GPU si disponible, sinon CPU avec saut d'images | À mesurer (critère A5) |

---

## 8. Risques, éthique, confidentialité

> **Note :** sur la photo de l'énoncé, seule la question 1 était lisible. Les réponses 2 à 8 ci-dessous suivent les thèmes habituels (finalité, biais, erreurs, sécurité, droit, usages détournés, limites). Il suffit de **renvoyer les sept autres questions** pour que chaque réponse soit placée en face de la bonne.

### Question 1 – Les données contiennent-elles des données personnelles ? Lesquelles ? Peut-on s'en passer ou les anonymiser ?
**Oui, potentiellement.** Les vidéos peuvent montrer des **plaques d'immatriculation** (identifient indirectement un propriétaire) et des **visages** de conducteurs ou de passants. Mais le besoin réel est un **nombre**, pas une identité : on peut s'en passer presque entièrement.
- **Minimisation :** plan large, aucune reconnaissance de plaque, aucune sauvegarde du flux en production, stockage limité à des compteurs agrégés par minute.
- **Anonymisation :** floutage des captures utilisées dans le rapport ; clips de test en résolution réduite, supprimés en fin de module.

### Questions 2 à 8 – Autres risques, par thème
| Thème | Risque | Prob. | Impact | Mesure |
|---|---|---|---|---|
| **Finalité et usage détourné** | Le même système pourrait servir à surveiller des personnes ou à verbaliser | Faible | Élevé | Aucune donnée individuelle conservée ; usage déclaré limité au comptage agrégé ; mention explicite dans la documentation |
| **Biais de performance** | Moins bon sur les motos, les petits véhicules, les véhicules très lointains ou masqués, de nuit, sous la pluie. Le modèle n'a pas été entraîné pour notre scène | Élevée | Moyen | Mesurer l'erreur par classe et par condition ; publier ces chiffres ; limiter l'usage déclaré aux conditions validées |
| **Erreurs et confiance excessive** | Le tableau de bord affiche un chiffre précis qui semble fiable alors qu'il est faux (caméra déplacée, ligne décalée) | Moyenne | Élevé | Contrôle visuel périodique d'une image avec la ligne tracée ; alerte si comptage nul ou flux coupé ; marge d'erreur affichée |
| **Transparence et explicabilité** | L'utilisateur ne comprend pas comment le chiffre est obtenu | Moyenne | Moyen | Documentation du principe (ligne, suivi), mode évaluation qui montre les passages détectés sur la vidéo |
| **Sécurité** | Accès non autorisé au flux ou à la base | Moyenne | Moyen | Authentification du tableau de bord, flux non exposé sur Internet, aucune donnée sensible en base |
| **Cadre légal** | Vidéosurveillance de la voie publique soumise à autorisation (au Maroc : loi 09-08 et CNDP ; en Europe : RGPD) | Moyenne | Élevé | Autorisation de l'autorité compétente avant tout déploiement réel ; en projet académique, vidéos tournées en lieu public sans cibler d'individus, ou accord obtenu |
| **Licences** | AGPL-3.0 d'Ultralytics ; conditions des données tierces | Moyenne | Moyen | Respecter et citer les licences ; licence entreprise ou détecteur à licence permissive avant tout usage commercial |
| **Dépendance** | Évolution ou retrait du modèle pré-entraîné ou de la bibliothèque | Faible | Moyen | Figer les versions, conserver une copie des poids |
| **Impact environnemental** | Calcul vidéo continu | Faible | Faible | Plus petit modèle qui passe les critères, saut d'images |
| **Risque projet** | Pas assez de vidéos exploitables, ou vérité terrain trop incertaine | Moyenne | Élevé | Tourner les clips dès la première semaine ; double comptage humain avec mesure d'accord (4.1) |

---

## 9. Limites et hors périmètre

### Limites connues
| Limite | Conséquence | Atténuation |
|---|---|---|
| Fortes densités : véhicules qui se masquent | Sous-comptage | Caméra en hauteur, angle plongeant ; mesurer l'erreur en trafic dense |
| Nuit, pluie, contre-jour | Performance non garantie | **Hors du périmètre validé** ; l'usage déclaré est limité au jour, temps sec |
| Motos et vélos petits et rapides | Comptage moins fiable | Rapportés avec leur erreur, sans seuil bloquant |
| Classe COCO `truck` regroupe poids lourds et utilitaires | Imprécision de la catégorie « poids lourd » | Intitulé « poids lourds et utilitaires » dans l'interface |
| Modèle non calibré sur notre scène | L'erreur dépend de l'angle et de la hauteur de la caméra | Réglage par site sur un clip dédié ; fine-tuning en option |
| Caméra fixe obligatoire | Si la caméra bouge, la ligne n'est plus valable | Alerte et vérification visuelle périodique |
| Validé sur 8 clips d'un seul site | Pas de garantie sur d'autres sites | À re-valider à chaque nouveau site |

### Hors périmètre
- Reconnaissance de plaques d'immatriculation.
- Estimation de la vitesse, détection d'infractions, verbalisation.
- Identification ou suivi de personnes.
- Entraînement d'un détecteur depuis zéro.
- Caméras mobiles (drone, véhicule).
- Déploiement industriel multi-sites, haute disponibilité.
- Prévision du trafic futur (extension possible).

---

## Annexe A – Plan de travail et répartition proposée

| Étape | Contenu | Livrable | Responsable proposé |
|---|---|---|---|
| 1 | Tournage des clips, vérité terrain (double comptage + arbitrage) | Clips, CSV de référence, taux d'accord | Les trois membres |
| 2 | Baselines C0 et C1, script d'évaluation | Tableau de baseline | MOHAMED NACER JOURAAI |
| 3 | Pipeline détection + suivi + comptage, tests unitaires | Pipeline fonctionnel | DOUAA AHMITO |
| 4 | Réglage, évaluation complète, analyse par condition, comparaison nano / small et suiveurs | Tableau de résultats, courbes | MOHAMED NACER JOURAAI et DOUAA AHMITO |
| 5 | Fine-tuning (si les critères ne sont pas atteints) | Modèle affiné, comparaison avant / après | YASSIR OUAHLA |
| 6 | Stockage, tableau de bord, alertes, export | Application démontrable | YASSIR OUAHLA |
| 7 | Étude finale, rapport, démonstration | `docs/etude-de-conception.md`, rapport | Les trois membres |

*La répartition est une proposition à ajuster par le groupe.*

## Annexe B – Correspondance avec le modèle de l'énoncé
| Section du modèle | Où dans ce document |
|---|---|
| 1. Contexte et utilisateurs | Section 1 |
| 2. Problème et décision | Section 2 |
| 3. Approche par sous-problème | Section 3 (tableau) et 3.1 (algorithme) |
| 4. Données | Section 4 (tableau) et 4.1 à 4.3 |
| 5. Métriques, baseline, critères d'acceptation | Section 5 |
| 6. Architecture prévue | Section 6 |
| 7. Choix technologiques | Section 7 (tableau Besoin / Outil / Justification) |
| 8. Risques, éthique, confidentialité | Section 8 |
| 9. Limites et hors périmètre | Section 9 |
