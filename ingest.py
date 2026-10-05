"""Partie 3a — Crée l'index `offres` avec un mapping explicite puis ingère le NDJSON en bulk.

Usage : python ingest.py [--fichier data/offres.ndjson] [--reset]
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from elasticsearch import helpers

from es_client import INDEX, get_client

SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}

MAPPINGS = {
    "dynamic": "strict",
    "properties": {
        "id": {"type": "keyword"},
        # TODO 1 : compléter le mapping des 12 autres champs (voir le tableau de l'énoncé)
        "id": {"type": "keyword"},
        "titre": {"type": "text", "analyzer": "french", "fields": {"brut": {"type": "keyword"}}},
        "entreprise": {"type": "keyword"},
        "description": {"type": "text", "analyzer": "french"},
        "competences": {"type": "keyword", "fields": {"texte": {"type": "text"}}},
        "ville": {"type": "keyword"},
        "localisation": {"type": "geo_point"},
        "contrat": {"type": "keyword"},
        "teletravail": {"type": "keyword"},
        "experience_annees": {"type": "integer"},
        "salaire_min": {"type": "integer"},
        "salaire_max": {"type": "integer"},
        "date_publication": {"type": "date", "format": "strict_date"},
        },
}


def lire_actions(fichier: Path) -> Iterator[dict]:
    """TODO 2 : générateur qui lit le fichier ligne à ligne et produit
    {"_index": INDEX, "_id": <id de l'offre>, "_source": <document>}."""
    with fichier.open(encoding="utf-8") as f:
        for ligne in f:
            if ligne.strip():
                doc = json.loads(ligne)
                yield {"_index": INDEX, "_id": doc["id"], "_source": doc}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fichier", type=Path, default=Path("data/offres.ndjson"))
    parser.add_argument("--reset", action="store_true", help="supprime l'index s'il existe")
    args = parser.parse_args()

    es = get_client()
    print("Cluster :", es.info()["version"]["number"])

    # TODO 3 : si --reset, supprimer l'index (sans erreur s'il n'existe pas)
    # TODO 4 : créer l'index s'il n'existe pas, avec SETTINGS et MAPPINGS
    # TODO 5 : ingérer avec helpers.bulk (chunk_size=1000, raise_on_error=False), afficher les erreurs
    # TODO 6 : rafraîchir l'index puis afficher le nombre de documents (es.count)

    if args.reset:
        es.indices.delete(index=INDEX, ignore_unavailable=True)
    if not es.indices.exists(index=INDEX):
        es.indices.create(index=INDEX, settings=SETTINGS, mappings=MAPPINGS)
        print(f"Index '{INDEX}' créé")

    ok, erreurs = helpers.bulk(es, lire_actions(args.fichier), chunk_size=1000, raise_on_error=False)
    for err in erreurs[:5]:
        print("Erreur :", err)

    es.indices.refresh(index=INDEX)
    total = es.count(index=INDEX)["count"]
    print(f"{ok} documents indexés, {len(erreurs)} erreurs, {total} documents dans '{INDEX}'")


if __name__ == "__main__":
    main()
