# TP — Ingestion et analyse de logs avec Logstash (EISI, 1 jour) dans TP2


Les apprenants ajoutent Logstash à la stack du TP d'introduction. Ils l'utilisent d'abord pour recharger les 5 000 offres d'emploi, puis pour transformer les logs d'accès du site de recrutement en événements structurés. Ils mènent ensuite une enquête dans Kibana et livrent un tableau de bord.

Livrable : `requetes/logstash.txt`; `logstash/pipeline/offres.conf`; `REPONSES_TP2.md`;`logstash/pipeline/web.conf`;`requetes/enquetes.txt`.  

## Introduction et Mise en place

Architecture du TP :   
![architecture TP](/TP2/image/architecture.PNG)  

## Étapes de mise en route

> 1. Ajouter au fichier `.env` le mot de passe du futur compte Logstash :
> 
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(16))"
> # puis dans .env : LOGSTASH_INTERNAL_PASSWORD=<valeur générée>
> ```
> 
> 2. Vérifier que la stack du TP d'introduction tourne et que l'index `offres` existe :
> 
> ```bash
> docker compose up -d
> docker compose ps                    # elasticsearch et kibana "healthy"
> ```
> 
> ```text
> GET offres/_count                    # attendu : 5000
> ```
> 
> 3. Dans Kibana Dev Tools, créer un rôle limité aux besoins de Logstash, puis l'utilisateur qui le porte (même mot de passe que dans `.env`) :
> 
> ```text
> POST _security/role/logstash_writer
> {
>   "cluster": ["monitor", "manage_index_templates"],
>   "indices": [
>     { "names": ["offres", "logs-web-*"],
>       "privileges": ["write", "create", "create_index", "auto_configure"] }
>   ]
> }
> 
> POST _security/user/logstash_internal
> { "password": "<LOGSTASH_INTERNAL_PASSWORD>", "roles": ["logstash_writer"],
>   "full_name": "Logstash - ingestion" }
> ```
> 
> Enregistrez ces requêtes dans `requetes/logstash.txt`, **sans** le mot de passe.

Vérification de la création : 
```bash
GET _security/role/logstash_writer
GET _security/user/logstash_internal
```

![Logstash](/TP2/image/testDroitRole1.PNG)  
![Logstash 1](/TP2/image/testDroitRole.PNG)  

> 4. Observer le service ajouté : il est rattaché au **profil** Compose `logstash`, donc > > `docker compose up -d` ne le démarre pas ; il faut le nommer (`docker compose up -d logstash`).

### Note sur l'organisation du dépôt et le montage des volumes

Le kit TP2 est rangé dans `TP2/kit-TP_2/` au lieu de la racine. Or les chemins de `docker-compose.override.yml` sont relatifs au dossier du fichier compose, donc à la racine. Au premier lancement, `./logstash/config/pipelines.yml` était introuvable : Docker a créé à sa place un dossier vide du même nom, puis a échoué à le monter sur un fichier du conteneur (erreur `not a directory`).

**Correction :**
- suppression du dossier vide créé par Docker ;
- chemins des volumes adaptés à l'arborescence (`./TP2/kit-TP_2/logstash/config/pipelines.yml` et `./TP2/kit-TP_2/logstash/pipeline`) ;
- `./data` conservé à la racine (il contient `offres.ndjson`) et `access.log` généré dans ce dossier avec `--sortie data\access.log` ;
- conteneur recréé avec `docker compose up -d --force-recreate logstash`, puisqu'un simple `restart` ne prend pas en compte une modification du fichier compose.

**À retenir :** un volume monté sur un chemin hôte inexistant est créé comme dossier vide. Il faut donc vérifier la configuration fusionnée avec `docker compose config` avant le lancement.  



### Questions

 pourquoi ne pas utiliser le compte `elastic` pour Logstash ? Que se passerait-il si le pipeline `web` tentait d'écrire dans `logs-generic-default` ? Pourquoi le mot de passe est-il transmis par variable d'environnement plutôt qu'écrit dans les fichiers `.conf` ?

- Pourquoi pas `elastic` ? C'est un super-utilisateur : s'il fuit (fichier, log, conteneur compromis), tout le cluster est exposé.  Principe de moindre privilège : `logstash_internal` ne peut qu'écrire dans `offres` et `logs-web-*`.  
- Écrire dans `logs-generic-default` ? Le rôle ne couvre pas ce nom : Elasticsearch répond 403 `security_exception`. Rien n'est écrit, l'erreur apparaît dans les journaux de Logstash.  
- Mot de passe par variable d'environnement : les `.conf` sont versionnés dans Git, `.env` ne l'est pas. On peut aussi changer le mot de passe sans toucher au pipeline.  

### Exercice 0

Champs ajoutés : `@timestamp`, `@version`, `host.hostname` (nom du conteneur), `event.original` (copie de la ligne) en plus de message. Le filtre ne met en majuscules que `message`.  
`@timestamp` = c'est l'heure de réception par Logstash, pas l'heure du fait décrit.  
`--path.data /tmp/essai` : le dossier de données par défaut (`/usr/share/logstash/data`, volume `lsdata`) est verrouillé par l'instance qui l'utilise. Un second Logstash qui pointerait dessus refuserait de démarrer ou mélangerait son état avec l'autre.  

## Partie 1 Recharger les offres avec Logstash

### 1.2 Premier lancement (snas le `mutate`)  

Aucun document n'est indexé : chaque événement reçoit `400 strict_dynamic_mapping_exception`.  
Les champs cités sont `@timestamp`, `@version`, `event`, `log` et `host`, tous ajoutés par Logstash.  
C'est le verrou `"dynamic": "strict"` du TP1 (exercice 1.4) qui les refuse.  

### 1.3 Corriger (avec le `mutate`)
```bash
docker compose restart logstash
```  

Dans Dev Tools : GET offres/_count puis GET offres/_doc/OFF-00002.  

`_count` reste 5 000 : l'`_id` est le même, donc chaque document est remplacé. Le `_version` de `OFF-00002` augmente de 1.
On supprime ces champs plutôt que d'assouplir le mapping, car ce sont des métadonnées de transport sans valeur métier. Le mapping strict reste un contrat.  
L'index doit exister avant le premier démarrage. Avec `manage_template => false` et le droit `create_index`, Elasticsearch le créerait en mapping dynamique : `localisation` ne serait plus un `geo_point`, il n'y aurait plus d'analyseur français ni de verrou.  

### 1.4 Relancer 

Le fichier est relu à chaque démarrage, car la sincedb `/dev/null` ne garde aucune mémoire. `_count` reste à 5 000 et `_version` augmente de 1.  
Avec la sincedb par défaut, la position est mémorisée : rien n'est relu.  
Sans `document_id`, chaque démarrage ajoute 5 000 doublons.  


## Partie 2 Superviser et fiabiliser  

### 2.1 Supervision  

```bash
curl.exe "http://localhost:9600/?pretty"
curl.exe "http://localhost:9600/_node/pipelines?pretty"
curl.exe "http://localhost:9600/_node/stats/pipelines/offres?pretty" 
```
Le JSON s'affiche dans le terminal. Les mêmes adresses s'ouvrent aussi dans un navigateur.  


2 pipelines (`offres` et `web`), chacun avec autant de workers que de cœurs CPU.
Pour `offres : in = filtered = out = 5000`. Ce sont des compteurs depuis le dernier démarrage.  
Le plugin le plus coûteux est en général la sortie `elasticsearch`, à cause de l'attente réseau des requêtes `_bulk`.  

### 2.2 Dead letter queue  

Le document est-il indexé ? Non : `GET offres/_doc/OFF-99999` renvoie `found: false`, et `_count reste` à 5 000.  
Où est-il ? Dans `/usr/share/logstash/data/dead_letter_queue/offres/`.
Raison du refus : `400 strict_dynamic_mapping_exception`, dynamic introduction of [prime].  
Apport par rapport à `raise_on_error=False` : la DLQ conserve le document complet sur disque, avec sa raison, et permet de le rejouer.  
Correction en trois étapes :  
1. relire la DLQ avec l'entrée `dead_letter_queue` ;  
2. corriger avec `mutate { remove_field => ["prime"] }`, ou ajouter `prime` au mapping si le champ est légitime;  
3. renvoyer vers `offres` avec `document_id => "%{id}"` et `commit_offsets => true`.  

### 2.3 Pourquoi deux pipelines  

Sans `pipelines.yml` : un seul pipeline `main`, qui concatène les deux `.conf`.  
Une offre : elle traverse tous les filtres (avec un `_grokparsefailure`) et part vers les deux destinations.  
Une ligne de log : elle part aussi vers `offres`, avec un `_id` littéral `%{id}`, et se fait rejeter.  
Autres avantages : isolation des pannes et de la contre-pression, réglages propres à chacun, supervision séparée, lisibilité. On l'a d'ailleurs constaté : une erreur commune (le 401) arrête les deux pipelines, car ils partagent le même compte.  

### 2.4 Ne rien perdre (réflexion) 

File en mémoire et `docker kill` : les événements en vol sont perdus.
Réglage à changer : `queue.type: persisted` écrit la file sur disque.   Garantie obtenue : au moins une fois.  
Rôle du `document_id` : un événement renvoyé remplace le document existant au lieu de créer un doublon.

## Partie 3 Transformer les logs d'accès 

### 3.1 Générer les logs 

```bash
docker compose stop logstash
python data\generate_access_logs.py
```

Ceci a généré un fichier de 20700 lignes dans `/data/acces.log`.  

### 3.2 Mettre au point le motif 

![Grok Debugger](/TP2/image/exo3-2.PNG)  

Champs extraits : `source.address`, `timestamp`, `http.request.method`, `url.original`, `http.version`, `http.response.status_code`, `http.response.body.bytes`, `http.request.referrer` et `user_agent.original`.  
Type de `status_code` : un nombre (le motif contient `:int`).  
Pourquoi traiter `timestamp` : c'est une chaîne, le filtre `date` est nécessaire pour l'écrire dans `@timestamp`.  
Motif d'identifiant : déclarez `OFFRE_ID OFF-[0-9]{5}`, puis utilisez `^/offres/%{OFFRE_ID:offre_id}(/%{WORD:action})?`. Résultat : `OFF-01468` et `postuler`.

### 3.3 Compléter le web.conf

```bash
docker compose run --rm --no-deps logstash --path.data /tmp/test --config.test_and_exit -f /usr/share/logstash/pipeline/web.conf
docker compose up -d logstash
docker compose logs -f logstash
```

### 3.4 Vérifier le data stream

```bash
GET _data_stream/logs-web-default
GET logs-web-default/_count
GET logs-web-default/_count
{ "query": { "term": { "tags": "_grokparsefailure" } } }
GET logs-web-default/_search
{ "size": 1, "sort": [{ "@timestamp": "asc" }] }
GET logs-web-default/_mapping/field/http.response.status_code
GET logs-web-default/_settings?filter_path=*.settings.index.mode
```  

Volumes : 20 700 documents et 0 échec de grok.  
Nom de l'index caché : `.ds-logs-web-default-2026.10.05-000001`. Ses parties :  
-    `.ds-` signale un backing index de data stream ;  
-    `logs-web-default` est le nom du data stream ;  
-    `AAAA.MM.JJ` est la date de création de l'index (le jour de votre ingestion), pas celle des logs ;  
-    `000001v est le numéro de génération, qui augmente à chaque rollover.  

