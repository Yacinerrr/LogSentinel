# Jeu de test figé (A1.3)



`data/test.csv` est le jeu de test held-out du projet. **Il ne sert jamais à entraîner, à régler un hyperparamètre ni à choisir un seuil.** Il n'est utilisé que pour l'évaluation finale.



## Contenu



480 lignes : 304 réelles et 176 artificielles (colonne `source`, `synthetic` pour les artificielles).



| Catégorie | Réelles | Artificielles |

|---|---|---|

| Critical Error | 0 | 20 |

| Deprecation Warning | 0 | 24 |

| Error | 4 | 23 |

| HTTP Status | 68 | 20 |

| Resource Usage | 20 | 0 |

| Security Alert | 63 | 23 |

| System Notification | 149 | 0 |

| Unclassified | 0 | 23 |

| User Action | 0 | 23 |

| Workflow Error | 0 | 20 |



## Construction (`ml/make_test_set.py`)



**Partie réelle (90 formes)**

- Tirage par formes entières (colonne `groupe`, message normalisé) : 20 % des formes de chaque catégorie. Aucune ligne d'une forme de test n'existe dans l'entraînement.

- Catégories à moins de 5 formes réelles : pas de test réel.

- Formes déjà reconnues par `config/regex_rules.json` : exclues, car le test mesure ce que Regex ne résout pas.

- Maximum 20 lignes distinctes par forme ; lignes identiques supprimées.



**Partie artificielle (176 lignes)**

- Deux lots générés par un LLM, avec un prompt différent de celui des données d'entraînement (`data/logsentinel_synthetic_logs.csv` et `_2.csv`).

- Lignes trop proches de l'entraînement retirées (similarité cosinus TF-IDF ≥ 0,70), ainsi que les cas non tranchés (« unrecognized parameter », « invalid timestamp », « unknown execution mode »).

- Étiquettes relues à la main ; 9 lignes ambiguës retirées des fichiers sources (accès FTP anonyme, connexions SSH/base de données, erreurs de permission).



## Utilisation



- Tout entraînement charge ses données via `ml.split.train_sans_test()`.

- `py -m pytest tests/test_no_leak.py` échoue si une forme ou une ligne est commune au train et au test.

- Ne régénère pas ce fichier à la légère : il dépend de `labeled_logs.csv`, des règles Regex et de la seed (`SEED`, dans `ml/common.py`). Toute régénération invalide les scores déjà publiés.



SHA-256 de `data/test.csv` : `<coller ici>`



## Limites connues



- **Cinq catégories sont testées uniquement sur des logs artificiels** : Critical Error, Workflow Error, Deprecation Warning, Unclassified, User Action. Leurs scores mesurent la généralisation vers le style d'un autre LLM, pas vers de vrais logs.

- **`Error` réel : 4 lignes seulement.** 20 formes sur 23 n'ont qu'une ligne distincte dans les données ; le test `Error` repose surtout sur les 23 lignes artificielles.

- **`Resource Usage` : une seule forme de test** (6 formes réelles au total), répétée avec des variantes d'identifiants. Score fragile.

- `User Action` n'a que 4 formes réelles (sous le seuil de 5) : pas de test réel.

- Les étiquettes artificielles ont été relues par une seule personne.

