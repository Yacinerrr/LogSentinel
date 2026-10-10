\# Taxonomie des logs



Ce document définit les catégories utilisées par LogSentinel. Toute étiquette (règles Regex, données d'entraînement, prompt du LLM, revue humaine) doit suivre ces définitions.



\## Principes généraux



1\. \*\*Une ligne = un log.\*\* On classe selon le sens de la ligne seule, pas selon l'incident auquel elle appartient.

2\. \*\*Le niveau du log (`INFO`, `WARNING`, `ALERT`) est un indice, pas une règle.\*\* C'est le sens du message qui décide.

3\. \*\*Un mot isolé ne suffit pas\*\* (`ALERT`, `HTTP`, `error`) : on regarde ce qui s'est réellement passé.

4\. \*\*En cas de doute entre deux catégories, on applique l'ordre de priorité ci-dessous\*\*, de la plus prioritaire à la moins prioritaire.

5\. \*\*Les exemples marqués `⚠️ synthétique` ne viennent pas de vrais logs\*\* et doivent être remplacés dès qu'une vraie ligne équivalente est trouvée.



\## Ordre de priorité \*(à valider avec Dev B)\*



| Rang | Catégorie | Idée |

|---|---|---|

| 1 | `HTTP Status` | Le format d'une requête web l'emporte, quel que soit le code |

| 2 | `Security Alert` | Échec d'authentification ou tentative d'intrusion |

| 3 | `Critical Error` | Service ou système inutilisable, données perdues |

| 4 | `Workflow Error` | Échec d'une règle ou d'une étape métier |

| 5 | `Error` | Échec technique qui n'entre dans aucune catégorie plus précise |

| 6 | `Resource Usage` | Quantité mesurée d'une ressource, sans échec |

| 7 | `Deprecation Warning` | Fonction annoncée comme bientôt supprimée |

| 8 | `User Action` | Action d'un utilisateur, sans échec |

| 9 | `System Notification` | Le système décrit simplement ce qu'il fait |

| 10 | `Unclassified` | Aucune des catégories ci-dessus ne convient |



\*\*Règle de lecture\*\* : la catégorie la plus \*\*précise\*\* gagne sur la plus générale. Une ligne qui correspond à `Error` et à `Resource Usage` (ex. : `No space left on device`) est `Error`, car l'échec l'emporte sur la mesure.



\---



\## HTTP Status



\*\*Définition\*\* : ligne qui enregistre une requête web, c'est-à-dire qu'elle contient une méthode (`GET`, `POST`...), un chemin (`/login`, `/v2/servers`) et un code de réponse (`200`, `404`, `500`...). Le code n'a pas d'importance : une requête réussie (`200`) et une requête échouée (`404`) sont toutes les deux `HTTP Status`.



\*\*Test rapide\*\* : la ligne contient-elle une méthode HTTP, un chemin et un code de réponse ? Si oui, c'est `HTTP Status`. Le simple mot « HTTP » dans un message ne suffit pas.



\*\*Exemples\*\*



1\. `10.11.10.1 "GET /v2/54fadb412c4e40cdbaed9335e4c35a9e/servers/detail HTTP/1.1" status: 200 len: 1874 time: 0.2106130`

2\. `10.11.10.1 "POST /v2/54fadb412c4e40cdbaed9335e4c35a9e/servers HTTP/1.1" status: 202 len: 733 time: 0.4586949`

3\. `10.11.10.1 "POST /v2/e9746973ac574c6b8a9e8857f56a7608/os-server-external-events HTTP/1.1" status: 404 len: 296 time: 0.1146111`

4\. `192.168.1.5 - - \[12/May/2026:10:21:01] "POST /login HTTP/1.1" 401 532`



\*\*Cas limites\*\*



\- \*\*Message d'erreur qui contient seulement le mot « HTTP »\*\* (`HTTP exception thrown: No instances found for any event`) → `Error`, car ce n'est pas une requête web.

\- \*\*Code d'erreur (`404`, `401`, `500`) dans une vraie requête\*\* → reste `HTTP Status`.

\- \*\*Échec de connexion dans une requête web\*\* (`"POST /login HTTP/1.1" 401`) → `HTTP Status`, pas `Security Alert`. Le format web est prioritaire.



\---



\## Security Alert



\*\*Définition\*\* : ligne qui signale une \*\*tentative d'accès non autorisée ou échouée\*\* : échec d'authentification, compte inexistant, ou message où le système lui-même signale une intrusion possible. La ligne décrit ce qui s'est passé (quelqu'un a essayé d'entrer et n'a pas réussi), qu'une attaque soit réelle ou non.



