#!/usr/bin/env python3
"""
Construit un GeoJSON enrichi des ecoles de Montreal a partir de deux sources MEQ:
1) Ecoles publiques (localisation, nom, type, municipalite)
2) Indices de defavorisation 2025-2026 (IMSE/SFR/deciles/annee)

Sortie par defaut:
- meq_ecoles_montreal_enrichi.geojson
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import unicodedata
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

PPS_PUBLIC_ECOLE_CSV = (
    "https://www.donneesquebec.ca/recherche/dataset/"
    "2d3b5cf8-b347-49c7-ad3b-bd6a9c15e443/resource/"
    "c6640a54-bc4b-43ec-864e-6c325dce61bc/download/pps_public_ecole.csv"
)

DEFAV_PRIM_CSV = (
    "https://www.donneesquebec.ca/recherche/dataset/"
    "004de02c-19f1-4da0-9af8-33f893e41972/resource/"
    "6c5d4a5d-ba3b-40a6-b570-916f43ab622c/download/defav_ecole_prim_public.csv"
)

DEFAV_SEC_CSV = (
    "https://www.donneesquebec.ca/recherche/dataset/"
    "004de02c-19f1-4da0-9af8-33f893e41972/resource/"
    "3e9aa43a-c32b-4779-b258-8407db716813/download/defav_ecole_sec_public.csv"
)


@dataclass
class DefavRow:
    code_org: str
    nom_org: str
    imse: float
    rang_decile_imse: Optional[int]
    sfr: Optional[float]
    rang_decile_sfr: Optional[int]
    nbre_eleves: Optional[int]
    diffusion: str
    annee_scol: str
    nom_cs: str


def fetch_csv_rows(url: str) -> List[Dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; MEQ-merge-script/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    text = payload.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def is_montreal_city(name: str) -> bool:
    n = normalize_text(name)
    return "montreal" in n


def as_float(value: str) -> Optional[float]:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def as_int(value: str) -> Optional[int]:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def parse_defav_rows(rows: List[Dict[str, str]], school_level: str) -> Dict[str, DefavRow]:
    result: Dict[str, DefavRow] = {}
    for row in rows:
        if (row.get("Annee_Scol") or "").strip() != "2025-2026":
            continue
        if (row.get("Diffusion") or "").strip().upper() != "OUI":
            continue

        code_org = (row.get("Code_Org") or "").strip()
        if not code_org:
            continue

        imse = as_float(row.get("IMSE", ""))
        if imse is None:
            continue

        data = DefavRow(
            code_org=code_org,
            nom_org=(row.get("Nom_Org") or "").strip(),
            imse=imse,
            rang_decile_imse=as_int(row.get("Rang_Decile_IMSE", "")),
            sfr=as_float(row.get("SFR", "")),
            rang_decile_sfr=as_int(row.get("Rang_Decile_SFR", "")),
            nbre_eleves=as_int(row.get("Nbre_Eleves", "")),
            diffusion=(row.get("Diffusion") or "").strip(),
            annee_scol=(row.get("Annee_Scol") or "").strip(),
            nom_cs=(row.get("Nom_Cs") or "").strip(),
        )

        # En cas de collision rare entre primaire/secondaire, on garde la valeur la plus defavorable (IMSE plus eleve)
        existing = result.get(code_org)
        if existing is None or data.imse > existing.imse:
            result[code_org] = data

    return result


def build_address(row: Dict[str, str]) -> str:
    parts = [
        (row.get("ADRS_GEO_L1_GDUNO_IMM") or "").strip(),
        (row.get("ADRS_GEO_L2_GDUNO_IMM") or "").strip(),
        (row.get("NOM_MUNCP_GDUNO_IMM") or "").strip(),
        (row.get("CD_POSTL_GDUNO_IMM") or "").strip(),
    ]
    return ", ".join(p for p in parts if p)


def build_dataset(
    pps_rows: List[Dict[str, str]],
    defav_map: Dict[str, DefavRow],
    municipality_filter: str,
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    target = normalize_text(municipality_filter)

    features: List[Dict[str, object]] = []
    stats = {
        "pps_total": len(pps_rows),
        "pps_municipality": 0,
        "pps_primary_or_secondary": 0,
        "matched_defav": 0,
        "kept": 0,
        "missing_coords": 0,
    }

    for row in pps_rows:
        city = (row.get("NOM_MUNCP_GDUNO_IMM") or row.get("NOM_MUNCP_GDUNO_ORGNS") or "").strip()
        if target:
            if target == "montreal":
                if not is_montreal_city(city):
                    continue
            elif normalize_text(city) != target:
                continue

        stats["pps_municipality"] += 1

        is_primary = (row.get("PRIM") or "").strip() == "1"
        is_secondary = (row.get("SEC") or "").strip() == "1"
        if not (is_primary or is_secondary):
            continue

        stats["pps_primary_or_secondary"] += 1

        code_org = (row.get("CD_ORGNS") or "").strip()
        defav = defav_map.get(code_org)
        if not defav:
            continue

        stats["matched_defav"] += 1

        lon = as_float(row.get("COORD_X_LL84_IMM", ""))
        lat = as_float(row.get("COORD_Y_LL84_IMM", ""))
        if lon is None or lat is None:
            stats["missing_coords"] += 1
            continue

        nom = (row.get("NOM_IMM") or row.get("NOM_OFFCL_ORGNS") or defav.nom_org or "").strip()
        adresse = build_address(row)

        feature = {
            "type": "Feature",
            "properties": {
                # Champs historiques utilises par l'application
                "nom": nom,
                "rang": None,  # calcule apres tri IMSE
                "adresse": adresse,
                # Champs enrichis
                "source": "MEQ",
                "annee_scolaire": defav.annee_scol,
                "code_organisme": code_org,
                "nom_organisme": (row.get("NOM_OFFCL_ORGNS") or "").strip(),
                "code_css_cs": (row.get("CD_CS") or "").strip(),
                "nom_css_cs": defav.nom_cs,
                "municipalite": city,
                "ordre_enseignement": (row.get("ORDRE_ENS") or "").strip(),
                "type_cs": (row.get("TYPE_CS") or "").strip(),
                "imse": defav.imse,
                "rang_decile_imse": defav.rang_decile_imse,
                "sfr": defav.sfr,
                "rang_decile_sfr": defav.rang_decile_sfr,
                "nombre_eleves": defav.nbre_eleves,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        }

        features.append(feature)

    # Rang derive de l'IMSE: plus IMSE est faible, meilleur est le rang.
    # On projette le rang sur [1, 350] pour compatibilite avec le validateur existant.
    ranked = sorted(
        features,
        key=lambda f: (
            f["properties"]["imse"],
            normalize_text(str(f["properties"]["nom"])),
        ),
    )
    total = len(ranked)
    for idx, feature in enumerate(ranked, start=1):
        if total <= 1:
            scaled_rank = 1
        else:
            scaled_rank = int(round((idx - 1) * 349 / (total - 1))) + 1
        feature["properties"]["rang"] = scaled_rank

    stats["kept"] = len(features)
    return features, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Fusionner les donnees MEQ en un GeoJSON enrichi")
    parser.add_argument(
        "--out",
        default="meq_ecoles_montreal_enrichi.geojson",
        help="Chemin de sortie GeoJSON",
    )
    parser.add_argument(
        "--municipality",
        default="Montreal",
        help="Filtre municipalite (defaut: Montreal)",
    )
    args = parser.parse_args()

    try:
        pps_rows = fetch_csv_rows(PPS_PUBLIC_ECOLE_CSV)
        defav_prim_rows = fetch_csv_rows(DEFAV_PRIM_CSV)
        defav_sec_rows = fetch_csv_rows(DEFAV_SEC_CSV)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Erreur telechargement source: {exc}", file=sys.stderr)
        return 1

    defav_map = {}
    defav_map.update(parse_defav_rows(defav_prim_rows, "primary"))
    defav_map.update(parse_defav_rows(defav_sec_rows, "secondary"))

    features, stats = build_dataset(pps_rows, defav_map, municipality_filter=args.municipality)

    output = {
        "type": "FeatureCollection",
        "name": "ecoles_meq_montreal_enrichi",
        "metadata": {
            "sources": {
                "ecoles_publiques": PPS_PUBLIC_ECOLE_CSV,
                "defavorisation_primaire": DEFAV_PRIM_CSV,
                "defavorisation_secondaire": DEFAV_SEC_CSV,
            },
            "annee_scolaire": "2025-2026",
            "scope": args.municipality,
            "stats": stats,
        },
        "features": features,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print("GeoJSON cree:", args.out)
    print("Stats:")
    for key, value in stats.items():
        print(f"- {key}: {value}")

    if not features:
        print("Aucun enregistrement retenu. Verifiez le filtre municipalite.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
