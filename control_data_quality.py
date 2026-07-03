#!/usr/bin/env python3
"""
Controle qualite d'un GeoJSON d'ecoles.
Complete le validateur existant avec des checks metier pour le pipeline multi-sources.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def validate(filepath: Path) -> Tuple[bool, Dict[str, object]]:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, {"errors": [f"fichier introuvable: {filepath}"]}
    except json.JSONDecodeError as exc:
        return False, {"errors": [f"json invalide: {exc}"]}

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        return False, {"errors": ["root invalide: FeatureCollection attendu"]}

    features = data.get("features", [])
    if not isinstance(features, list):
        return False, {"errors": ["champ features invalide"]}

    rank_values: List[int] = []
    names = Counter()
    normalized_names = Counter()
    coords_to_names = defaultdict(list)

    for idx, feat in enumerate(features):
        if not isinstance(feat, dict) or feat.get("type") != "Feature":
            errors.append(f"feature {idx}: type invalide")
            continue

        props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
        geom = feat.get("geometry") if isinstance(feat.get("geometry"), dict) else {}

        nom = str(props.get("nom", "") or "").strip()
        if not nom:
            errors.append(f"feature {idx}: nom manquant")
        else:
            names[nom] += 1
            normalized_names[normalize_text(nom)] += 1

        rang_raw = props.get("rang")
        try:
            rang = int(float(rang_raw))
            if rang <= 0:
                errors.append(f"feature {idx} ({nom}): rang <= 0")
            rank_values.append(rang)
        except (TypeError, ValueError):
            errors.append(f"feature {idx} ({nom}): rang invalide")

        adresse = str(props.get("adresse", "") or "").strip()
        if not adresse:
            warnings.append(f"feature {idx} ({nom}): adresse manquante")

        if geom.get("type") != "Point":
            errors.append(f"feature {idx} ({nom}): geometrie non Point")
            continue

        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 2:
            errors.append(f"feature {idx} ({nom}): coordonnees invalides")
            continue

        lon, lat = coords
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            errors.append(f"feature {idx} ({nom}): coordonnees non numeriques")
            continue

        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            errors.append(f"feature {idx} ({nom}): coordonnees hors limites WGS84")

        key = f"{lon:.7f},{lat:.7f}"
        coords_to_names[key].append(nom)

    if rank_values:
        rank_counter = Counter(rank_values)
        duplicated_ranks = [r for r, c in rank_counter.items() if c > 1]
        if duplicated_ranks:
            warnings.append(f"rangs dupliques: {len(duplicated_ranks)}")

        rank_min = min(rank_values)
        rank_max = max(rank_values)
        expected = set(range(rank_min, rank_max + 1))
        missing = sorted(expected - set(rank_values))
        if missing:
            preview = ", ".join(str(x) for x in missing[:15])
            warnings.append(f"rangs manquants ({len(missing)}): {preview}")

    duplicated_exact_names = [(n, c) for n, c in names.items() if c > 1]
    duplicated_normalized = [(n, c) for n, c in normalized_names.items() if c > 1]
    duplicate_coords = [(k, v) for k, v in coords_to_names.items() if len(v) > 1]

    stats = {
        "total_features": len(features),
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "duplicate_exact_names": len(duplicated_exact_names),
        "duplicate_normalized_names": len(duplicated_normalized),
        "superposed_points": len(duplicate_coords),
        "rank_min": min(rank_values) if rank_values else None,
        "rank_max": max(rank_values) if rank_values else None,
    }

    report = {
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "samples": {
            "duplicate_exact_names": duplicated_exact_names[:10],
            "duplicate_normalized_names": duplicated_normalized[:10],
            "superposed_points": [
                {"coordinates": k, "schools": v[:5], "count": len(v)}
                for k, v in duplicate_coords[:10]
            ],
        },
    }

    return len(errors) == 0, report


def print_report(report: Dict[str, object]) -> None:
    stats = report.get("stats", {})
    print("Controle qualite GeoJSON")
    print("- total_features:", stats.get("total_features"))
    print("- errors_count:", stats.get("errors_count"))
    print("- warnings_count:", stats.get("warnings_count"))
    print("- duplicate_exact_names:", stats.get("duplicate_exact_names"))
    print("- duplicate_normalized_names:", stats.get("duplicate_normalized_names"))
    print("- superposed_points:", stats.get("superposed_points"))
    print("- rank_min:", stats.get("rank_min"))
    print("- rank_max:", stats.get("rank_max"))

    errors = report.get("errors", [])
    warnings = report.get("warnings", [])

    if errors:
        print("\nErreurs:")
        for msg in errors[:25]:
            print("-", msg)
        if len(errors) > 25:
            print(f"- ... et {len(errors) - 25} autres")

    if warnings:
        print("\nAvertissements:")
        for msg in warnings[:25]:
            print("-", msg)
        if len(warnings) > 25:
            print(f"- ... et {len(warnings) - 25} autres")


def main() -> int:
    parser = argparse.ArgumentParser(description="Controle qualite du GeoJSON ecoles")
    parser.add_argument("geojson", nargs="?", default="ecoles.geojson", help="Fichier GeoJSON a controler")
    parser.add_argument(
        "--report-json",
        default="",
        help="Chemin optionnel pour exporter le rapport detaille JSON",
    )
    args = parser.parse_args()

    ok, report = validate(Path(args.geojson))
    print_report(report)

    if args.report_json:
        out = Path(args.report_json)
        with out.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nRapport exporte: {out}")

    if ok:
        print("\nStatut: OK")
        return 0

    print("\nStatut: ECHEC")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
