# Kit apprenant — TP Introduction à Elasticsearch (EISI)

L'énoncé complet est dans le document de TP (section « Mise en place »). Démarrage rapide :

```bash
cp .env.example .env            # puis changez les mots de passe et la clé
docker compose up -d
docker compose ps               # elasticsearch healthy, setup exited (0), kibana healthy
```

Changement de clé : 
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"   # clé KIBANA_ENCRYPTION_KEY ; Windows : python au lieu de python3
# copier <la clé> dans le .env et changer les deux autres mots de passe
```  

Environnement Python, macOS / Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Environnement Python, Windows (PowerShell) :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Puis, sur tous les systèmes :

```bash
pip install -r requirements.txt
python data/generate_offres.py  # -> data/offres.ndjson
```

Kibana : <http://localhost:5601> (utilisateur `elastic`). Arrêt : `docker compose down`
(ajoutez `-v` pour supprimer aussi les données).

---
# Pour avancer dans le TP - Accès Elastic

sous cmd, executer : 
```bash
curl -u elastic:<Votre mot de passe> "http://localhost:9200/_cluster/health?pretty"  
# attendu : "status" : "green"
```
Ouvrez http://localhost:5601, connectez-vous en elastic, puis Menu → Management → Dev Tools. C'est là que vous tapez les requêtes des parties 1, 3 et 4 ; Hoppscotch ou curl donnent le même résultat (voir « Outils pour envoyer les requêtes »).

# Exxercice 0 - vérifier l'accès au cluster

## 1. côté Kibana  -> Dev Tools
```bash
GET /
```
Réponse :   
```bash
{
  "name": "es01",
  "cluster_name": "tp-eisi",
  "cluster_uuid": "WIiu3F8ZQw6NPZJ13CZOQw",
  "version": {
    "number": "9.5.4",
    "build_flavor": "default",
    "build_type": "docker",
    "build_hash": "9170df19cae1adb107b7b489b4d82dec66d7a337",
    "build_date": "2026-09-09T22:42:53.976833287Z",
    "build_snapshot": false,
    "lucene_version": "10.5.1",
    "minimum_wire_compatibility_version": "8.19.0",
    "minimum_index_compatibility_version": "8.0.0"
  },
  "tagline": "You Know, for Search"
}
```

## 2. Avec `curl`
```bash
curl -u elastic:ssrg521gfs5 "http://localhost:9200/"
```

le `-u`permettant de passer utilisateur et mot de passe en paramètre. L'absence du paramètre cause une erreure d'authentification. 

Réponse :   
![requête curl](/image/Capture_exo0_curl.PNG)

## Quuestion
Les réponses sont identiques - Kibana, curl, hoppscotch appellent la même API REST. Seul l'habillage change.  
Sans `-u` nous obtenons une erreur d'authentification (`xpack.security.enable=true`).  
Pourquoi kibana ne demande pas de mot de passe ? on s'est authentifié une fois à la connxion, kibana garde une session (cookie) et relaie chaque requête vers Elasticsearch.

---
# Partie 1 - Conceptes, CRUD et mapping

## 1.1
Version : `9.5.4` (`version.number` de `GET /`).  
Noeuds : 1 (`es01`, `discovery.type=single-node`).
Index commençant par un point : ce sont des index système / cachés (`.kibana*`, `.security*`, `.tasks` ...) utilisés par Kibana et les fonctionnalités de la stack. Ils n'apparaissent qu'avec `expand_wildcards=all`.

## 1.2 Le CRUD  
`_version` : 1 après le `PUT`, 2 après l'`_update`, 3 dans la réponse du `DELETE` (une suppression est aussi une écriture).  
`POST essai/_doc` : Elasticsearch génère un `_id` aléatoire de 20 caractères (type base64 URL).
L'index `essai` n'existait pas : il a été créé automatiquement au premier `PUT` (`action.auto_create_index`), avec un mapping dynamique.  

## 1.3 Les pièges du mapping dynamique 
`salaire` (`"45000"`) > `text` + sous-champ `salaire.keyword` : une chaîne reste une chaîne de caractère (la détection numérique est désactivée par défaut).  
`publication` > `date` : la détection de date est active par défaut.  
`actif` (`"true"`) > `text` + `keyword` également.
Le document 2 est accepté car `52000` est converti en chaîne pour entrer dans un champ `text/keyword` (coercition).  
Conséquence : tri et filtre portent sur `"100000" < "45000"` et `salaire > 50000`. Cela compare des chaînes caractère par caractère. Les moyennes sont impossibles. Seule solution : recréer l'index avec le bon type (+ réindexer).  

## 1.4 Mapping explicite de l'index `offres`  
Erreur : `400`, `strict_dynamic_mapping_exception` — mapping set to strict, dynamic introduction of [champ_inconnu] within [_doc] is not allowed.  
Intérêt en production : le schéma est un contrat ; une faute de frappe (vile au lieu de ville) ou un champ inattendu provoque une erreur visible au lieu de créer silencieusement un champ mal typé, qu'on ne pourrait plus corriger sans réindexer (et on évite l'explosion du nombre de champs).  
---
# Partie 2 - Ingestion en Python
---
# Partie 3 - Recherche et analyseurs
---
# Partie 4 - Agrégations
---
# Partie 5 - Mini-défi
