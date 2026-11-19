# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :** …  ·  **Membres :** Douaa Ahmito, …  ·  **Date :** 06/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP2.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Vos cinq requêtes, le code que vous aviez **prévu**, puis le code **obtenu** dans `/docs` :

| Requête | Ce qui ne va pas | Code prévu | Code obtenu |
|---|---|---|---|
| 1 : `POST /v1/predict` sans `load_pct` | champ manquant | 422 | 422 |
| 2 : `POST /v1/predict` avec `"load_pct": 250` | valeur absurde | 422 | 422 |
| 3 : `POST /v1/predict` avec `"temperature_c": "chaud"` | texte au lieu d'un nombre | 422 | 422 |
| 4 : `POST /v1/predict` avec `"pression_bar": 3.0` en plus | champ en trop | 422 | 422 |
| 5 : `POST /v1/predire` (relevé valide) | mauvaise route | 404 | 404 |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

Non. Le cas le plus piégeux est le **champ en trop** : par défaut, Pydantic ignore les champs inconnus et l'API répondrait 200. Ici, `SensorReading` déclare `extra="forbid"`, donc le champ en trop donne 422. Pour la **mauvaise route**, ce n'est pas 422 mais 404 : la route est contrôlée avant les données, et `/v1/predire` n'existe pas.

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
18 passed
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`parametrize` lance la même fonction de test une fois par ligne de la liste `CAS_REFUSES`, avec des arguments différents. On écrit le test une seule fois et on ajoute un cas en ajoutant une ligne. pytest compte **5 tests** pour cette seule fonction (un par cas), chacun nommé dans le rapport (`test_requete_refusee[champ manquant-...]`) : si un cas échoue, on sait lequel.

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
(collez ici la sortie obtenue dans votre TP1 ; après ruff check . --fix et ruff format . : All checks passed!)
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?

`ruff` **lit** le code sans l'exécuter (analyse statique) : imports inutiles (F401), imports mal rangés (I001), variables jamais utilisées, style. `pytest` **exécute** le code et vérifie son comportement : pour telle entrée, la réponse attendue. Un code peut passer ruff et être faux, ou passer pytest et être mal écrit : les deux sont complémentaires.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
2 failed, 16 passed, 1 warning in 1.54s
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?

`test_security.py::test_missing_key_is_rejected` (sans clé) et `test_security.py::test_wrong_key_is_rejected` (fausse clé). Ils reçoivent **200** : la clé n'est encore vérifiée nulle part, donc l'API prédit pour tout le monde.

## 4. La clé API (sprint 1)

Votre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    expected = get_settings().api_key
    if expected is None:
        # Erreur du serveur, pas du client : .env n'a pas été chargé
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La clé API du serveur n'est pas configurée (MAINTAI_API_KEY)",
        )
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API absente ou invalide",
        )
```

Votre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?

Toujours **2** : la fonction existe, mais aucune route ne l'appelle. Tant qu'elle n'est pas déclarée comme dépendance du router, FastAPI ne l'exécute jamais.

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
18 passed, 1 warning in 1.03s
```

Lancez `uvicorn maintai.api.main:app --reload --env-file .env`, puis envoyez ces requêtes (avec `/docs` ou `curl.exe`) :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability":0.0027,"alert":false,"threshold":0.3,"model_version":"2026-11-06T23:37:50Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |

(Relevé normal : `{"temperature_c":60.0,"vibration_mm_s":2.0,"load_pct":50.0,"runtime_hours":5000}`.)

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

Les contrôles se font dans l'ordre route → clé → données → modèle, et le premier qui échoue donne la réponse. Sans clé, la requête est arrêtée à l'étape 2 (401) : l'API ne regarde même pas les données. Avec la bonne clé, elle passe l'étape 2 et c'est le schéma qui refuse 500 °C (422, borne `le=150`).

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

**500** : `{"detail":"La clé API du serveur n'est pas configurée (MAINTAI_API_KEY)"}`. Sans `.env`, `get_settings().api_key` vaut `None` : le serveur n'a aucune clé à laquelle comparer. Ce n'est pas la faute du client (401 dirait « votre clé est mauvaise ») : c'est une erreur de configuration du serveur, donc un code 5xx.

## 5. La page web (sprint 2)

