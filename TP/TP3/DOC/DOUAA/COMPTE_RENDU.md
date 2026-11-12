# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** G1  ·  **Membres :** DOUAA AHMITO  ·  **Date :** 12/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP3.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
5 failed, 18 passed
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

- `tests/test_client.py` (3 tests : `test_client_returns_prediction`, `test_client_wrong_key_raises_401`, `test_client_bad_reading_raises_422`) : **`NotImplementedError`**, car `MaintaiClient.predict` n'est pas encore écrite.
- `tests/test_ui.py` (2 tests : `test_ui_shows_the_data`, `test_ui_shows_the_prediction`) : **`IndexError: list index out of range`**. Les tests cherchent `at.metric[0]` et `at.metric[-1]`, mais la page n'affiche encore aucun indicateur (seulement les `st.info` du starter), donc la liste des métriques est vide.


## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

streamlit run cherche les modules dans le dossier du script (ui/), où il n'y a pas maintai. python -m ajoute le dossier courant (TP3/), qui contient maintai

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

    nuage = df.assign(panne=df.failure.map({0: "non", 1: "oui"}))
    st.subheader("Température et vibration")
    st.scatter_chart(nuage, x="temperature_c", y="vibration_mm_s", color="panne")
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés |5000 |
| Taux de panne | 13.6%|
| Température moyenne | |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

le taux de panne monte très vite. Avec la température, il ne dépasse pas 37 %. La vibration compte le plus.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

il s'affiche à chaque changement dans la liste déroulante : Streamlit relance tout le script à chaque interaction. Les curseurs de « Prédiction » n'affichent rien , seul le bouton « Prédire » relance.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

le CSV n'est lu qu'une seule fois au lieu d'être relu à chaque relance.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        r = self.http.post("/v1/predict", json=reading, headers=headers)
        if r.status_code != 200:
            raise APIError(r.status_code, r.json().get("detail"))
        return r.json()
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
23 passed
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé |95 % et ALERTE : au-dessus du seuil 0.3 |
| valeurs par défaut, fausse clé |Erreur 401 : Clé API absente ou invalide |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) |API injoignable : uvicorn est-il lancé ? |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

Pourquoi pas de CORS : CORS est une règle du navigateur. Ici, c'est le serveur Streamlit (Python) qui appelle l'API, comme curl : pas de contrôle CORS. La clé reste vérifiée.

## 5. Questions de compréhension

1. Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?
   Au TP2, c'est le navigateur qui envoie la requête (fetch). Dans Streamlit, c'est le serveur Python, avec MaintaiClient.
2. Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?
   Les tests donnent le TestClient de FastAPI à MaintaiClient (paramètre http) : la requête va directement à l'application, sans serveur.
3. Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?
   Démonstration : Streamlit, rapide à faire en Python, sans JavaScript. Technicien : une page HTML/JS, plus légère et plus facile à adapter à son usage.