Premier événement : `2026-09-22T22:00:39Z`, soit le 23/09 à 00:00:39 heure de Paris.  
Type de `status_code` : `long`. C'est ce qui permet les filtres `>= 500`, les plages et les formules Lens.  
`index.mode` : `logsdb`.   

### 3.5 Rejouer sans doublons 

```bash
docker compose restart logstash
```

Constat : 41 400 documents, donc des doublons. Contrairement à `offres`, aucun `_id` n'est fourni.  
Modifier un document ? Pas par l'API `index` : un data stream est en ajout seul. Il faut passer par `_update_by_query` ou `_delete_by_query`.  
Deux solutions :  
1.  une sincedb persistante, pour ne pas relire le fichier ;  
2.  un `fingerprint` SHA-256 de `message` utilisé comme `document_id`. Un rejeu provoque un conflit 409, ignoré. L'unicité n'est garantie qu'au sein d'un même backing index.  

Pour repartir d'un état propre : `docker compose stop logstash`, puis `DELETE _data_stream/logs-web-default` dans Dev Tools, puis `docker compose up -d logstash`.  

## Partie 4 Enquête dans Kibana 

### 4.1 Vue d'ensemble  

```bash
FROM logs-web-default | STATS n = COUNT(*) BY http.response.status_code | SORT n DESC
FROM logs-web-default | STATS n = COUNT(*) BY http.request.method
FROM logs-web-default | STATS total = COUNT(*) | EVAL par_jour = total / 7.0
```

