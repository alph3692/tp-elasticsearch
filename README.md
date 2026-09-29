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
---
# Partie 2 - Ingestion en Python
---
# Partie 3 - Recherche et analyseurs
---
# Partie 4 - Agrégations
---
# Partie 5 - Mini-défi
