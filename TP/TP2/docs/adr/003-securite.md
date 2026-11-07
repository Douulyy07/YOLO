# ADR 003 : transmission de la clé API et origines CORS autorisées

Date : 05/11/2026 · Auteurs : [Douaa-AHMITO _ Nacer JOURAAI _ Yassir OUAHLA]

## Contexte
L'API MaintAI ne doit répondre qu'aux programmes autorisés, et la clé ne doit jamais apparaître dans le code ni dans Git. Une page servie sur `http://localhost:5500` doit pouvoir appeler l'API ; une page servie ailleurs, non.

## Décision 1 : où transmettre la clé ?

### Options étudiées
1. **En-tête `X-API-Key`** : non enregistré dans les journaux ni l'historique ; vérifiable avant de lire les données ; documenté dans `/docs`. Inconvénient : il faut l'autoriser dans CORS (`allow_headers`).
2. **Dans l'URL (`?api_key=...`)** : simple, mais l'URL est enregistrée partout (journaux du serveur, historique du navigateur, en-tête `Referer`) : la clé fuit.
3. **Dans le corps JSON** : mélange authentification et données, impossible en GET, et oblige à modifier `SensorReading` (qui refuse les champs en trop).

### Décision
En-tête `X-API-Key`, vérifié par `require_api_key` sur tout le router `/v1`. La clé est lue depuis `.env` (ignoré par Git) ; `.env.example` est commité avec une fausse valeur.

**Ce que l'autre option ferait perdre :** l'URL ferait perdre le secret ; le corps ferait perdre la séparation entre « qui appelle ? » (401) et « les données sont-elles valides ? » (422).

## Décision 2 : quelles origines autoriser ?

### Options étudiées
1. **Une liste explicite** (`http://localhost:5500,http://127.0.0.1:5500`) : seules les pages connues peuvent appeler l'API depuis un navigateur. Inconvénient : ajouter chaque origine et relancer uvicorn.
2. **`*`** : aucune configuration, mais n'importe quel site ouvert dans le navigateur pourrait appeler l'API.

### Décision
Une liste explicite dans `.env` (`MAINTAI_CORS_ORIGINS`), lue au démarrage par `config.py`.

**Ce que l'autre option ferait perdre :** `*` ferait perdre le contrôle des pages autorisées.

## Conséquences
- Sans clé ou avec une fausse clé : 401, avant la validation des données (500 °C sans clé donne 401). `/health` reste public.
- Serveur lancé sans `.env` : 500 (erreur de configuration du serveur).
- CORS est une règle du navigateur : curl, Java ou Python ne sont pas concernés. La clé reste la vraie protection.
- À surveiller : ne jamais commiter `.env` ; changer la clé si elle fuit ; HTTPS en production.
https://github.com/Douulyy07/YOLO.git