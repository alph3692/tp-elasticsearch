"""Mini-défi — moteur de recherche d'offres en ligne de commande.

Attendu :
  python search.py "développeur python"
  python search.py "données spark" --ville Lyon --contrat CDI --salaire-min 45000
  python search.py "kubernetes" --autour "43.6108,3.8767"--rayon 50km --teletravail partiel
"""

from __future__ import annotations

import argparse

from es_client import INDEX, get_client


def construire_requete(args: argparse.Namespace) -> dict:
    """TODO : requête bool
    - must   : multi_match sur titre (x3), competences.texte (x2), description, tolérant aux fautes
    - filter : ville, contrat, teletravail (term), salaire_max >= --salaire-min (range),
               distance autour d'un point (geo_distance) si --autour est fourni
    """
    """Requête bool : le texte est scoré (must), les critères exacts sont filtrés (filter)."""
    must = [{
        "multi_match": {
            "query": args.texte,
            "fields": ["titre^3", "competences.texte^2", "description"],
            "fuzziness": "AUTO",   # tolère 1 à 2 fautes selon la longueur du mot
        }
    }]

    filtres: list[dict] = []
    if args.ville:
        filtres.append({"term": {"ville": args.ville}})
    if args.contrat:
        filtres.append({"term": {"contrat": args.contrat}})
    if args.teletravail:
        filtres.append({"term": {"teletravail": args.teletravail}})
    if args.salaire_min is not None:
        filtres.append({"range": {"salaire_max": {"gte": args.salaire_min}}})
    if args.autour:
        lat, lon = (float(x) for x in args.autour.split(","))
        filtres.append({"geo_distance": {"distance": args.rayon,
                                         "localisation": {"lat": lat, "lon": lon}}})

    return {"bool": {"must": must, "filter": filtres}}

FACETTES = {
    "villes": {"terms": {"field": "ville", "size": 12}},
    "contrats": {"terms": {"field": "contrat", "size": 5}},
    "competences": {"terms": {"field": "competences", "size": 10}},
}


def formater_salaire(src: dict) -> str:
    if "salaire_min" not in src:
        return "salaire non communiqué"
    return f"{src['salaire_min'] // 1000}–{src['salaire_max'] // 1000} k€"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("texte")
    p.add_argument("--ville")
    p.add_argument("--contrat", choices=["CDI", "CDD", "Alternance", "Freelance", "Stage"])
    p.add_argument("--teletravail", choices=["aucun", "partiel", "total"])
    p.add_argument("--salaire-min", type=int)
    p.add_argument("--autour", help="lat,lon")
    p.add_argument("--rayon", default="30km")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--taille", type=int, default=10)
    args = p.parse_args()

    es = get_client()
    # TODO : appeler es.search avec la requête, la pagination (from_, size), un highlight sur
    # description et trois facettes (aggs terms) : ville, contrat, compétences.
    # Afficher : total, puis pour chaque résultat score, titre, entreprise, ville, contrat, salaire,
    # l'extrait surligné, et enfin les facettes.
    rep = es.search(
        index=INDEX,
        query=construire_requete(args),
        from_=(args.page - 1) * args.taille,
        size=args.taille,
        source=["titre", "entreprise", "ville", "contrat", "salaire_min", "salaire_max"],
        highlight={"fields": {"description": {}}, "pre_tags": ["\033[1;33m"], "post_tags": ["\033[0m"]},
        aggs=FACETTES,
    )

    total = rep["hits"]["total"]["value"]
    nb_pages = max(1, -(-total // args.taille))
    print(f"\n{total} offre(s) trouvée(s) — page {args.page}/{nb_pages}\n")

    for hit in rep["hits"]["hits"]:
        s = hit["_source"]
        print(f"[{hit['_score']:.2f}] {s['titre']} — {s['entreprise']} ({s['ville']}, {s['contrat']}, "
              f"{formater_salaire(s)})")
        for extrait in hit.get("highlight", {}).get("description", [])[:1]:
            print(f"        … {extrait} …")

    print("\nFacettes")
    for nom, agg in rep["aggregations"].items():
        valeurs = ", ".join(f"{b['key']} ({b['doc_count']})" for b in agg["buckets"])
        print(f"  {nom:<12} {valeurs or '—'}")


if __name__ == "__main__":
    main()
