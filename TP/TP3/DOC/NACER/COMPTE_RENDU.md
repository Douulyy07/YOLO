# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Date :** 12/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP3.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
======================================================= 5 failed, 18 passed, 1 warning in 10.31s =======================================================
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

- `tests/test_client.py` (3 tests) échoue avec `NotImplementedError: TP3 sprint 2 : MaintaiClient.predict` : la méthode `predict` du client n'est pas encore écrite, elle ne fait que lever cette erreur.
- `tests/test_ui.py` (2 tests) échoue avec `IndexError: list index out of range` : la page n'affiche encore aucun `st.metric`, donc la liste `at.metric` est vide quand le test lit `at.metric[0]` ou `at.metric[-1]`.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Python cherche les modules dans une liste de dossiers (`sys.path`), et cette liste dépend de la façon de lancer le programme. Avec `streamlit run ui/app.py`, Python cherche d'abord dans le dossier du script, c'est-à-dire `TP3\ui\`, où il n'y a pas de dossier `maintai\`. Avec `python -m streamlit run ui/app.py`, Python ajoute le dossier **courant** (`TP3\`) à la liste, et `maintai\` s'y trouve : l'import `from maintai.client import ...` réussit. Cela ne marche donc que si on lance la commande depuis `TP3`.

## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :

```python
    c1, c2, c3 = st.columns(3)
    c1.metric("Relevés", len(df))
    c2.metric("Taux de panne", f"{df.failure.mean():.1%}")
    c3.metric("Température moyenne", f"{df.temperature_c.mean():.1f} °C")

    variable = st.selectbox("Variable", FEATURES)
    tranches = pd.cut(df[variable], bins=10)
    taux = df.groupby(tranches, observed=True).failure.mean()
    taux.index = [round(i.mid) for i in taux.index]
    st.subheader(f"Taux de panne selon {variable}")
    st.bar_chart(taux)

    st.subheader("Température et vibration")
    df_nuage = df.assign(panne=df.failure.map({0: "non", 1: "oui"}))
    st.scatter_chart(df_nuage, x="temperature_c", y="vibration_mm_s", color="panne")
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13,6 % |
| Température moyenne | 59,7 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Le taux de panne augmente très fortement avec la vibration. Il est d'environ 2 % pour les vibrations autour de 1 mm/s, 10 % vers 3 mm/s, 32 % vers 6 mm/s, puis 66 % vers 8 mm/s et 84 % vers 10 mm/s. Au-delà d'environ 12 mm/s, toutes les machines tombent en panne (100 %). La courbe monte vite et finit par atteindre le maximum. En comparaison, la température fait monter le taux de panne de 0 % (vers 27 °C) à environ 37 % (vers 90 °C) seulement. La variable qui compte le plus est donc la **vibration**.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

Le mot « relance » s'affiche dans le terminal à chaque action sur la page (changement de la liste déroulante, etc.). Cela montre que Streamlit **relance tout le script `ui/app.py`**, de la première à la dernière ligne, à chaque interaction avec un widget. Les curseurs placés dans un `st.form` font exception : ils ne relancent rien tant qu'on ne clique pas sur « Prédire ».

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Comme Streamlit relance tout le script à chaque clic, sans cache le fichier CSV serait relu à chaque fois. Avec `@st.cache_data`, le CSV n'est lu qu'à la première exécution ; ensuite Streamlit renvoie le même tableau gardé en mémoire. La page reste rapide.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        r = self.http.post("/v1/predict", json=reading, headers=headers)
        if r.status_code != 200:
            raise APIError(r.status_code, r.json().get("detail"))
        return r.json()
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
COLLER ICI la dernière ligne de votre pytest (attendu : 23 passed)
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | « Probabilité de panne : 95 % » et un message d'alerte rouge « ALERTE : au-dessus du seuil 0.3 » |
| valeurs par défaut, fausse clé | un avertissement jaune « Erreur 401 : » suivi du message de l'API (clé absente ou invalide) |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | une erreur rouge « API injoignable : uvicorn est-il lancé ? » |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

CORS est une règle appliquée par le **navigateur**. En TP2, `fetch(...)` s'exécutait dans le navigateur : celui-ci demandait la permission à l'API (requête OPTIONS avec l'en-tête `Origin`) et bloquait la réponse si l'origine n'était pas dans la liste autorisée. Avec Streamlit, le navigateur ne fait qu'afficher la page et n'appelle jamais l'API. C'est le **serveur Streamlit (du code Python avec `httpx`)** qui envoie la requête, comme le ferait `curl` ou le programme Java. Il n'y a pas de navigateur dans cet échange, donc pas de contrôle CORS. La clé API, elle, reste vérifiée par l'API.

## 5. Questions de compréhension

1. Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?

   Dans la page web du TP2, c'est le **navigateur** de l'utilisateur (le JavaScript `fetch` qui s'exécute dedans). Dans Streamlit, c'est le **serveur Streamlit**, c'est-à-dire du code Python (`MaintaiClient`, avec `httpx`). Le navigateur affiche seulement la page.

2. Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?

   `MaintaiClient` accepte un client HTTP en paramètre (`http=`). Les tests lui donnent le `TestClient` de FastAPI, qui envoie les requêtes **directement à l'application en mémoire**, sans passer par le réseau ni par un serveur. Le code testé est le même (`self.http.post(...)`), mais il n'y a pas besoin de lancer uvicorn. C'est pour cela que `predict` doit utiliser `self.http` et non `httpx.post`.

3. Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?

   Pour une **démonstration à un client**, je choisirais la page HTML + JavaScript : on contrôle entièrement l'apparence (logo, couleurs, mise en page), ce qui donne une image plus professionnelle et personnalisée. Pour l'**application d'un technicien de maintenance**, je choisirais Streamlit : elle est écrite entièrement en Python (pas besoin de connaître JavaScript), se développe vite, et propose déjà des graphiques, des formulaires et des onglets. L'outil est interne, donc un design standard suffit. Le prix à payer est une interface moins personnalisable.

## 6. Le rendu Git

- Lien de la pull request : À COMPLÉTER
- Le tag `tp3` existe sur GitHub : À COMPLÉTER (oui / non)
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? À COMPLÉTER (oui / non)

## 7. Ce qui reste flou

À COMPLÉTER avec ce qui reste flou pour vous (par exemple : la différence exacte entre `st.cache_data` et un simple appel de fonction, ou le moment précis où CORS intervient).