Votre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
document.getElementById("go").addEventListener("click", async () => {
  const reading = Object.fromEntries(FEATURES.map(f => [f, Number(document.getElementById(f).value)]));
  const url = document.getElementById("url").value.trim().replace(/\/+$/, "");
  const cle = document.getElementById("key").value;
  try {
    const resp = await fetch(`${url}/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": cle },
      body: JSON.stringify(reading),
    });
    const data = await resp.json();
    if (!resp.ok) {
      // 401 : clé ; 422 : données refusées ; 503 : modèle absent
      const detail = Array.isArray(data.detail)
        ? data.detail.map(d => `${d.loc.at(-1)} : ${d.msg}`).join(" ; ") // erreurs 422 de Pydantic
        : data.detail;
      show("err", `Erreur ${resp.status} : ${detail}`);
      return;
    }
    const pct = (data.failure_probability * 100).toFixed(1);
    if (data.alert) {
      show("alert", `ALERTE : probabilité de panne ${pct} % (seuil ${data.threshold})`);
    } else {
      show("ok", `Pas d'alerte : probabilité de panne ${pct} % (seuil ${data.threshold})`);
    }
  } catch (e) {
    // API arrêtée, ou CORS qui bloque (page servie depuis une origine non autorisée)
    show("err", `API injoignable (arrêtée, ou bloquée par CORS) : ${e.message}`);
  }
});
```

Ce qu'affiche la page (servie sur le port 5500) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | `Pas d'alerte : probabilité de panne 5.7 % (seuil 0.3)` (60 °C, 2 mm/s) ; avec les valeurs par défaut de la page (72 °C, 6 mm/s, 85 %, 15 000 h) : `ALERTE : probabilité de panne 94.8 % (seuil 0.3)` |
| 500 °C, bonne clé | `Erreur 422 : temperature_c : Input should be less than or equal to 150` |
| relevé normal, fausse clé | `Erreur 401 : Clé API absente ou invalide` |

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

La page affiche `API injoignable (arrêtée, ou bloquée par CORS) : Failed to fetch`. La console affiche :

```
Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
Failed to load resource: net::ERR_FAILED
```

Le navigateur a d'abord envoyé une requête `OPTIONS` (pré-vol) ; l'API a répondu `400 Disallowed CORS origin`, sans en-tête `Access-Control-Allow-Origin`, car `http://localhost:5501` n'est pas dans `MAINTAI_CORS_ORIGINS`. Le navigateur n'a donc jamais envoyé le POST. Depuis 5500, le même pré-vol répond `200` avec `access-control-allow-origin: http://localhost:5500`.

Pourquoi `curl.exe` obtient-il une réponse alors que la page du port 5501 est bloquée ?

CORS est une règle appliquée **par le navigateur**, pour protéger l'utilisateur contre une page qui utiliserait son navigateur pour appeler l'API. `curl.exe` (comme Java ou Python) n'est pas un navigateur : il n'envoie pas de requête `OPTIONS`, n'a pas d'origine et ignore les en-têtes CORS. Seule la clé compte pour lui. CORS n'est donc pas une protection de l'API : la clé reste indispensable.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

**4 échouent**, ils reçoivent **401** au lieu de 422 : la clé est vérifiée avant les données. Le cas **mauvaise route** passe quand même (404) : la route `/v1/predire` n'existe pas, donc la requête est refusée à l'étape 1, avant même la vérification de la clé (la dépendance n'est attachée qu'aux routes existantes du router).

Dernière ligne de `python -m pytest` avec `headers=HEADERS` :

```
23 passed, 1 warning in 1.07s
```

(Le warning vient de la bibliothèque : `StarletteDeprecationWarning` sur `httpx` dans `TestClient`, sans lien avec notre code. `ruff check .` après le sprint 1 : `All checks passed!`)

## 7. Questions de compréhension

1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?
   **401 Unauthorized** : on ne sait pas qui appelle (clé absente ou fausse) : problème d'**authentification**. **422 Unprocessable Content** : le client est identifié, mais les données ne respectent pas le schéma (champ manquant, valeur hors bornes, mauvais type). **403 Forbidden** : on sait qui appelle, mais il n'a pas le droit de faire cette action : problème d'**autorisation** (hors TP2).
2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?
   Le code finit sur GitHub, et une clé commitée une seule fois reste dans l'historique de Git pour toujours, même si on supprime le fichier ensuite (il faut alors changer la clé). `.env` contient la **vraie** clé et les origines, propres à chaque machine : il est ignoré par le `.gitignore` et n'est **jamais** commité. `.env.example` contient les mêmes variables avec une **fausse** valeur (`changez-moi`) : il est **commité** et indique ce qu'il faut configurer.
3. Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?
   Une URL est enregistrée partout : journaux du serveur et des proxys, historique du navigateur, marque-pages, en-tête `Referer`. Une clé dans l'URL fuiterait dans tous ces endroits. Un en-tête n'est pas journalisé par défaut (et il est chiffré avec HTTPS).
4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?
   Il compare en **temps constant** : la durée ne dépend pas du nombre de caractères justes. `==` s'arrête au premier caractère différent ; en mesurant le temps de réponse, un attaquant pourrait deviner la clé caractère par caractère (attaque temporelle, *timing attack*).
5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?
   Une origine est le triplet **schéma + domaine + port**. Non : le port diffère (5500 et 8000), ce sont deux origines différentes. C'est pour cela que la page du port 5500 a besoin que l'API l'autorise par CORS. De même, `localhost:5500` et `127.0.0.1:5500` sont deux origines différentes (d'où les deux entrées dans `.env`).

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? non (il est ignoré par `.gitignore`)
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

…