![Vue Discover](/TP2/image/exo4-1.PNG)  

Codes HTTP : 200 → 17 805 ; 201 → 1 492 ; 304 → 488 ; 404 → 508 ; 500 → 5 ; 503 → 402.  
Méthodes : GET → 19 208 ; POST → 1 492.  
Volume : environ 2 957 requêtes par jour.  


### 4.2 L'incident   

```bash
FROM logs-web-default | WHERE http.response.status_code >= 500 | STATS erreurs = COUNT(*) BY heure = BUCKET(@timestamp, 1 hour) | SORT erreurs DESC | LIMIT 10

FROM logs-web-default | WHERE @timestamp >= "2026-09-28T11:30:00Z" AND @timestamp < "2026-09-28T13:30:00Z" AND http.response.status_code >= 500 | STATS erreurs = COUNT(*) BY tranche = BUCKET(@timestamp, 5 minutes) | SORT tranche

FROM logs-web-default | WHERE @timestamp >= "2026-09-28T12:00:00Z" AND @timestamp < "2026-09-28T12:45:00Z" | EVAL zone = CASE(url.original LIKE "/api/*", "api", url.original LIKE "/offres/*", "offres", url.original LIKE "/recherche*", "recherche", url.original LIKE "/static/*", "static", "accueil") | STATS n = COUNT(*) BY zone, http.response.status_code

FROM logs-web-default | WHERE http.response.status_code == 503 | STATS n = COUNT(*), debut = MIN(@timestamp), fin = MAX(@timestamp)
```