\*\*Test rapide\*\* : la ligne dit-elle qu'une authentification a échoué, qu'un utilisateur n'existe pas, ou qu'une tentative d'intrusion est possible ? Si oui, c'est `Security Alert`. Un mot comme `ALERT` seul ne suffit pas.



\*\*Exemples\*\*



1\. `Dec 10 06:55:46 LabSZ sshd\[24200]: reverse mapping checking getaddrinfo for ns.marryaldkfaczcz.com \[173.234.31.186] failed - POSSIBLE BREAK-IN ATTEMPT!`

2\. `Dec 10 06:55:46 LabSZ sshd\[24200]: Invalid user webmaster from 173.234.31.186`

3\. `Dec 10 07:13:43 LabSZ sshd\[24227]: Failed password for root from 5.36.59.76 port 42393 ssh2`

4\. `Jun 15 02:04:59 combo sshd(pam\_unix)\[20882]: authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=220-135-151-1.hinet-ip.hinet.net  user=root`



\*\*Cas limites\*\*



\- \*\*Mot `ALERT` sans lien avec la sécurité\*\* (`logrotate: ALERT exited abnormally with \[1]`) → `Error`. Personne n'attaque, un programme interne a planté.

\- \*\*Étapes intermédiaires d'une tentative\*\* (`check pass; user unknown`, `input\_userauth\_request: invalid user ... \[preauth]`) → `Security Alert`. Chaque ligne est classée selon son propre sens, même si elle fait partie d'une série de 6 ou 7 lignes. \*(à valider avec Dev B)\*

\- \*\*Message répété\*\* (`message repeated 5 times: \[ Failed password for root ... ]`) → `Security Alert`. Le contenu répété décide, pas la mention « repeated ».

\- \*\*Connexion coupée avant identification\*\* (`Connection closed by 212.47.254.145 \[preauth]`, `Received disconnect from ...: 11: Bye Bye \[preauth]`) → `System Notification`. Aucun échec ni intrusion n'est écrit explicitement dans la ligne. \*(à valider avec Dev B)\*

\- \*\*Ouverture ou fermeture de session\*\* (`su(pam\_unix)\[21416]: session opened for user cyrus by (uid=0)`) → `System Notification`. Aucun échec. \*(à valider avec Dev B : `User Action` possible)\*

\- \*\*Échec d'authentification dans une requête web\*\* (`"POST /login HTTP/1.1" 401 532`) → `HTTP Status`. Le format web est prioritaire.

\- \*\*Connexion réussie\*\* (`Accepted password for admin from 10.0.0.2 port 51234 ssh2`, ⚠️ synthétique) → `User Action`. Il n'y a ni échec ni suspicion.



\---



\## Critical Error



\*\*Définition\*\* : ligne qui signale une \*\*panne grave\*\* : un service ou le système entier est inutilisable, une ressource indispensable est inaccessible, ou des données sont perdues ou corrompues. La différence avec `Error` est la \*\*gravité\*\* : ici, le fonctionnement normal est interrompu.



