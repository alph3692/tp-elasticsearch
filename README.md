# Kit apprenant — TP Introduction à Elasticsearch (EISI)
# TP — Ingestion et analyse de logs avec Logstash (EISI, 1 jour) dans TP2/

Les réponses du TP1 **`REPONSES.md`** sont **ici**, à la suite du `README.md`  
Les réponses du TP2 **`REPONSES_TP2.md`** sont dans **TP2/**.  

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

## 2.1  Compléter `ingest.py`  
Voir le fichier.

## 2.2 Idempotence et identifiants  

Le nombre reste 5 000 (le `_version` de chaque document passe à 2).  
Fixer `_id = id` fait de l'action `index` un « créer ou remplacer » : relancer le script produit le même état final.  
Avec des `_id` générés, chaque relance ajouterait 5 000 doublons (10 000, puis 15 000…), faussant comptages et agrégations.  

## 2.3 Provoquer une erreur de mapping  

Seul le document `OFF-99999` est rejeté (`strict_dynamic_mapping_exception`) : le bulk renvoie un statut par opération. Sortie : `5000 documents indexés, 1 erreurs`.  
`raise_on_error=False` : le pipeline ne s'arrête pas au premier document invalide. On récupère la liste des erreurs pour les journaliser, les corriger ou les envoyer dans une file de rejet (dead letter queue).  


## 2.4 Vérifier dans Kibana  
 
`GET offres/_count` -> `5000`. santé de l'index green (0 réplique sur un seul nœud).

Data View `offres` :   
![Data View Offres](/image/Capture_exo2-4.PNG)

---
# Partie 3 - Recherche et analyseurs

## 3.1 Voir travailler un analyseur  

`standard` : découpe + minuscules seulement -> `les`, `développeuses`, `travaillaient`, `sur`, `l'analyse`, `des`, `données` (l'apostrophe est conservée dans le token).  
`french` : élision (`l'analyse` -> `analyse`), suppression des mots vides (`les`, `sur`, `des`), racinisation légère des mots restants.  
`donnée` / `données` : deux tokens différents avec `standard`, le même avec `french`.
Avec l'analyseur français, une recherche au singulier retrouve le pluriel (et inversement), donc le paramètre de langue est important. Le même analyseur doit être appliqué à l'indexation et à la recherche.  


## 3.2 `Match` contre `term`  

`term` n'analyse pas la valeur cherchée :  
> `ville` est un `keyword` stocké `Paris` -> `paris` ne correspond à rien. Correction : `"Paris"` (1 492 offres).  
> `titre` est un `text` stocké en tokens (`data`, `engineer`, `senior`) -> la phrase complète n'existe pas comme token. Correction : `titre.brut` (103 offres).  

`match` « projets bancaires » : OR par défaut -> ≈ 4 190 offres (toutes celles qui contiennent `projet`, y compris « chefs de projet », grâce à la racinisation). Avec `"operator": "and"` -> 393 offres.  

## 3.3 Plusieurs champs, pondération et fautes de frappe  

Le paramètre qui rattrape la faute : `fuzziness: "AUTO"` (distance d'édition 0, 1 ou 2 selon la longueur du terme. `kubernetis` -> `kubernetes` = 1 substitution).  
Sans fuzziness, seules les offres « Terraform » remontent. Avec, les offres Kubernetes apparaissent et celles qui citent les deux passent en tête.  
`titre^3` : quasiment aucun effet ici, car aucun titre ne contient « Kubernetes » ni « Terraform » (les titres sont « Ingénieur DevOps… », « Architecte Cloud… »). Un poids ne multiplie que le score d'un champ qui correspond. Essayez `"devops terraform"` pour voir l'effet.  

## 3.4 Requête `bool` 

Résultat attendu : 25 offres, toutes « Administrateur Bases de Données » (les descriptions ne contiennent jamais le mot « données »).  
Sans `should`, les scores sont quasi identiques. Avec, les 15 offres qui ont la compétence Elasticsearch reçoivent un bonus et passent en tête. Le nombre de résultats ne change pas (le `should` est facultatif dès qu'il y a un `must/filter`).  
Critères exacts dans `filter` plutôt que `must` :   
1.  Pertinence : un critère oui/non ne doit pas modifier le score (être à Toulouse ne rend pas une offre « plus pertinente »).   
2.  Performance : pas de calcul de score et résultats de filtre mis en cache.   

## 3.5 Recherche géographique  

Uniquement des offres de Montpellier (les autres villes sont à plus de 20 km) ; chaque hit porte dans `sort` sa distance en km.  

## 3.6 Pagination et surlignage  

`from + size ≤ 10 000` (`index.max_result_window`) : pour servir la page N, chaque shard doit trier et renvoyer `from + size` documents au nœud coordinateur. La mémoire et le CPU croissent avec la profondeur.
Au-delà : `search_after` (on repart de la clé de tri du dernier résultat) + point in time (instantané stable de l'index pendant le parcours).  

---
# Partie 4 - Agrégations

## 4.1 Offres et salaire moyen par ville  

Salaire moyen le plus élevé : Paris ≈ 57 442 € (majoration de 6 000 € dans le générateur), puis Grenoble ≈ 53 046 €. Le plus bas : Nice ≈ 49 456 €.  
La moyenne n'est calculée que sur les 3 389 offres qui ont un `salaire_min` (CDI + CDD). Exemple Paris : `doc_count` = 1 492 mais la moyenne porte sur 994 offres (vérifiable avec `value_count`).  
titre à la place de `ville` : erreur `illegal_argument_exception —` Fielddata is disabled on [titre] (un champ `text` n'a pas de `doc_values`). Correction : `titre.brut`.  

## 4.2 Publications par mois  

| Mois | Offres |  
|---|---|  
| 2026-04 (à partir du 3) | 763 |
| 2026-05 | 865 |  
| 2026-06 | 820 |  
| 2026-07 | 835 |  
| 2026-08 | 880 |  
| 2026-09 | 837 |  

## 4.3 Tranche de salair et statistiques  

`< 40 k` : 484 ; `40–55 k` : 1 363 ; `≥ 55 k` : 1 542 (total 3 389 : les offres sans salaire ne tombent dans aucune tranche). `to` est exclusif, `from` inclusif.  
`experience_annees` : count 5 000, min 0, max 15, moyenne ≈ 5,91.  

## 4.4 Requête et agrégation  

Offres « Data Engineer » : 462 (avec `match_phrase` ; un `match` simple en OR ramènerait aussi les « Data Scientist »).  
Top 5 compétences : Airflow (315), Spark (313), Kafka (312), Python (311), SQL (301).
Télétravail le plus fréquent : partiel (284).  
L'agrégation porte uniquement sur les documents sélectionnés par `query`.  

## 4.5 Visualiser  

![Nombre d'offre par Ville et par Contrat](/image/Capture_exo4-5.PNG)  

---
# Partie 5 - Mini-défi

```bash
python search.py "développeur python"
```  
Extrait :  
![Requete Search 1](/image/MiniProjet.PNG)   

```bash
python search.py "kubernetes" --autour "43.6108,3.8767" --rayon 50km --teletravail partiel --page 2
```  
Extrait : 
![Requete Search 2](/image/MiniProjet_2.PNG)  
