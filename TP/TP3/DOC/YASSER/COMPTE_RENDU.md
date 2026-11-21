# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** G1  ·  **Membres :** Yassir Ouahla  ·  **Date :** 21/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP3.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
========================= 5 failed, 18 passed in 2.34s =========================
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

Les deux fichiers qui échouent initialement sont :
- **`tests/test_client.py`** (3 tests en échec : `test_client_returns_prediction`, `test_client_wrong_key_raises_401`, `test_client_bad_reading_raises_422`) : ils lèvent une erreur `NotImplementedError` (ou `AssertionError` / `TypeError`) car la méthode `MaintaiClient.predict()` dans `maintai/client.py` n'est pas encore implémentée.
- **`tests/test_ui.py`** (2 tests en échec : `test_ui_shows_the_data`, `test_ui_shows_the_prediction`) : ils échouent avec une `AssertionError` / `IndexError` (sur `at.metric[0]` et `at.button[0]`) car les composants des onglets « Données » et « Prédiction » dans `ui/app.py` ne sont pas encore codés.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
Traceback:
File "...\TP3\ui\app.py", line 9, in <module>
    from maintai.client import APIError, MaintaiClient
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Lorsque l'on exécute `streamlit run ui/app.py`, Python place uniquement le sous-dossier `ui/` dans le chemin de recherche des modules (`sys.path`), ce qui l'empêche de trouver le paquet `maintai` situé à la racine du projet. En revanche, l'option `python -m streamlit ...` démarre Streamlit en tant que module depuis le répertoire courant : Python ajoute automatiquement le dossier racine du projet (`TP3`) à `sys.path` (et garantit l'utilisation de l'interpréteur de l'environnement virtuel `.venv`), rendant l'import `from maintai...` accessible.

## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :

