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


## A1.2 : classifieur BERT-embedding + seuil de confiance

### Méthode
- Embeddings `BAAI/bge-small-en-v1.5` (texte brut du log), cachés par hash du contenu.
- Classifieur : LogisticRegression (`class_weight="balanced"`), même type que la baseline.
- Évaluation : StratifiedGroupKFold (5 plis, même SEED et mêmes groupes que A1.1).
- Courbe précision/couverture : confiances « hors entraînement » (chaque log est
  prédit par un modèle qui n'a vu ni lui ni son groupe), calculée sur les logs réels uniquement.

### Comparaison avec la baseline (macro-F1, classes réelles)
| Modèle | macro-F1 réelles |
|---|---|
| TF-IDF + LogReg (A1.1) | 0,668 ± 0,130 |
| MiniLM | 0,702 ± 0,083 |
| **bge-small (retenu)** | **0,714 ± 0,113** |
| mpnet | 0,642 ± 0,101 |

bge-small dépasse la baseline en moyenne, mais l'écart (+0,046) est inférieur à
l'écart-type entre plis : on ne peut pas parler de gain net sur ce seul critère.
mpnet, plus gros et plus lent (22 min de calcul contre 7,5), fait moins bien que la baseline.

### Seuil retenu : 0,82
Couverture 36,8 % des logs réels, précision 99,2 % sur les logs acceptés
(graphique : `docs/precision_coverage.png`). Les logs sous le seuil sont à envoyer à l'étape suivante (LLM).

Justification : la précision chute brutalement sous 0,79 (87,5 % à 0,78, 96,8 % à 0,79).
0,82 laisse une marge au-dessus de cette falaise. Entre 0,80 et 0,85, les données ne
permettent pas de départager les seuils (écarts inférieurs à un groupe).

### Limites
- **Échantillon effectif réduit** : 522 groupes distincts pour 10 000 logs réels.
  La falaise de précision vient de 2 groupes seulement (`jk2_init() Found child ...` : 537 logs,
  `Received disconnect ... Bye Bye [preauth]` : 331 logs), tous deux de vrai label
  System Notification, prédits Error et User Action.
- **Couverture dominée par les classes faciles** (mesure au seuil 0,80) : HTTP Status 93 %
  et Security Alert 82 % des logs acceptés, contre 16 % pour Error et pour System Notification
  (67 % des logs réels à elles deux).
- **User Action** : 10 logs réels seulement, classe surtout apprise via le synthétique, aucun
  log réel accepté au seuil 0,80. L'étiquette des logs `Received disconnect` est discutable
  (System Notification ou User Action) ; non re-étiqueté dans cette tâche.
- Le seuil est choisi sur les mêmes données que la courbe : légèrement optimiste.
- La classe Unclassified n'existe que dans le synthétique et n'a pas posé de problème (2 logs
  réels dans la bande suspecte) : conservée.
- Pas encore de courbe précision/couverture pour la baseline TF-IDF : le gain de routage de BERT
  n'est donc pas encore comparé à armes égales.


  ## A1.4 : ingénierie du prompt LLM

**Modèle mesuré : `gemini-3.1-flash-lite` (API Gemini gratuite), mesures du 2 novembre 2026.**
Ce n'est pas DeepSeek R1 : faute de crédits, R1 n'a pas été testé. Les taux ci-dessous ne se transposent pas automatiquement à R1.

### Protocole
- Trois jeux disjoints : exemples du prompt (10 lignes), réglage `tune` (44), final `final` (108). Le jeu final n'a pas été regardé pendant le réglage, et le prompt n'a pas été modifié après sa mesure.
- « Difficile » = confiance BERT sous 0,82, ou prédiction BERT fausse.
- Format attendu : JSON strict `{"label", "reason"}`, un retry (température 0,5), `maxOutputTokens` = 400, température 0 au premier essai.
- Échec de format : JSON invalide, champ manquant, label hors taxonomie, réponse vide ou tronquée. Un label faux est une erreur d'accuracy, pas de format.
- Deux séries : sans sortie structurée forcée, puis avec (`responseSchema`).

### Résultats sur `final` (108 lignes)

| | Sans sortie forcée | Avec sortie forcée |
|---|---|---|
| Échec de format avant retry | 0/108 (0,0 %) | 0/108 (0,0 %) |
| Échec de format après retry | 0/108 (0,0 %) | 0/108 (0,0 %) |
| Réponses coupées (`finish` ≠ STOP) | 0 | 0 |
| Accuracy totale | 99/108 (91,7 %) | 101/108 (93,5 %) |
| Accuracy réelle | 58/64 (90,6 %) | 60/64 (93,8 %) |
| Accuracy synthétique | 41/44 (93,2 %) | 41/44 (93,2 %) |

Critère de la tâche (≥ 95 % parsable, accuracy consignée) : atteint. Le prompt seul donne déjà un format parsable ; la sortie forcée n'apporte pas de gain de format mesurable, et l'écart d'accuracy (2 lignes) est dans le bruit.

### Historique du réglage (`tune`, 44 lignes)
- `v1` : 0 % d'échec de format, 43/44 (97,7 %). Seule erreur : un log signalant une incohérence entre deux sources, classé System Notification au lieu de Error.
- `v2` : définition de Error complétée (« inconsistency between two sources », aussi ajoutée à `docs/TAXONOMY.md`). 43/44 aussi : l'erreur réelle est corrigée, mais une ligne synthétique tronquée change de côté. Sur 44 lignes, `v1` et `v2` ne sont pas distinguables ; `v2` est retenu car sa règle découle de la taxonomie.

### Erreurs sur `final`
Les erreurs se concentrent sur les règles fines de la taxonomie :
- Matériel au démarrage prédit Resource Usage (`On node 0 totalpages`, `126MB LOWMEM available`, `0MB HIGHMEM available`) : 3 lignes.
- Lignes tronquées ou sans sens prédites System Notification au lieu d'Unclassified (`Connection to ... est` ×2, `-- MARK --`) : 3 lignes.
- `fatal: Write failed: Connection reset by peer [preauth]` prédit Security Alert au lieu d'Error : 1 ligne.
- Scanner de ports (`Did not receive identification string`) prédit System Notification au lieu de Security Alert : 2 lignes, uniquement sans sortie forcée.

### Limites
- 108 lignes : incertitude d'environ ±5 points sur l'accuracy ; 0 échec de format sur 108 signifie un taux probablement inférieur à 3 %, pas nul.
- Les logs synthétiques ont été écrits d'après la taxonomie et testés par un LLM : ils sont probablement plus faciles que de vrais logs.
- Les étiquettes réelles viennent des modèles de log, donc certaines sont discutables (lignes tronquées, cas « à valider » de la taxonomie).
- Deux variantes proches (`Connection to ... est`) sont dans le même jeu : une même erreur compte deux fois.
- `tune` a servi au réglage, ses 97,7 % sont optimistes ; la référence est `final`.
- Gemini 3.1 flash-lite n'est pas R1 : le taux de format de R1 reste à mesurer.
- Le quota gratuit et des erreurs 503 ont imposé des relances ; elles n'affectent pas les mesures (seules les réponses reçues sont comptées).