\*\*Test rapide\*\* : la ligne dit-elle qu'un service est arrêté, qu'une dépendance vitale (base de données, disque système) est inaccessible, ou que des données sont perdues ? Si oui, c'est `Critical Error`. Un échec limité à une opération, avec un service qui continue de tourner, est une `Error`.



\*\*Exemples\*\* \*(aucune vraie ligne dans nos extraits, à remplacer)\*



1\. `Database connection lost, service down` ⚠️ synthétique

2\. `CRITICAL: kernel panic - not syncing: Fatal exception` ⚠️ synthétique

3\. `FATAL: could not write to file "pg\_wal/000000010000000000000001": No space left on device` ⚠️ synthétique



\*\*Cas limites\*\* \*(le critère exact est à valider avec Dev B)\*



\- \*\*Mot `CRITICAL` ou `FATAL` sans arrêt réel\*\* (ex. : message `CRITICAL` pour une opération isolée qui a échoué) → `Error`. Le niveau est un indice, pas une règle.

\- \*\*Échec isolé d'un programme annexe\*\* (`logrotate: ALERT exited abnormally with \[1]`) → `Error`, pas `Critical Error`. Le serveur continue de tourner.

\- \*\*Panne causée par un manque de ressource\*\* (`No space left on device` qui bloque le service) → `Critical Error` si le service s'arrête, `Error` si une seule opération échoue.

\- \*\*Attaque qui fait tomber le service\*\* → `Security Alert` si la ligne parle d'accès, `Critical Error` si elle parle de la panne. Une ligne, un sens.



\---



\## Workflow Error



\*\*Définition\*\* : ligne qui signale l'\*\*échec d'une règle, d'une étape ou d'un processus métier\*\* (ticket, validation, escalade, approbation, automatisation). Le problème ne vient pas de l'infrastructure mais de la logique de l'application : donnée manquante, règle impossible à appliquer, transition interdite.



\*\*Test rapide\*\* : la ligne parle-t-elle d'une règle, d'un ticket, d'une validation ou d'un processus métier qui a échoué ? Si oui, c'est `Workflow Error`. Si l'échec est purement technique (fichier, connexion, programme), c'est `Error`.



\*\*Exemples\*\*



1\. `Escalation rule failed for ticket ID 71234: undefined assignee` \*(tiré du guide du projet)\*

2\. `Approval workflow stopped for purchase order PO-2041: no approver defined` ⚠️ synthétique

3\. `Validation failed for invoice 5530: required field 'customer' is empty` ⚠️ synthétique



\*\*Cas limites\*\*



