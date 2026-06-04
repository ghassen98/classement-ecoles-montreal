#!/usr/bin/env python3
"""
Script de validation des données GeoJSON pour la carte des écoles.
Vérifie la cohérence des données, les types, les valeurs manquantes et les doublons.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def validate_geojson(filepath):
    """Charge et valide un fichier GeoJSON."""
    print(f"Validation de {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Erreur: fichier introuvable: {filepath}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON: {e}")
        return False
    
    # Vérifier structure globale
    if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
        print("❌ Format non valide: doit être un FeatureCollection")
        return False
    
    features = data.get('features', [])
    if not isinstance(features, list):
        print("❌ 'features' doit être un tableau")
        return False
    
    print(f"✓ Structure GeoJSON valide")
    print(f"  Total features: {len(features)}")
    
    errors = []
    warnings = []
    nom_counts = Counter()
    coords_to_names = defaultdict(list)
    rank_distribution = defaultdict(int)
    
    for idx, feat in enumerate(features):
        if not isinstance(feat, dict) or feat.get('type') != 'Feature':
            errors.append(f"Feature {idx}: type invalide")
            continue
        
        props = feat.get('properties', {})
        geom = feat.get('geometry', {})
        
        # Vérifier nom
        nom = str(props.get('nom', '')).strip()
        if not nom:
            errors.append(f"Feature {idx}: champ 'nom' manquant ou vide")
        else:
            nom_counts[nom] += 1
        
        # Vérifier rang
        try:
            rang = int(float(props.get('rang', 0)))
            if rang <= 0 or rang > 350:
                warnings.append(f"Feature {idx} ({nom}): rang {rang} hors plage attendue (1-350)")
            rank_distribution[rang // 100] += 1
        except (ValueError, TypeError):
            errors.append(f"Feature {idx} ({nom}): rang invalide ou non numérique")
        
        # Vérifier adresse
        adresse = str(props.get('adresse', '')).strip()
        if not adresse:
            warnings.append(f"Feature {idx} ({nom}): champ 'adresse' manquant")
        
        # Vérifier géométrie
        if geom.get('type') != 'Point':
            errors.append(f"Feature {idx} ({nom}): géométrie doit être Point")
            continue
        
        coords = geom.get('coordinates', [])
        if not isinstance(coords, list) or len(coords) != 2:
            errors.append(f"Feature {idx} ({nom}): coordonnées invalides")
            continue
        
        lon, lat = coords
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            errors.append(f"Feature {idx} ({nom}): coordonnées hors limites WGS84")
        
        coords_to_names[tuple(coords)].append(nom)
    
    # Rapporter doublons de noms
    duplicate_names = [(n, c) for n, c in nom_counts.items() if c > 1]
    if duplicate_names:
        print(f"\n⚠️  Doublons de noms ({len(duplicate_names)}):")
        for nom, count in sorted(duplicate_names, key=lambda x: -x[1])[:10]:
            print(f"  - {nom}: {count} fois")
    
    # Rapporter superpositions de points
    duplicate_coords = [(k, len(v)) for k, v in coords_to_names.items() if len(v) > 1]
    if duplicate_coords:
        print(f"\n⚠️  Points superposés ({len(duplicate_coords)}):")
        for coords, count in sorted(duplicate_coords, key=lambda x: -x[1])[:5]:
            schools = coords_to_names[coords]
            print(f"  - {coords}: {count} écoles")
            for s in schools[:3]:
                print(f"      • {s}")
    
    # Résumé distribution rangs
    print(f"\n📊 Distribution des rangs:")
    for bucket in sorted(rank_distribution.keys()):
        start = bucket * 100 + 1
        end = (bucket + 1) * 100
        count = rank_distribution[bucket]
        bar = "█" * min(50, count // 2)
        print(f"  Rang {start:3d}–{end:3d}: {count:3d} écoles {bar}")
    
    # Rapporter erreurs
    if errors:
        print(f"\n❌ Erreurs trouvées ({len(errors)}):")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... et {len(errors) - 20} autres")
        return False
    
    if warnings:
        print(f"\n⚠️  Avertissements ({len(warnings)}):")
        for warn in warnings[:10]:
            print(f"  - {warn}")
        if len(warnings) > 10:
            print(f"  ... et {len(warnings) - 10} autres")
    
    print(f"\n✅ Validation complète: fichier valide")
    return True


if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'ecoles.geojson'
    success = validate_geojson(filepath)
    sys.exit(0 if success else 1)