```python
    c1, c2, c3 = st.columns(3)
    c1.metric("Relevés", f"{len(df)}")
    c2.metric("Taux de panne", f"{df['failure'].mean() * 100:.1f}%")
    c3.metric("Température moyenne", f"{df['temperature_c'].mean():.1f} °C")

    choix_var = st.selectbox("Variable", FEATURES)
    intervalles = pd.cut(df[choix_var], bins=10)
    taux_panne = df.groupby(intervalles, observed=True)["failure"].mean()
    taux_panne.index = taux_panne.index.map(lambda intervalle: round(intervalle.mid))
    st.subheader(f"Taux de panne selon {choix_var}")
    st.bar_chart(taux_panne)

    st.subheader("Température et vibration")
    nuage_df = df.copy()
    nuage_df["panne"] = nuage_df["failure"].replace({0: "non", 1: "oui"})
    st.scatter_chart(nuage_df, x="temperature_c", y="vibration_mm_s", color="panne")
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13.6% |
| Température moyenne | 59.8 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Le taux de panne croît fortement à mesure que la vitesse de vibration augmente. Pour des vibrations faibles (autour de 1 à 3 mm/s), le taux de panne reste très bas (entre 2 % et 10 %). Il grimpe ensuite rapidement à environ 32 % vers 6 mm/s, puis entre 66 % et 84 % pour des vibrations de 8 à 10 mm/s, avant d'atteindre 100 % pour les tranches supérieures à 12 mm/s (certaines tranches extrêmes vers 17-19 mm/s sont à 0 % uniquement parce qu'elles contiennent très peu ou pas de relevés dans la distribution Gamma). La vibration est donc un facteur déterminant du risque de défaillance.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

À chaque modification d'un curseur (ou changement de variable dans la liste déroulante), une nouvelle ligne `relance` s'affiche dans le terminal. Cela illustre le cycle d'exécution de Streamlit : il ne met pas à jour uniquement un composant isolé, mais ré-exécute l'intégralité du script Python `ui/app.py` du début à la fin à chaque interaction de l'utilisateur avec l'interface.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Puisque Streamlit relance tout le script à chaque clic ou déplacement de curseur, la fonction `charger` serait appelée à chaque interaction. Le décorateur `@st.cache_data` mémorise en mémoire vive le `DataFrame` renvoyé pour un chemin de fichier donné (`path`) : la lecture du fichier CSV sur le disque (`pd.read_csv`) n'a lieu qu'au premier chargement, et les exécutions suivantes récupèrent directement le résultat mis en cache, ce qui évite de ralentir l'application.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        en_tetes = {}
        if self.api_key:
            en_tetes["X-API-Key"] = self.api_key
        reponse = self.http.post("/v1/predict", json=reading, headers=en_tetes)
        donnees = reponse.json()
        if not reponse.is_success:
            raise APIError(reponse.status_code, donnees.get("detail"))
        return donnees
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
============================== 23 passed in 2.41s ==============================
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | Métrique `Probabilité de panne : 95 %` accompagnée d'un message d'erreur rouge : `ALERTE : au-dessus du seuil 0.3` |
| valeurs par défaut, fausse clé | Un bandeau d'avertissement jaune (`st.warning`) : `Erreur 401 : Clé API absente ou invalide` |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | Un bandeau d'erreur rouge (`st.error`) : `API injoignable : uvicorn est-il lancé ?` |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

La politique CORS (*Cross-Origin Resource Sharing*) est une restriction de sécurité appliquée exclusivement par les **navigateurs web** lorsqu'une page exécutant du JavaScript (comme `fetch` dans le client web du TP2 sur le port 5500) effectue une requête vers une autre origine (le port 8000). Avec Streamlit, ce n'est pas le navigateur qui appelle l'API FastAPI : le navigateur dialogue uniquement avec le serveur Streamlit (port 8501), et c'est le processus **Python côté serveur** (via `httpx` dans `MaintaiClient`) qui interroge l'API sur le port 8000. Les requêtes HTTP effectuées de serveur à serveur (hors navigateur) ne sont pas soumises aux règles CORS.

## 5. Questions de compréhension

1. Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?
   - **Dans le TP2 (HTML/JS)** : c'est directement le **navigateur web de l'utilisateur** (côté client) qui exécute l'appel `fetch()` en JavaScript vers l'API FastAPI.
   - **Dans le TP3 (Streamlit)** : c'est le **serveur Python Streamlit** (côté backend) qui exécute `MaintaiClient.predict()` avec `httpx` pour interroger l'API FastAPI, puis transmet l'état mis à jour de l'interface au navigateur via WebSocket.
2. Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?
   Le constructeur de `MaintaiClient` accepte un paramètre optionnel `http`. Dans les tests, la fixture `client` (`conftest.py`) injecte une instance de `TestClient(app)` fournie par FastAPI/Starlette. Ce `TestClient` expose la même interface que `httpx.Client` mais achemine les requêtes directement vers l'application ASGI FastAPI en mémoire dans le même processus Python, sans passer par une couche réseau ni démarrer de serveur `uvicorn`.
3. Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?
   - **Pour une démonstration à un client** : je choisirais **Streamlit (TP3)**. En quelques dizaines de lignes de Python pur, sans écrire de HTML/CSS/JS, on obtient un tableau de bord interactif combinant visualisation du jeu de données (indicateurs, histogramme, nuage de points) et simulation de prédiction en direct.
   - **Pour l'application d'un technicien de maintenance** : je choisirais une **interface web HTML + JavaScript (TP2)** (ou un framework frontend dédié). En production sur le terrain, on a besoin d'une interface sur mesure, réactive sur mobile/tablette, qui ne ré-exécute pas tout un script Python côté serveur à chaque interaction et qui communique directement avec l'API.

## 6. Le rendu Git

- Lien de la pull request : …
- Le tag `tp3` existe sur GitHub : oui
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? non (ces fichiers et dossiers sont exclus par `.gitignore`).

## 7. Ce qui reste flou

Le fonctionnement global de Streamlit (modèle de ré-exécution du script, mise en cache avec `@st.cache_data`) ainsi que la distinction entre un appel HTTP depuis le navigateur (soumis à CORS) et un appel depuis le backend Python (`httpx`, non soumis à CORS) sont bien compris.