\- \*\*Échec technique dans un processus métier\*\* (`Connection refused` pendant la validation d'une facture) → `Error`. La cause est technique, pas la règle métier.

\- \*\*Erreur de saisie utilisateur\*\* (champ obligatoire vide) → `Workflow Error`, car une règle métier est violée.

\- \*\*Échec d'un module qui pourrait être métier ou technique\*\* → `Error` en cas de doute, et signaler le cas à Dev B pour trancher. \*(à valider avec Dev B)\*



\---



\## Error



\*\*Définition\*\* : ligne qui signale qu'une \*\*opération technique a échoué ou qu'un programme s'est mal comporté\*\* (plantage, exception, élément introuvable, anomalie détectée), sans que le service entier soit arrêté. C'est la catégorie par défaut pour tout échec technique qui n'est ni une tentative d'accès (`Security Alert`), ni une requête web (`HTTP Status`), ni un échec de processus métier (`Workflow Error`), ni une panne grave (`Critical Error`).



\*\*Test rapide\*\* : la ligne dit-elle que quelque chose a échoué, a planté, est introuvable ou est anormal, et le reste du système continue-t-il de tourner ? Si oui, c'est `Error`. Le niveau du log (`INFO`, `WARNING`, `ALERT`) ne décide pas : c'est le sens du message qui compte.



\*\*Exemples\*\*



1\. `Jun 15 04:06:20 combo logrotate: ALERT exited abnormally with \[1]`

2\. `nova-api.log.1.2017-05-16\_13:53:08 2017-05-16 00:01:43.495 25746 INFO nova.api.openstack.wsgi \[req-a0893d5a-dc60-4c49-82e5-b9f7dfc2f6ab f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] HTTP exception thrown: No instances found for any event`

3\. `nova-compute.log.1.2017-05-16\_13:55:31 2017-05-16 00:01:45.116 2931 WARNING nova.virt.libvirt.imagecache \[req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/\_base/a489c868f0c37da93b76227c91bb03908ac0e742`



\*\*Cas limites\*\*



\- \*\*Mot `ALERT` dans un message d'échec interne\*\* (`logrotate: ALERT exited abnormally with \[1]`) → `Error`. Personne n'attaque, un programme a planté.

\- \*\*Exception écrite au niveau `INFO`\*\* (`HTTP exception thrown: No instances found...`) → `Error`. Le niveau est trompeur, le message décrit bien une exception.

\- \*\*Avertissement d'anomalie\*\* (`WARNING ... Unknown base file: ...`) → `Error`. Une anomalie est signalée, même si rien n'a encore planté. \*(à valider avec Dev B : `System Notification` possible)\*

\- \*\*Échec d'authentification\*\* → `Security Alert`, pas `Error`.

\- \*\*Requête web en échec\*\* → `HTTP Status`, pas `Error`.

\- \*\*Échec d'un processus métier\*\* → `Workflow Error`, pas `Error`.

\- \*\*Échec qui arrête tout le service\*\* → `Critical Error`, pas `Error`. \*(à valider avec Dev B)\*

\- \*\*Épuisement de ressource qui provoque un échec\*\* (`No space left on device`) → `Error`. L'échec l'emporte sur la mesure.



\---



\## Resource Usage



\*\*Définition\*\* : ligne qui rapporte une \*\*quantité mesurée\*\* d'une ressource machine (mémoire, disque, CPU, réseau...) : consommation actuelle, quantité libre, total disponible ou limite configurée avec une valeur chiffrée. La ligne décrit l'\*\*état\*\* des ressources, pas un événement ni un échec.



\*\*Test rapide\*\* : la ligne contient-elle un chiffre avec son unité (`MB`, `GB`, `%`, `VCPU`...) qui dit combien d'une ressource est utilisé, libre, disponible ou autorisé ? Si oui, c'est `Resource Usage`.



\*\*Exemples\*\*



1\. `2017-05-16 00:01:53.257 2931 INFO nova.compute.claims \[req-caeb3818-dab6-4e8d-9ea6-aceb23905ebc 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] \[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total memory: 64172 MB, used: 512.00 MB`

2\. `2017-05-16 00:01:53.258 2931 INFO nova.compute.claims \[req-caeb3818-dab6-4e8d-9ea6-aceb23905ebc 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] \[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] memory limit: 96258.00 MB, free: 95746.00 MB`

3\. `2017-05-16 00:01:53.259 2931 INFO nova.compute.claims \[req-caeb3818-dab6-4e8d-9ea6-aceb23905ebc 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] \[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total disk: 15 GB, used: 0.00 GB`

4\. `2017-05-16 00:01:53.260 2931 INFO nova.compute.claims \[req-caeb3818-dab6-4e8d-9ea6-aceb23905ebc 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] \[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total vcpu: 16 VCPU, used: 0.00 VCPU`



\*\*Cas limites\*\*



\- \*\*Demande de ressources\*\* (`Attempting claim: memory 2048 MB, disk 20 GB, vcpus 1 CPU`) → `System Notification`. Les chiffres sont ce qui est \*demandé\*, pas ce qui est utilisé : c'est une action en cours. \*(à valider avec Dev B)\*

\- \*\*Limite sans valeur\*\* (`disk limit not specified, defaulting to unlimited`) → `System Notification`. Aucune quantité chiffrée.

\- \*\*Seuil dépassé sans échec\*\* (`Disk usage at 95%`, ⚠️ synthétique) → `Resource Usage`, même si le niveau du log est `WARNING`.

\- \*\*Épuisement qui provoque un échec\*\* (`Out of memory`, `No space left on device`) → `Error` (ou `Critical Error` si le service s'arrête). L'échec l'emporte.

\- \*\*Chiffres dans une requête web\*\* (`len: 1874 time: 0.21` dans une ligne `GET ... HTTP/1.1`) → `HTTP Status`. Le format web est prioritaire.

\- \*\*Nom de ressource sans mesure\*\* (`Active base files: /var/lib/...`) → `System Notification`.



\---



\## Deprecation Warning



\*\*Définition\*\* : ligne qui annonce qu'une \*\*fonctionnalité, un module, une API ou une option est obsolète\*\* et sera supprimée ou remplacée dans une version future. Rien n'a échoué pour l'instant : c'est un avertissement à destination des développeurs ou des administrateurs.



\*\*Test rapide\*\* : la ligne contient-elle une idée de « bientôt supprimé », « obsolète », « remplacé par », « deprecated » ou « will be removed in version X » ? Si oui, c'est `Deprecation Warning`.



\*\*Exemples\*\*



1\. `The 'ReportGenerator' module will be retired in version 4.0` \*(tiré du guide du projet)\*

2\. `DeprecationWarning: the imp module is deprecated in favour of importlib` ⚠️ synthétique

3\. `WARNING: option 'xmlrpc\_port' is deprecated and will be removed in a future release, use 'http\_port' instead` ⚠️ synthétique



\*\*Cas limites\*\*



\- \*\*Fonction obsolète qui provoque un échec\*\* (`deprecated API call failed`) → `Error`. L'échec l'emporte.

\- \*\*Mot `deprecated` dans un nom de fichier ou de variable\*\* sans message d'avertissement → pas `Deprecation Warning`. La ligne doit annoncer une suppression ou un remplacement.

\- \*\*Changement de version déjà effectif\*\* (`module X was removed in 4.0`) → `System Notification`. Ce n'est plus un avertissement sur le futur.



\---



\## User Action



\*\*Définition\*\* : ligne qui décrit une \*\*action effectuée par un utilisateur identifié\*\* (connexion réussie, déconnexion, création ou modification d'un élément, téléchargement), sans échec ni suspicion.



\*\*Test rapide\*\* : la ligne nomme-t-elle un utilisateur qui a fait quelque chose, avec succès ? Si oui, c'est `User Action`. Si c'est le système qui agit seul, c'est `System Notification`.



\*\*Exemples\*\* \*(aucune vraie ligne dans nos extraits, à remplacer)\*



1\. `User User123 logged in.` \*(tiré du guide du projet)\*

2\. `User admin logged out.` ⚠️ synthétique

3\. `Accepted password for admin from 10.0.0.2 port 51234 ssh2` ⚠️ synthétique



\*\*Cas limites\*\*



\- \*\*Ouverture de session système\*\* (`su(pam\_unix): session opened for user cyrus by (uid=0)`) → `System Notification`. Le compte `cyrus` est un compte de service, ce n'est pas une personne. \*(à valider avec Dev B)\*

\- \*\*Action automatique lancée par un utilisateur\*\* (ex. : `Backup started by admin`) → `User Action` si l'utilisateur est nommé comme auteur. \*(⚠️ synthétique, à valider avec Dev B)\*

\- \*\*Échec de connexion\*\* → `Security Alert`, jamais `User Action`.



\---



\## System Notification



\*\*Définition\*\* : ligne où le \*\*système décrit simplement ce qu'il fait\*\* : démarrage, arrêt, tâche terminée, nettoyage, ouverture de session technique, chargement d'un composant. Aucun échec, aucune mesure, aucun utilisateur identifié, aucune suspicion. C'est la catégorie la plus générale : tout ce qui n'entre dans aucune catégorie plus précise et qui reste normal.



\*\*Test rapide\*\* : la ligne décrit-elle un fonctionnement normal du système, sans échec, sans chiffre de ressource, sans utilisateur nommé, sans requête web ? Si oui, c'est `System Notification`.



\*\*Exemples\*\*



1\. `2016-09-29 02:04:27, Info                  CBS    Session: 30546354\_3233207109 initialized by client WindowsUpdateAgent.`

2\. `2016-09-29 02:04:27, Info                  CBS    Read out cached package applicability for package: Package\_for\_KB2846960\~31bf3856ad364e35\~amd64\~\~6.1.1.3, ApplicableState: 80, CurrentState:112`

3\. `nova-compute.log.1.2017-05-16\_13:55:31 2017-05-16 00:01:40.979 2931 INFO nova.compute.manager \[req-31d09752-6f82-4fc5-ac97-416b9c865af4 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] \[instance: b562ef10-ba2d-48ae-bf4a-18666cba4a51] Took 1.05 seconds to destroy the instance on the hypervisor.`

4\. `Jun 15 04:06:19 combo su(pam\_unix)\[21416]: session closed for user cyrus`



\*\*Cas limites\*\*



\- \*\*Durée ou chiffre dans un message de fonctionnement\*\* (`Took 1.05 seconds to destroy the instance`) → `System Notification`. Un chiffre ne suffit pas pour `Resource Usage` : il faut une quantité de \*\*ressource machine\*\* (mémoire, disque, CPU).

\- \*\*Connexion coupée avant identification\*\* (`Connection closed by 212.47.254.145 \[preauth]`) → `System Notification`. \*(à valider avec Dev B : `Security Alert` possible)\*

\- \*\*Demande de ressources\*\* (`Attempting claim: memory 2048 MB...`) → `System Notification`, car ce sont des chiffres demandés et non mesurés. \*(à valider avec Dev B)\*

\- \*\*Succès d'une opération technique\*\* (`Deletion of /var/lib/nova/instances/...\_del complete`) → `System Notification`.

\- \*\*Avertissement d'anomalie\*\* (`WARNING ... Unknown base file`) → classé `Error` pour l'instant, mais `System Notification` reste possible. \*(à valider avec Dev B)\*



\---



\## Unclassified



\*\*Définition\*\* : catégorie de \*\*repli sûr\*\*. On l'utilise quand aucune autre catégorie ne convient, ou quand la ligne est trop courte, tronquée ou ambiguë pour être classée sans deviner. Mieux vaut `Unclassified` qu'une mauvaise étiquette : ces lignes alimentent la file de revue humaine.



\*\*Test rapide\*\* : après avoir parcouru l'ordre de priorité, aucune catégorie ne s'applique sans hésitation forte ? Alors c'est `Unclassified`.



\*\*Exemples\*\* \*(aucune vraie ligne dans nos extraits, à remplacer)\*



1\. `-- MARK --` ⚠️ synthétique

2\. `ok` ⚠️ synthétique

3\. `Jun 15 12:12:34 combo kernel: xyz 0x3f2a` ⚠️ synthétique



\*\*Cas limites\*\*



\- \*\*Ligne coupée ou tronquée\*\* (comme la première ligne de l'extrait Linux, qui commence par `6:02 combo sshd...`) → `Unclassified` si le sens n'est plus lisible, sinon la catégorie correspondant à la partie lisible. \*(à valider avec Dev B)\*

\- \*\*Ligne dans une langue ou un format inconnu\*\* → `Unclassified`, et ajouter la ligne à la revue humaine.

\- \*\*Hésitation entre deux catégories proches\*\* → ne \*\*pas\*\* utiliser `Unclassified` : appliquer l'ordre de priorité. `Unclassified` est réservé aux cas sans catégorie plausible.

