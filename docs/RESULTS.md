# Résultats A1.1 : baseline TF-IDF + régression logistique

## Résumé

- **macro-F1 au hasard (80/20, comme `ml/train.py`)** : **0,961** (texte brut). Sert à comparer avec BERT. Gonflé par la fuite : des lignes quasi identiques sont des deux côtés.
- **macro-F1 par groupes, classes réelles** : **0,668 ± 0,130** (texte brut). C'est le chiffre honnête.
- Écart d'environ 0,29 point : c'est la taille de la fuite.

## Protocole

- Données : `data/labeled_logs.csv`, 10 970 lignes (5 sources réelles de 2 000 lignes + 970 synthétiques), 10 catégories.
- Modèle : `TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)` + `LogisticRegression(max_iter=2000, class_weight="balanced")`. Mêmes réglages de classifieur que `ml/train.py`.
- Groupe d'une ligne = son message normalisé (UUID, identifiants hexadécimaux, nombres masqués) : 1 034 groupes.
- Validation croisée : `StratifiedGroupKFold`, 5 plis, `random_state=42`. Les lignes d'un même groupe sont toujours du même côté.
- « Réelles » = hors `source == synthetic`. Les classes `Critical Error`, `Deprecation Warning`, `Unclassified`, `Workflow Error` et presque tout `User Action` sont synthétiques.

## macro-F1

| Protocole | Texte brut | Texte normalisé |
|---|---|---|
| 80/20 au hasard | 0,961 | 0,959 |
| Par groupes, toutes classes | 0,752 ± 0,085 | 0,719 ± 0,089 |
| Par groupes, classes réelles | 0,668 ± 0,130 | 0,624 ± 0,152 |
| Par groupes, classes synthétiques | 0,953 ± 0,043 | 0,933 ± 0,053 |

Le texte normalisé fait un peu moins bien que le brut, mais l'écart est inférieur à l'incertitude : on ne peut pas conclure.

## Par classe (lignes réelles, par groupes, texte brut)

| Classe | Précision | Rappel | F1 | Lignes |
|---|---|---|---|---|
| HTTP Status | 1,00 | 1,00 | 1,00 | 1 017 |
| Security Alert | 1,00 | 0,97 | 0,98 | 2 198 |
| Resource Usage | 0,72 | 0,87 | 0,79 | 114 |
| System Notification | 0,76 | 0,38 | 0,51 | 5 198 |
| Error | 0,35 | 0,32 | 0,34 | 1 463 |
| User Action | 0,00 | 0,10 | 0,00 | 10 |

## Constats vérifiés

- `System Notification` est bien reconnue sur Linux (92 %) et OpenStack (95 %), presque jamais ailleurs : OpenSSH 7 %, Windows 2 %, Apache 0 %.
- Les lignes `System Notification` ratées partent vers `Unclassified` (1 897), `Error` (848) et `User Action` (414). Windows et Apache fournissent 94 % des lignes envoyées vers `Unclassified`.
- Sur 242 formes `System Notification`, 148 sont ratées. Cinq formes (836, 608, 569, 541 et 413 lignes) représentent environ 93 % des lignes mal classées.
- Le mot `user` n'explique pas les 414 lignes envoyées vers `User Action` : une seule le contient. 413 viennent d'OpenSSH.
- `Unclassified` contient des fragments hexadécimaux, `-- MARK --` et `...` (12 formes sur 55 examinées).
- `Error` repose sur des identifiants précis (par exemple un code d'erreur Windows). `Deprecation Warning` et `Workflow Error` reposent sur des mots vides (`the`, `is`, `no`), donc sur le style du générateur.
- `Error` et `System Notification` se confondent dans les deux sens : 618 `Error` prédites `SN`, 848 `SN` prédites `Error`.

## Interprétations (non vérifiées)

- Les lignes ratées sont des formes sans équivalent dans les autres sources, donc le modèle ne généralise pas d'une source à l'autre.
- `Received disconnect ... Bye Bye` est peut-être confondu avec la forme `... disconnected by user`, qui commence par les mêmes mots.
- On ne sait pas pourquoi ces lignes partent vers `Unclassified` plutôt que vers une autre classe.

## Limites

- Le dataset contient environ 1 000 motifs, pas 10 970 exemples indépendants.
- `User Action` n'a que 10 lignes réelles : son score n'est pas exploitable.
- `Resource Usage` n'a que 6 formes.
- Apache n'a que 3 formes `System Notification`.
- Les classes synthétiques mesurent la reconnaissance du générateur, pas de vrais logs.
- Le grand écart-type montre que ces chiffres sont instables.

## Décisions proposées (à valider par Dev B en relecture)

1. **`Unclassified`** : conservée dans l'entraînement de la baseline, pour rester comparable à `ml/train.py`. Elle reçoit environ 23 % des lignes réelles à tort ; le macro-F1 sans cette classe est donné ci-dessous.
2. **Frontière `Error` / `System Notification`** : règle de taxonomie inchangée. La confusion vient surtout d'un manque de diversité (Apache n'a que 3 formes `System Notification`). Piste : faire décider le niveau suivant (LLM) quand la probabilité est faible.
3. **Comparaison avec BERT** : on rapporte les deux protocoles. Le protocole par groupes tranche, le protocole au hasard assure la comparabilité avec `train.py`.

## Limites à traiter dans des tâches séparées

- Plus de vraies lignes pour `User Action` (10 aujourd'hui).
- Remplacer les exemples synthétiques par des lignes réelles (`TAXONOMY_REVIEW.md`, section 6).
- Plus de formes Apache.
- Le dataset doit être versionné : toute comparaison doit se faire sur la même version.


## Reproduire

```
py -m pip install scikit-learn pandas
py -m ml.baseline_tfidf data/labeled_logs.csv
```