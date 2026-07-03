#!/usr/bin/env python3
"""
Extrait un CSV (nom, rang, adresse) depuis le PDF CGTSIM en ligne.

Source attendue: rapport CGTSIM de classification des ecoles.
Le parsing est base sur le texte PDF et dedupe les doublons entre sections.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Le package 'pypdf' est requis. Installez-le avec: python -m pip install pypdf"
    ) from exc


DEFAULT_CGTSIM_PDF_URL = (
    "https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf"
)


@dataclass
class CgtsimRow:
    nom: str
    rang: int
    ordre: str


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def download_pdf(url: str, out_path: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; cgtsim-extractor/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = resp.read()
    out_path.write_bytes(payload)


def parse_rows_from_pdf(pdf_path: Path) -> Tuple[List[CgtsimRow], Dict[str, int]]:
    reader = PdfReader(str(pdf_path))

    row_pattern = re.compile(
        r"(?<!\d)(?P<rang>\d{1,3})\s+(?P<css>[A-Z][A-Z0-9\-]{2,})\s+"
        r"(?P<ordre>Primaire|Secondaire)\s+(?P<nom>.+?)\s+"
        r"(?P<indice>\d,\d{5})\s+(?P<tranche>\d{1,2}-\d{1,3}%)",
        re.IGNORECASE | re.DOTALL,
    )

    raw_matches = 0
    rows: List[CgtsimRow] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if not text.strip():
            continue

        for m in row_pattern.finditer(text):
            try:
                rang = int(m.group("rang"))
            except ValueError:
                continue

            if rang <= 0:
                continue

            raw_matches += 1
            ordre = m.group("ordre").capitalize()
            nom = m.group("nom").strip(" ,;:-")

            if not nom:
                continue
            rows.append(CgtsimRow(nom=nom, rang=rang, ordre=ordre))

    dedup: Dict[Tuple[int, str, str], CgtsimRow] = {}
    for row in rows:
        key = (row.rang, row.ordre, normalize_text(row.nom))
        if key not in dedup:
            dedup[key] = row

    unique_rows = sorted(dedup.values(), key=lambda r: (r.rang, r.ordre, normalize_text(r.nom)))

    stats = {
        "pages": len(reader.pages),
        "raw_matches": raw_matches,
        "unique_rows": len(unique_rows),
    }
    return unique_rows, stats


def write_csv(rows: List[CgtsimRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["nom", "rang", "adresse", "ordre_ens"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "nom": row.nom,
                    "rang": row.rang,
                    "adresse": "",
                    "ordre_ens": row.ordre,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extraction CSV depuis PDF CGTSIM")
    parser.add_argument("--pdf-url", default=DEFAULT_CGTSIM_PDF_URL, help="URL du PDF CGTSIM")
    parser.add_argument("--out", required=True, help="Chemin du CSV de sortie")
    args = parser.parse_args()

    out_csv = Path(args.out)

    try:
        with tempfile.TemporaryDirectory(prefix="cgtsim_pdf_") as tmp_dir:
            pdf_path = Path(tmp_dir) / "cgtsim.pdf"
            download_pdf(args.pdf_url, pdf_path)
            rows, stats = parse_rows_from_pdf(pdf_path)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Erreur extraction CGTSIM: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print("Aucune ligne extraite du PDF CGTSIM.", file=sys.stderr)
        return 2

    write_csv(rows, out_csv)

    print(f"CSV CGTSIM genere: {out_csv}")
    print("Stats extraction:")
    for k, v in stats.items():
        print(f"- {k}: {v}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
