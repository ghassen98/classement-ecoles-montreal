# CI/CD

Ce dossier contient les artefacts DevOps lies aux pipelines CI/CD.

## Convention
- `devops/ci/` : definitions de pipeline et documentation d'execution.
- Les workflows GitHub Actions actifs peuvent etre references ici et places dans `.github/workflows/` si necessaire.

## Pipeline propose
- Validation syntaxe Python
- Verification qualite des donnees (scripts/validate_geojson.py)
- Controle metier (scripts/control_data_quality.py)
