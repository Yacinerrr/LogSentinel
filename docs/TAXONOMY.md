# Taxonomie des logs

Ce document définit les catégories utilisées par LogSentinel. Toute étiquette (règles Regex, données d'entraînement, prompt du LLM, revue humaine) doit suivre ces définitions.

## Principes généraux

1. **Une ligne = un log.** On classe selon le sens de la ligne seule, pas selon l'incident auquel elle appartient.
2. **Le niveau du log (`INFO`, `WARNING`, `ALERT`, `FATAL`) est un indice, pas une règle.** C'est le sens du message qui décide.
3. **Un mot isolé ne suffit pas** (`ALERT`, `HTTP`, `error`, `fatal`) : on regarde ce qui s'est réellement passé.
4. **En cas de doute entre deux catégories, on applique l'ordre de priorité ci-dessous.**
5. **`Unclassified` est réservé aux lignes sans catégorie plausible**, jamais à une simple hésitation.
6. **Les exemples marqués ⚠️ synthétique ne viennent pas de vrais logs** et seront remplacés dès qu'une vraie ligne équivalente sera trouvée. Quatre catégories reposent aujourd'hui sur des données synthétiques (`Critical Error`, `Workflow Error`, `Deprecation Warning`, `Unclassified`), ainsi que l'essentiel de `User Action`.

## Ordre de priorité *(à valider)*

| Rang | Catégorie | Idée |
|---|---|---|
| 1 | `HTTP Status` | Le format d'une requête web l'emporte, quel que soit le code |
| 2 | `Security Alert` | Échec d'authentification, accès anonyme ou intrusion signalée |
| 3 | `Critical Error` | Service ou système inutilisable, données perdues |
| 4 | `Workflow Error` | Échec d'une règle ou d'une étape métier |
| 5 | `Error` | Échec technique ou anomalie signalée, sans catégorie plus précise |
| 6 | `Resource Usage` | Quantité mesurée d'une ressource, sans échec |
| 7 | `Deprecation Warning` | Fonction annoncée comme bientôt supprimée |
| 8 | `User Action` | Action d'un utilisateur, sans échec |
| 9 | `System Notification` | Le système décrit simplement ce qu'il fait |
| 10 | `Unclassified` | Aucune des catégories ci-dessus ne convient |

**Règle de lecture** : la catégorie la plus précise gagne sur la plus générale. Une ligne qui correspond à `Error` et à `Resource Usage` (par exemple `No space left on device`) est `Error`, car l'échec l'emporte sur la mesure.

## Règles de cohérence entre jeux de logs

| Situation | Catégorie |
|---|---|
| Format de requête web (méthode, chemin, code) | `HTTP Status` |
| Échec d'authentification, utilisateur inconnu, accès anonyme, intrusion signalée | `Security Alert` |
| Échec technique écrit explicitement (`failed`, code d'erreur) | `Error` |
| Anomalie signalée sans échec franc (`Unknown ...`, `Invalid ...`, `Unrecognized ...`) | `Error` |
| État « désactivé » ou « absent » sans problème signalé | `System Notification` |
| Matériel ou configuration décrits au démarrage | `System Notification` |
| Ouverture ou fermeture de session PAM | `System Notification` |
| Durée ou compteur dans un message de fonctionnement | `System Notification` |
| Connexion réussie annoncée explicitement | `User Action` |
| Déconnexion demandée explicitement par l'utilisateur | `User Action` |

---

## HTTP Status

**Définition** : ligne qui enregistre une requête web, c'est-à-dire qu'elle contient une méthode (`GET`, `POST`...), un chemin (`/login`, `/v2/servers`) et un code de réponse (`200`, `404`, `500`...). Le code n'a pas d'importance : une requête réussie et une requête échouée sont toutes les deux `HTTP Status`.

**Test rapide** : la ligne contient-elle une méthode HTTP, un chemin et un code de réponse ? Si oui, c'est `HTTP Status`. Le simple mot « HTTP » dans un message ne suffit pas.

**Exemples**

1. `10.11.10.1 "GET /v2/54fadb412c4e40cdbaed9335e4c35a9e/servers/detail HTTP/1.1" status: 200 len: 1874 time: 0.2106130`
2. `10.11.10.1 "POST /v2/54fadb412c4e40cdbaed9335e4c35a9e/servers HTTP/1.1" status: 202 len: 733 time: 0.4586949`
3. `10.11.10.1 "POST /v2/e9746973ac574c6b8a9e8857f56a7608/os-server-external-events HTTP/1.1" status: 404 len: 296 time: 0.1146111`
4. `192.168.1.5 - - [12/May/2026:10:21:01] "POST /login HTTP/1.1" 401 532`

**Cas limites**

- **Message d'erreur qui contient seulement le mot « HTTP »** (`HTTP exception thrown: No instances found for any event`) → `Error`, car ce n'est pas une requête web.
- **Code d'erreur (`404`, `401`, `500`) dans une vraie requête** → reste `HTTP Status`.
- **Échec de connexion dans une requête web** (`"POST /login HTTP/1.1" 401`) → `HTTP Status`, pas `Security Alert`.
- **Taille et durée dans une requête** (`len: 1874 time: 0.21`) → `HTTP Status`, pas `Resource Usage`.

---

## Security Alert

**Définition** : ligne qui signale une **tentative d'accès non autorisée, échouée ou sans authentification** : échec d'authentification, compte inexistant, accès anonyme, ou message où le système lui-même signale une intrusion possible. La ligne décrit ce qui s'est passé, qu'une attaque soit réelle ou non.

**Test rapide** : la ligne dit-elle qu'une authentification a échoué, qu'un utilisateur n'existe pas, qu'un accès s'est fait sans identification, ou qu'une intrusion est possible ? Si oui, c'est `Security Alert`. Un mot comme `ALERT` seul ne suffit pas.

**Exemples**

1. `reverse mapping checking getaddrinfo for ns.marryaldkfaczcz.com [173.234.31.186] failed - POSSIBLE BREAK-IN ATTEMPT!`
2. `Invalid user webmaster from 173.234.31.186`
3. `Failed password for root from 5.36.59.76 port 42393 ssh2`
4. `authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=220-135-151-1.hinet-ip.hinet.net  user=root`

**Cas limites**

- **Mot `ALERT` sans lien avec la sécurité** (`logrotate: ALERT exited abnormally with [1]`) → `Error`.
- **Étapes intermédiaires d'une tentative** (`check pass; user unknown`, `input_userauth_request: invalid user ... [preauth]`, `Failed none for invalid user ...`) → `Security Alert`. Chaque ligne est classée selon son propre sens.
- **Préfixe `error:` devant un échec d'authentification** (`error: Received disconnect from ...: Auth fail [preauth]`) → `Security Alert`. Le contenu décide, pas le préfixe.
- **Message répété** (`message repeated 5 times: [ Failed password for root ... ]`) → `Security Alert`.
- **Trop d'échecs ou nombre maximal d'essais** (`Disconnecting: Too many authentication failures`, `PAM service(sshd) ignoring max retries`) → `Security Alert`.
- **Accès sans authentification** (`ANONYMOUS FTP LOGIN FROM ...`) → `Security Alert`, même si rien n'a échoué.
- **Client connecté sans jamais envoyer d'identification** (`Did not receive identification string from ...`) → `Security Alert`. Signature typique d'un scanner de ports.
- **Connexion coupée avant identification** (`Connection closed by ... [preauth]`, `Received disconnect from ...: Bye Bye [preauth]`) → `System Notification`. Aucun échec ni intrusion n'est écrit dans la ligne.
- **Ouverture ou fermeture de session** (`session opened for user cyrus by (uid=0)`) → `System Notification`.
- **Échec d'authentification dans une requête web** (`"POST /login HTTP/1.1" 401`) → `HTTP Status`.
- **Connexion réussie** (`Accepted password for ...`) → `User Action`.

---

## Critical Error

**Définition** : ligne qui signale une **panne grave** : un service ou le système entier est inutilisable, une ressource indispensable est inaccessible, ou des données sont perdues ou corrompues. La différence avec `Error` est la gravité : ici, le fonctionnement normal est interrompu.

**Test rapide** : la ligne dit-elle qu'un service est arrêté, qu'une dépendance vitale (base de données, disque système) est inaccessible, ou que des données sont perdues ? Si oui, c'est `Critical Error`. Un échec limité à une opération, avec un service qui continue de tourner, est une `Error`.

**Exemples** *(aucune vraie ligne dans nos extraits, à remplacer)*

1. `Database connection lost, service down` ⚠️ synthétique
2. `CRITICAL: nginx service stopped unexpectedly and could not be restarted` ⚠️ synthétique
3. `kernel panic - not syncing: Fatal exception in interrupt` ⚠️ synthétique

**Cas limites** *(critère exact à valider)*

- **Mot `CRITICAL` ou `FATAL` sans arrêt réel** (`fatal: Write failed: Connection reset by peer [preauth]`) → `Error`. Une seule opération échoue.
- **Échec isolé d'un programme annexe** (`logrotate: ALERT exited abnormally with [1]`) → `Error`. Le serveur continue de tourner.
- **Manque de ressource** (`No space left on device`) → `Critical Error` si le service s'arrête, `Error` si une seule opération échoue.
- **Attaque qui fait tomber le service** → `Security Alert` si la ligne parle d'accès, `Critical Error` si elle parle de la panne. Une ligne, un sens.

---

## Workflow Error

**Définition** : ligne qui signale l'**échec d'une règle, d'une étape ou d'un processus métier** (ticket, validation, escalade, approbation, automatisation). Le problème vient de la logique de l'application, pas de l'infrastructure : donnée manquante, règle impossible à appliquer, transition interdite.

**Test rapide** : la ligne parle-t-elle d'une règle, d'un ticket, d'une validation ou d'un processus métier qui a échoué ? Si oui, c'est `Workflow Error`. Si l'échec est purement technique (fichier, connexion, programme), c'est `Error`.

**Exemples**

1. `Escalation rule failed for ticket ID 71234: undefined assignee` *(tiré du guide du projet)*
2. `Approval workflow stopped for purchase order 48213: no approver defined` ⚠️ synthétique
3. `Validation failed for invoice 5530: required field 'customer' is empty` ⚠️ synthétique

**Cas limites**

- **Échec technique pendant un processus métier** (`Connection refused` en validant une facture) → `Error`. La cause est technique.
- **Erreur de saisie qui viole une règle métier** (champ obligatoire vide) → `Workflow Error`.
- **Échec qui peut être métier ou technique** → `Error` en cas de doute *(à valider)*.

---

## Error

**Définition** : ligne qui signale qu'une **opération technique a échoué ou qu'une anomalie a été détectée** (plantage, exception, élément introuvable, valeur invalide), sans que le service entier soit arrêté. C'est la catégorie par défaut des échecs qui ne sont ni des tentatives d'accès (`Security Alert`), ni des requêtes web (`HTTP Status`), ni des échecs métier (`Workflow Error`), ni des pannes graves (`Critical Error`).

**Test rapide** : la ligne dit-elle que quelque chose a échoué, a planté, est introuvable, invalide ou anormal, et le reste du système continue-t-il de tourner ? Si oui, c'est `Error`.

**Exemples**

1. `logrotate: ALERT exited abnormally with [1]`
2. `HTTP exception thrown: No instances found for any event`
3. `Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742`
4. `Failed to internally open package. [HRESULT = 0x80070002 - CBS_E_INVALID_PACKAGE]`

**Cas limites**

- **Mot `ALERT` dans un message d'échec interne** → `Error`, pas `Security Alert`.
- **Exception écrite au niveau `INFO`** → `Error`. Le niveau est trompeur.
- **Échec écrit avec un code d'erreur** (`Failed to ...`, `HRESULT = ... E_FAIL`) → `Error`, même si le niveau est `Info` ou `Warning`.
- **Échec réseau ou de connexion** (`getpeername (ftpd): Transport endpoint is not connected`, `warning: can't get client address: Connection reset by peer`) → `Error`.
- **Anomalie signalée sans échec franc** (`Unknown base file`, `Unrecognized packageExtended attribute`, `Invalid ACPI-PCI IRQ routing table`, `notify question section contains no SOA`) → `Error`.
- **État simplement « désactivé » ou « absent »** (`ACPI: Interpreter disabled`, `No Plug & Play device found`) → `System Notification`.
- **Refus par configuration** (`Directory index forbidden by rule: ...`) → `Error`.
- **Échec d'authentification** → `Security Alert`. **Requête web en échec** → `HTTP Status`. **Échec d'un processus métier** → `Workflow Error`. **Échec qui arrête tout le service** → `Critical Error`.
- **Épuisement de ressource qui provoque un échec** (`No space left on device`) → `Error`. L'échec l'emporte sur la mesure.

---

## Resource Usage

**Définition** : ligne qui rapporte une **quantité mesurée** d'une ressource machine (mémoire, disque, CPU, réseau...) : consommation actuelle, quantité libre, total disponible ou limite configurée avec une valeur chiffrée. La ligne décrit l'**état** des ressources, pas un événement ni un échec.

**Test rapide** : la ligne contient-elle un chiffre avec son unité (`MB`, `GB`, `%`, `VCPU`...) qui dit combien d'une ressource est utilisé, libre, disponible ou autorisé ? Si oui, c'est `Resource Usage`.

**Exemples**

1. `[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total memory: 64172 MB, used: 512.00 MB`
2. `[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] memory limit: 96258.00 MB, free: 95746.00 MB`
3. `[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total disk: 15 GB, used: 0.00 GB`
4. `[instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Total vcpu: 16 VCPU, used: 0.00 VCPU`

**Cas limites**

- **Demande de ressources** (`Attempting claim: memory 2048 MB, disk 20 GB, vcpus 1 CPU`) → `System Notification`. Les chiffres sont ce qui est demandé, pas ce qui est utilisé.
- **Limite sans valeur** (`disk limit not specified, defaulting to unlimited`) → `System Notification`.
- **Capacité matérielle détectée au démarrage** (`LOWMEM available`, `CPU: L2 cache: ...`) → `System Notification`. Ce n'est pas un état d'utilisation.
- **Seuil dépassé sans échec** (`Disk usage at 95%`) ⚠️ synthétique → `Resource Usage`, même au niveau `WARNING`.
- **Épuisement qui provoque un échec** (`Out of memory`, `No space left on device`) → `Error`, ou `Critical Error` si le service s'arrête.
- **Chiffres dans une requête web** → `HTTP Status`.
- **Nom de ressource sans mesure** (`Active base files: /var/lib/...`) → `System Notification`.
- **Durée dans un message de fonctionnement** (`Took 1.05 seconds to destroy the instance`) → `System Notification`. Une durée n'est pas une ressource machine.

---

## Deprecation Warning

**Définition** : ligne qui annonce qu'une **fonctionnalité, un module, une API ou une option est obsolète** et sera supprimée ou remplacée dans une version future. Rien n'a échoué pour l'instant : c'est un avertissement à destination des développeurs ou des administrateurs.

**Test rapide** : la ligne exprime-t-elle « bientôt supprimé », « obsolète », « remplacé par », « deprecated » ou « will be removed in version X » ? Si oui, c'est `Deprecation Warning`.

**Exemples**

1. `The 'ReportGenerator' module will be retired in version 4.0` *(tiré du guide du projet)*
2. `DeprecationWarning: get_records() is deprecated and will be removed in version 5.2, use fetch_records() instead` ⚠️ synthétique
3. `WARNING: option 'xmlrpc_port' is deprecated and will be removed in a future release, use 'http_port' instead` ⚠️ synthétique

**Cas limites**

- **Fonction obsolète qui provoque un échec** (`deprecated API call failed`) → `Error`. L'échec l'emporte.
- **Mot `deprecated` dans un nom de fichier ou de variable**, sans avertissement → pas `Deprecation Warning`.
- **Changement déjà effectif** (`module X was removed in 4.0`) → `System Notification`. Ce n'est plus un avertissement sur le futur.

---

## User Action

**Définition** : ligne qui décrit une **action effectuée par un utilisateur** (connexion réussie, déconnexion voulue, création ou modification d'un élément, téléchargement), sans échec ni suspicion. Une connexion réussie annoncée explicitement est une action d'utilisateur, quel que soit le compte, y compris `root`.

**Test rapide** : la ligne dit-elle explicitement qu'une connexion a réussi, ou qu'un utilisateur a fait quelque chose, avec succès ? Si oui, c'est `User Action`. Si c'est le système qui agit seul, c'est `System Notification`.

**Exemples**

1. `User User123 logged in.` *(tiré du guide du projet)*
2. `Accepted password for <utilisateur> from <ip> port <port> ssh2` *(modèle réel du jeu OpenSSH)*
3. `ROOT LOGIN ON tty2` *(jeu Linux)*
4. `Received disconnect from <ip>: <code>: disconnected by user` *(modèle réel du jeu OpenSSH)*

**Cas limites**

- **Ouverture ou fermeture de session PAM** (`session opened for user ... by (uid=...)`, `session closed for user ...`) → `System Notification`, même pour SSH. Le texte seul ne dit pas si c'est une personne ou le système.
- **Déconnexion demandée par l'utilisateur** (`Closed due to user request`, `disconnected by user`) → `User Action`. Le texte le dit explicitement.
- **Connexion réussie annoncée explicitement** (`Accepted password for ...`, `ROOT LOGIN ON tty2`) → `User Action`, y compris pour `root`.
- **Accès sans authentification** (`ANONYMOUS FTP LOGIN`) → `Security Alert`.
- **Échec de connexion** → `Security Alert`, jamais `User Action`.
- **Action automatique lancée par un utilisateur nommé** (`Backup started by admin`) ⚠️ synthétique → `User Action` *(à valider)*.

---

## System Notification

**Définition** : ligne où le **système décrit simplement ce qu'il fait** : démarrage, arrêt, tâche terminée, nettoyage, ouverture de session technique, chargement d'un composant. Aucun échec, aucune mesure de ressource, aucun utilisateur identifié, aucune suspicion. C'est la catégorie la plus générale : tout ce qui n'entre dans aucune catégorie plus précise et qui reste normal.

**Test rapide** : la ligne décrit-elle un fonctionnement normal, sans échec, sans chiffre de ressource, sans utilisateur nommé, sans requête web ? Si oui, c'est `System Notification`.

**Exemples**

1. `Session: 30546354_3233207109 initialized by client WindowsUpdateAgent.`
2. `Read out cached package applicability for package: Package_for_KB2846960~31bf3856ad364e35~amd64~~6.1.1.3, ApplicableState: 80, CurrentState:112`
3. `[instance: b562ef10-ba2d-48ae-bf4a-18666cba4a51] Took 1.05 seconds to destroy the instance on the hypervisor.`
4. `session closed for user cyrus`

**Cas limites**

- **Durée ou chiffre dans un message de fonctionnement** (`Took 1.05 seconds to destroy the instance`) → `System Notification`.
- **Connexion coupée avant identification** (`Connection closed by ... [preauth]`) → `System Notification`.
- **Demande de ressources** (`Attempting claim: memory 2048 MB...`) → `System Notification`.
- **Succès d'une opération technique** (`Deletion of ... complete`, `cupsd startup succeeded`) → `System Notification`.
- **Matériel ou configuration décrits au démarrage** (`CPU: L2 cache: ...`, `HIGHMEM available`, `ACPI: Interpreter disabled`) → `System Notification`.
- **Ouverture ou fermeture de session PAM** → `System Notification`.
- **Anomalie signalée explicitement** (`Unknown base file`) → `Error`, pas `System Notification`.

---

## Unclassified

**Définition** : catégorie de **repli sûr**. On l'utilise quand aucune autre catégorie ne convient, ou quand la ligne est trop courte, tronquée ou ambiguë pour être classée sans deviner. Mieux vaut `Unclassified` qu'une mauvaise étiquette : ces lignes alimentent la file de revue humaine.

**Test rapide** : après avoir parcouru l'ordre de priorité, aucune catégorie ne s'applique sans hésitation forte ? Alors c'est `Unclassified`.

**Exemples** *(aucune vraie ligne dans nos extraits, à remplacer)*

1. `-- MARK --` ⚠️ synthétique
2. `0x3fa2c91b 0x7b10e4d2` ⚠️ synthétique
3. `kernel: xyz 0x3f2a` ⚠️ synthétique

**Cas limites**

- **Ligne coupée ou tronquée** (`6:02 combo sshd...`) → `Unclassified` si le sens n'est plus lisible, sinon la catégorie de la partie lisible *(à valider)*.
- **Ligne dans une langue ou un format inconnu** → `Unclassified`, et ajouter la ligne à la revue humaine.
- **Hésitation entre deux catégories proches** → ne pas utiliser `Unclassified` : appliquer l'ordre de priorité.