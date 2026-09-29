# Kit apprenant — TP Introduction à Elasticsearch (EISI)

L'énoncé complet est dans le document de TP (section « Mise en place »). Démarrage rapide :

```bash
cp .env.example .env            # puis changez les mots de passe et la clé
docker compose up -d
docker compose ps               # elasticsearch healthy, setup exited (0), kibana healthy
```

Changement de clé : 
````bash
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
