#!/usr/bin/env python3
"""
Construit un GeoJSON ecoles a partir de 2 sources:
1) CGTSIM: classement pedagogique (rang, nom ecole)
2) Donnees ouvertes Montreal: geolocalisation et adresses

Le script est tolerant aux schemas de colonnes differents via detection automatique.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

CGTSIM_DEFAULT = "https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf"
MONTREAL_DEFAULT = "https://data.montreal.ca"
MONTREAL_LIEUX_INTERET_GEOJSON = (
    "https://donnees.montreal.ca/dataset/763fe3b8-cdc3-4b8a-bbbd-a0a9bc587c56/"
    "resource/5ca7cdb8-f86f-4038-b5a8-657446c75427/download/lieux_d_interet.geojson"
)


@dataclass
class RankingRow:
    nom: str
    rang: int
    adresse: str


@dataclass
class MontrealSchoolRow:
    nom: str
    adresse: str
    lon: float
    lat: float
    raw: Dict[str, object]


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; schools-pipeline/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    return payload.decode("utf-8-sig", errors="replace")


def fetch_json(url: str) -> object:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; schools-pipeline/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    return json.loads(payload.decode("utf-8-sig", errors="replace"))


def read_source(source: str) -> object:
    if source.startswith("http://") or source.startswith("https://"):
        if source.lower().endswith(".csv"):
            return list(csv.DictReader(io.StringIO(fetch_text(source))))
        if source.lower().endswith(".json") or source.lower().endswith(".geojson"):
            return fetch_json(source)
        raise ValueError(
            "Source distante non supportee. Fournir un .csv, .json ou .geojson (pas un PDF brut)."
        )

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source}")

    lower = path.name.lower()
    if lower.endswith(".csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    if lower.endswith(".json") or lower.endswith(".geojson"):
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    raise ValueError("Format non supporte. Utiliser CSV/JSON/GeoJSON.")


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def simplify_school_name(value: str) -> str:
    n = normalize_text(value)
    n = re.sub(r"\b(annexe|pavillon|edifice|occupation transitoire|temporaire)\b.*$", "", n).strip()
    n = re.sub(r"\s+", " ", n).strip()
    return n


def find_column(columns: Iterable[str], candidates: List[str]) -> Optional[str]:
    by_norm = {normalize_text(c): c for c in columns}
    for cand in candidates:
        key = normalize_text(cand)
        if key in by_norm:
            return by_norm[key]

    for col in columns:
        norm_col = normalize_text(col)
        for cand in candidates:
            norm_cand = normalize_text(cand)
            if norm_cand and norm_cand in norm_col:
                return col
    return None


def as_int(value: object) -> Optional[int]:
    txt = str(value or "").strip()
    if not txt:
        return None
    txt = txt.replace(" ", "")
    try:
        return int(float(txt))
    except ValueError:
        return None


def as_float(value: object) -> Optional[float]:
    txt = str(value or "").strip().replace(",", ".")
    if not txt:
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def parse_rank_rows(data: object) -> List[RankingRow]:
    if not isinstance(data, list):
        raise ValueError("La source CGTSIM doit etre un tableau (CSV converti en lignes).")

    if not data:
        return []

    sample = data[0]
    if not isinstance(sample, dict):
        raise ValueError("Format de ligne CGTSIM invalide.")

    cols = list(sample.keys())
    name_col = find_column(cols, ["nom", "nom_ecole", "ecole", "etablissement", "school_name"])
    rank_col = find_column(cols, ["rang", "classement", "rank", "position"])
    addr_col = find_column(cols, ["adresse", "address", "adresse_complete", "location"])

    if not name_col or not rank_col:
        raise ValueError(
            "Colonnes CGTSIM non detectees. Colonnes minimales attendues: nom + rang."
        )

    rows: List[RankingRow] = []
    for row in data:
        if not isinstance(row, dict):
            continue

        nom = str(row.get(name_col, "") or "").strip()
        rang = as_int(row.get(rank_col))
        adresse = str(row.get(addr_col, "") or "").strip() if addr_col else ""

        if not nom or rang is None:
            continue

        rows.append(RankingRow(nom=nom, rang=rang, adresse=adresse))

    rows.sort(key=lambda r: r.rang)
    return rows


def _extract_rows_from_geojson(data: Dict[str, object]) -> List[Dict[str, object]]:
    feats = data.get("features")
    if not isinstance(feats, list):
        return []

    rows: List[Dict[str, object]] = []
    for feat in feats:
        if not isinstance(feat, dict):
            continue

        props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
        geom = feat.get("geometry") if isinstance(feat.get("geometry"), dict) else {}
        row: Dict[str, object] = {}
        if isinstance(props, dict):
            row.update(props)
        if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
            coords = geom.get("coordinates")
            if len(coords) == 2:
                row["_lon"] = coords[0]
                row["_lat"] = coords[1]
        rows.append(row)
    return rows


def row_passes_filter(
    row: Dict[str, object],
    columns: List[str],
    filter_field: str,
    filter_value: str,
    filter_mode: str,
) -> bool:
    if not filter_field or not filter_value:
        return True

    resolved_field = find_column(columns, [filter_field]) or filter_field
    field_value = str(row.get(resolved_field, "") or "")
    left = normalize_text(field_value)
    right = normalize_text(filter_value)

    if not right:
        return True
    if filter_mode == "equals":
        return left == right
    return right in left


def build_montreal_address(row: Dict[str, object], addr_col: Optional[str]) -> str:
    if addr_col:
        direct = str(row.get(addr_col, "") or "").strip()
        if direct:
            return direct

    numero_col = find_column(row.keys(), ["numero", "numéro", "numero_civique"])
    rue_col = find_column(row.keys(), ["rue", "street", "voie"])
    ville_col = find_column(row.keys(), ["ville", "city", "municipalite", "municipalité"])
    cp_col = find_column(row.keys(), ["code_postal", "code postal", "postal", "cp"])

    parts = [
        str(row.get(numero_col, "") or "").strip() if numero_col else "",
        str(row.get(rue_col, "") or "").strip() if rue_col else "",
        str(row.get(ville_col, "") or "").strip() if ville_col else "",
        str(row.get(cp_col, "") or "").strip() if cp_col else "",
    ]

    return ", ".join(p for p in parts if p)


def parse_montreal_rows(
    data: object,
    filter_field: str = "",
    filter_value: str = "",
    filter_mode: str = "contains",
) -> List[MontrealSchoolRow]:
    rows: List[Dict[str, object]]

    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        rows = _extract_rows_from_geojson(data)
    elif isinstance(data, list):
        rows = [r for r in data if isinstance(r, dict)]
    else:
        raise ValueError("La source Montreal doit etre une liste ou un GeoJSON FeatureCollection.")

    if not rows:
        return []

    cols = list(rows[0].keys())
    name_col = find_column(
        cols,
        [
            "nom",
            "nom_ecole",
            "nom_etablissement",
            "ecole",
            "name",
            "school_name",
            "titre_lieu",
            "nom français",
            "nom francais",
            "nom_francais",
        ],
    )
    addr_col = find_column(
        cols,
        [
            "adresse",
            "adresse_complete",
            "adresse_principale",
            "titre_lieu_adresse_postale",
            "address",
            "addr_full",
            "location",
        ],
    )
    lon_col = find_column(
        cols,
        [
            "_lon",
            "longitude",
            "long",
            "lon",
            "x",
            "coord_x",
            "coordonnee_x",
        ],
    )
    lat_col = find_column(
        cols,
        [
            "_lat",
            "latitude",
            "lat",
            "y",
            "coord_y",
            "coordonnee_y",
        ],
    )

    if not name_col or not lon_col or not lat_col:
        raise ValueError(
            "Colonnes Montreal non detectees. Attendu: nom + longitude + latitude (ou geometrie Point)."
        )

    result: List[MontrealSchoolRow] = []
    for row in rows:
        if not row_passes_filter(row, cols, filter_field, filter_value, filter_mode):
            continue

        nom = str(row.get(name_col, "") or "").strip()
        lon = as_float(row.get(lon_col))
        lat = as_float(row.get(lat_col))

        if not nom or lon is None or lat is None:
            continue

        adresse = build_montreal_address(row, addr_col)
        result.append(MontrealSchoolRow(nom=nom, adresse=adresse, lon=lon, lat=lat, raw=row))

    return result


def make_variants(name: str) -> List[str]:
    full = normalize_text(name)
    base = simplify_school_name(name)
    variants = [v for v in [full, base] if v]
    return list(dict.fromkeys(variants))


def choose_best_candidate(name: str, candidates: List[MontrealSchoolRow]) -> MontrealSchoolRow:
    target = normalize_text(name)
    best = candidates[0]
    best_score = -1.0
    for cand in candidates:
        score = SequenceMatcher(None, target, normalize_text(cand.nom)).ratio()
        if score > best_score:
            best = cand
            best_score = score
    return best


def build_match_indexes(rows: List[MontrealSchoolRow]) -> Dict[str, List[MontrealSchoolRow]]:
    idx: Dict[str, List[MontrealSchoolRow]] = {}
    for row in rows:
        for variant in make_variants(row.nom):
            idx.setdefault(variant, []).append(row)
    return idx


def fuzzy_match(name: str, rows: List[MontrealSchoolRow], threshold: float) -> Optional[MontrealSchoolRow]:
    target = normalize_text(name)
    best: Optional[MontrealSchoolRow] = None
    best_score = -1.0
    for row in rows:
        score = SequenceMatcher(None, target, normalize_text(row.nom)).ratio()
        if score > best_score:
            best = row
            best_score = score
    if best is None or best_score < threshold:
        return None
    return best


def merge_sources(
    ranking_rows: List[RankingRow],
    montreal_rows: List[MontrealSchoolRow],
    fuzzy_threshold: float,
) -> Tuple[List[Dict[str, object]], Dict[str, object], List[Dict[str, object]]]:
    index = build_match_indexes(montreal_rows)

    features: List[Dict[str, object]] = []
    unmatched: List[Dict[str, object]] = []

    exact_matches = 0
    fuzzy_matches = 0

    for row in ranking_rows:
        matched: Optional[MontrealSchoolRow] = None
        for key in make_variants(row.nom):
            candidates = index.get(key)
            if candidates:
                matched = choose_best_candidate(row.nom, candidates)
                exact_matches += 1
                break

        if matched is None:
            matched = fuzzy_match(row.nom, montreal_rows, threshold=fuzzy_threshold)
            if matched is not None:
                fuzzy_matches += 1

        if matched is None:
            unmatched.append(
                {
                    "nom_cgtsim": row.nom,
                    "rang": row.rang,
                    "adresse_cgtsim": row.adresse,
                }
            )
            continue

        adresse = matched.adresse or row.adresse
        feature = {
            "type": "Feature",
            "properties": {
                "nom": row.nom,
                "rang": row.rang,
                "adresse": adresse,
                "source_rang": "CGTSIM",
                "source_geo": "Montreal Open Data",
                "nom_montreal": matched.nom,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [matched.lon, matched.lat],
            },
        }
        features.append(feature)

    features.sort(key=lambda f: int(f["properties"]["rang"]))

    stats = {
        "cgtsim_rows": len(ranking_rows),
        "montreal_rows": len(montreal_rows),
        "matched": len(features),
        "unmatched": len(unmatched),
        "exact_matches": exact_matches,
        "fuzzy_matches": fuzzy_matches,
        "match_rate": round((len(features) / len(ranking_rows) * 100.0), 2) if ranking_rows else 0.0,
    }

    return features, stats, unmatched


def write_unmatched_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["nom_cgtsim", "rang", "adresse_cgtsim"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fusion CGTSIM + Montreal Open Data -> GeoJSON")
    parser.add_argument(
        "--cgtsim",
        required=True,
        help="Chemin/URL CSV de classement CGTSIM (nom + rang)",
    )
    parser.add_argument(
        "--montreal",
        required=True,
        help="Chemin/URL CSV/GeoJSON des ecoles Montreal (nom + coordonnees)",
    )
    parser.add_argument(
        "--montreal-filter-field",
        default="",
        help="Nom de colonne Montreal utilisee pour filtrer (ex: Catégorie)",
    )
    parser.add_argument(
        "--montreal-filter-value",
        default="",
        help="Valeur de filtre Montreal (ex: Établissement scolaire)",
    )
    parser.add_argument(
        "--montreal-filter-mode",
        choices=["contains", "equals"],
        default="contains",
        help="Mode de comparaison du filtre Montreal",
    )
    parser.add_argument(
        "--out",
        default="ecoles.geojson",
        help="Fichier GeoJSON de sortie",
    )
    parser.add_argument(
        "--unmatched-out",
        default="unmatched_cgtsim_montreal.csv",
        help="Fichier CSV des lignes CGTSIM non associees",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.86,
        help="Seuil de similarite [0-1] pour le matching flou",
    )

    args = parser.parse_args()

    if not (0.0 <= args.fuzzy_threshold <= 1.0):
        print("Le seuil fuzzy doit etre entre 0 et 1.", file=sys.stderr)
        return 2

    try:
        cgtsim_data = read_source(args.cgtsim)
        montreal_data = read_source(args.montreal)

        ranking_rows = parse_rank_rows(cgtsim_data)
        montreal_rows = parse_montreal_rows(
            montreal_data,
            filter_field=args.montreal_filter_field,
            filter_value=args.montreal_filter_value,
            filter_mode=args.montreal_filter_mode,
        )

        if not ranking_rows:
            print("Aucune ligne CGTSIM exploitable.", file=sys.stderr)
            return 3
        if not montreal_rows:
            print("Aucune ligne Montreal exploitable.", file=sys.stderr)
            return 4

        features, stats, unmatched = merge_sources(
            ranking_rows=ranking_rows,
            montreal_rows=montreal_rows,
            fuzzy_threshold=args.fuzzy_threshold,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Erreur pipeline: {exc}", file=sys.stderr)
        return 1

    output = {
        "type": "FeatureCollection",
        "name": "ecoles_cgtsim_montreal",
        "metadata": {
            "sources": {
                "cgtsim": args.cgtsim,
                "montreal_open_data": args.montreal,
                "cgtsim_reference": CGTSIM_DEFAULT,
                "montreal_reference": MONTREAL_DEFAULT,
                "montreal_lieux_interet_geojson": MONTREAL_LIEUX_INTERET_GEOJSON,
            },
            "matching": {
                "fuzzy_threshold": args.fuzzy_threshold,
                "montreal_filter_field": args.montreal_filter_field,
                "montreal_filter_value": args.montreal_filter_value,
                "montreal_filter_mode": args.montreal_filter_mode,
            },
            "stats": stats,
        },
        "features": features,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    write_unmatched_csv(args.unmatched_out, unmatched)

    print(f"GeoJSON cree: {args.out}")
    print("Stats:")
    for key, value in stats.items():
        print(f"- {key}: {value}")
    if unmatched:
        print(f"Lignes non associees exportees: {args.unmatched_out}")

    if not features:
        print("Aucune ecole fusionnee. Verifier le mapping des colonnes.", file=sys.stderr)
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