1. Quand : lundi 28/09/2026 de 14:00 à 14:45 heure de Paris (12:00–12:45 UTC). Premier 503 à 14:00:08, dernier à 14:44:56, entre 35 et 53 erreurs par tranche de 5 minutes.  
2. URL touchées : uniquement `/api/offres`. L'accueil, la recherche, les fiches, les candidatures et les fichiers statiques fonctionnent normalement.
3. Ampleur : 402 réponses 503 en environ 45 minutes. Les 5 erreurs 500 de la semaine sont du bruit de fond.  
4. Comportement des clients : environ 11 appels API par 45 minutes en temps normal, contre 403 pendant l'incident, soit 35 fois plus. Les clients réessaient automatiquement. Recommandation : backoff exponentiel côté clients et disjoncteur côté serveur.  

![Vue Discover](/TP2/image/exo4-2.PNG)  

### 4.3 L'activité suspecte  

```bash
FROM logs-web-default | WHERE http.response.status_code == 404 | STATS n = COUNT(*) BY source.address | SORT n DESC | LIMIT 5

FROM logs-web-default | WHERE source.address == "203.0.113.66" AND http.response.status_code == 404 | STATS n = COUNT(*), debut = MIN(@timestamp), fin = MAX(@timestamp)

FROM logs-web-default | WHERE source.address == "203.0.113.66" AND http.response.status_code == 404 | STATS n = COUNT(*) BY url.original, user_agent.original | SORT n DESC
``` 


Origine : l'adresse 203.0.113.66, responsable de 300 des 508 réponses 404.
Moment et durée : samedi 26/09 de 03:12:00 à 03:16:59 heure de Paris, à une requête par seconde.  
Cible : `/admin`, `/.git/config`, `/.env`, `/phpmyadmin/`, `/server-status` et `/wp-login.php`. C'est un scan de vulnérabilités ; tout a répondu 404, rien n'était exposé.  
Comment le reconnaître : son agent est `Mozilla/5.0 zgrab/0.x`, un outil de scan sans navigateur, sans système ni version. Son rythme est régulier et il n'envoie aucun referrer.  
Les 208 autres 404 : toutes sur `/offres/OFF-09xxx`, des offres inexistantes, réparties sur la semaine. Ce sont des liens morts, pas une menace.  

![Vue Discover](/TP2/image/exo4-3.PNG)  


### 4.4 Les offres les plus consultées   

```bash 
FROM logs-web-default | WHERE http.request.method == "GET" AND http.response.status_code == 200 AND labels.offre_id IS NOT NULL | STATS vues = COUNT(*) BY labels.offre_id | SORT vues DESC, labels.offre_id ASC | LIMIT 10

# Dev Tool
GET offres/_search
{
  "size": 10,
  "_source": ["titre", "ville", "contrat"],
  "query": { "ids": { "values": ["OFF-04662","OFF-01153","OFF-03141","OFF-00289","OFF-00901","OFF-01275","OFF-01660","OFF-02899","OFF-03126","OFF-03145"] } }
}
```

| Rang | Offre | Vues | Titre | Ville | Contrat |
|------|-------|------|-------|-------|---------|
| 1 | OFF-04662 | 8 | Développeur Front-end Senior | Bordeaux | Freelance |  
| 2 | OFF-01153 | 7 | Développeur Java Confirmé | Toulouse | Freelance |  
| 3 | OFF-03141 | 7 | Développeur Python Confirmé | Bordeaux | CDI |  
| 4 | OFF-00289 | 6 | Data Scientist Lead | Lyon | CDI |  
| 5 | OFF-00901 | 6 | Développeur Java Junior | Paris | CDI |  
| 6 | OFF-01275 | 6 | Administrateur Bases de Données Lead | Paris | CDI |  
| 7 | OFF-01660 | 6 | Architecte Cloud Senior | Lyon | CDI |  
| 8 | OFF-02899 | 6 | Data Engineer (Alternance) | Lyon | Alternance |  
| 9 | OFF-03126 | 6 | Administrateur Bases de Données Junior | Lyon | CDI |  
| 10 | OFF-03145 | 6 | Data Engineer Lead | Montpellier | CDI |  

![Vue Discover](/TP2/image/exo4-4.PNG)  

### 4.5 Le public  

```bash
FROM logs-web-default | EVAL mobile = CASE(user_agent.os.name IN ("iOS", "Android"), 1, 0) | STATS part_mobile_pct = SUM(mobile) * 100.0 / COUNT(*)

FROM logs-web-default | STATS n = COUNT(*) BY user_agent.name | SORT n DESC | LIMIT 3
```

Part mobile : environ 39,4 % (8 155 requêtes).  
Top 3 des navigateurs : Safari (environ 4 150), Mobile Safari (environ 4 099) et Chrome (environ 4 058). La répartition est quasi uniforme ; vérifiez les noms exacts dans votre sortie.  

![Vue Discover](/TP2/image/exo4-5.PNG)  


## Partie 5 Tableau de bord et restitution 


Tableau de bord « Site de recrutement — trafic » construit avec Lens sur la data view « Logs web » (`logs-web-*`, `@timestamp`) et Maps sur la data view `offres` :  
- Requêtes : 20 700 ; taux d'erreur serveur : 1,97 %.  
- Trafic dans le temps : barres empilées par code HTTP ; pics visibles le 26/09 vers 3 h (scan, 404) et le 28/09 de 14:00 à 14:45 (incident API, 503).  
- Offres les plus consultées (GET + 200), navigateurs (top 5), carte des offres.  

Interactivité : un clic sur un segment 503 ajoute le filtre `http.response.status_code: 503` à tout le tableau de bord (402 requêtes, 100 % d'erreurs, un seul pic le 28/09).  
Le panneau temporel est construit en Lens sur data view : en ES|QL, la conversion du code en texte (`TO_STRING`) crée un champ calculé à la requête, non filtrable par clic.  
Sur la carte, « Apply global time » et « Apply global filter » sont désactivés :  
- `offres` n'a pas le champ `http.response.status_code`, et sa date est celle de publication des offres.  

![Vue Discover](/TP2/image/exo5-1.PNG) 


### Filtre 503

![Vue Discover](/TP2/image/exo5-2.PNG) 

Avec le filtre 503, le panneau « Offres les plus consultées » est vide : sa requête exige un code 200, ce qui est incompatible avec le filtre ; de plus, les 503 portent uniquement sur /api/offres, sans identifiant d'offre. Cela confirme que l'incident n'a touché que l'API.  
