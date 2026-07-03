# Analyse des Sources de Données - Classement des Écoles Montréal

## 📊 État Actuel

### Source Utilisée
- **Document**: Classification des écoles 2022
- **Autorité**: CGTSIM (Centre de gestion et de technologies de l'information scolaire de Montréal)
- **Lien**: https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf
- **Année des données**: 2022 (données datant de plus de 3 ans)
- **Statut**: Non à jour

### Données Actuelles dans le Repo
- **346 écoles** validées
- **6 doublons** de noms
- **33 points superposés** (annexes partageant des coordonnées)
- **Dernier update**: Non spécifié (données manquantes dans README)

---

## 🔍 Sources Alternative Identifiées

### 1. **CGTSIM - Source Officielle (Améliorée)**
| Critère | Détails |
|---------|---------|
| **Site officiel** | https://www.cgtsim.qc.ca |
| **URL classifications** | ❌ Page 404 (lien déplacé) |
| **PDF 2022** | ✅ Disponible via archive |
| **Fréquence** | Annuelle (février-mars) |
| **Fiabilité** | ⭐⭐⭐⭐⭐ (source officielle) |
| **Actions recommandées** | Chercher les rapports 2023, 2024, 2025 |

**Recommandation**: Chercher directement sur le site CGTSIM:
- Naviguer vers: https://www.cgtsim.qc.ca/ressources/ ou /documents/
- Contacter: service@cgtsim.qc.ca pour les derniers rapports

### 2. **Portail des Données Ouvertes Montréal**
| Critère | Détails |
|---------|---------|
| **URL** | https://data.montreal.ca |
| **Type de données** | Données publiques, géospatiales |
| **Actualité** | Généralement à jour |
| **Fiabilité** | ⭐⭐⭐⭐ (source officielle municipale) |
| **Données pertinentes** | Coordonnées écoles, services, adresses |
| **Format** | CSV, GeoJSON, API |
| **Limitation** | Pas de ranking pédagogique directs |

**Actions recommandées**:
```bash
# Chercher sur le portail:
# Mots-clés: "écoles", "schools", "primaire", "secondaire"
# Filtre par: Éducation, Géospatial
```

### 3. **Ministère de l'Éducation du Québec (MEQ)**
| Critère | Détails |
|---------|---------|
| **Site** | https://www.quebec.ca/education |
| **Données disponibles** | Listes d'écoles, accréditation, programmes |
| **Format** | Web, potentiellement PDF, API |
| **Fiabilité** | ⭐⭐⭐⭐⭐ (source gouvernementale) |
| **Actualité** | À vérifier |
| **Limitation** | Peut ne pas inclure les rankings |

### 4. **Données Géolocalisées Alternatives**

#### Google Places / Google Maps API
- ✅ Coordonnées GPS à jour
- ✅ Adresses validées
- ✅ Photos, avis
- ❌ API payante
- ❌ Pas de ranking pédagogique

#### OpenStreetMap (OSM)
- ✅ Données open source
- ✅ Gratuit
- ✅ Tag standardisés pour écoles
- ❌ Peu à jour pour certains emplacements
- Base: https://wiki.openstreetmap.org/wiki/Schools

#### Overpass API (requête OSM)
```
# Query pour récupérer écoles à Montréal:
[bbox:45.407,-73.977,45.707,-73.473];
(
  node["amenity"="school"];
  way["amenity"="school"];
  relation["amenity"="school"];
);
out geom;
```

### 5. **Sources de Ranking Pédagogique Alternatives**

#### A. Statistiques Éducation Québec (SEQ)
- Statistiques officielles par école
- Taux de réussite, abandon scolaire, etc.
- Format: Rapports PDF/Excel
- Actualité: Annuelle

#### B. Institut de la statistique du Québec (ISQ)
- Données démographiques, scolaires
- Reports: https://www.stat.gouv.qc.ca

#### C. Alloprof (Ressource Éducative)
- Données publiques sur écoles
- Potentiellement des rankings
- Format: Web/API possible

---

## 📈 Comparaison des Sources

| Source | Actualité | Fiabilité | Données Complètes | Format | Accès |
|--------|-----------|-----------|-------------------|--------|-------|
| CGTSIM (2022) | ❌ 2022 | ⭐⭐⭐⭐⭐ | ✅ | PDF | Manuel |
| CGTSIM (Récent) | ⏳ À chercher | ⭐⭐⭐⭐⭐ | ✅ | ? | Probable |
| Données Montréal | ✅ Régulier | ⭐⭐⭐⭐ | ⚠️ Partiel | CSV/GeoJSON | API |
| MEQ | ✅ | ⭐⭐⭐⭐⭐ | ⚠️ Partiel | Web/PDF | Web |
| Google Maps | ✅ Temps réel | ⭐⭐⭐ | ✅ | API | Payante |
| OpenStreetMap | ⚠️ Variable | ⭐⭐⭐ | ✅ | XML/JSON | Gratuite |
| ISQ | ✅ Annuelle | ⭐⭐⭐⭐⭐ | ⚠️ Stats | JSON/PDF | Web |

---

## 🎯 Recommandations

## ✅ Implémentation démarrée dans le repo

### Intégration Source 1 + Source 2 (script d'extraction)
- Script ajouté: `build_cgtsim_montreal_geojson.py`
- Objectif: fusionner un classement CGTSIM (CSV) avec un dataset Montréal (CSV/GeoJSON)
- Sorties:
   - `ecoles.geojson` (fusion)
   - `unmatched_cgtsim_montreal.csv` (non-correspondances à corriger)

### Contrôle des données (script dédié)
- Script ajouté: `control_data_quality.py`
- Contrôles couverts:
   - structure GeoJSON
   - rangs dupliqués/manquants
   - doublons de noms exacts et normalisés
   - points superposés
   - coordonnées invalides
- Export possible d'un rapport JSON complet pour audit

### Commandes de base
```bash
python3 build_cgtsim_montreal_geojson.py --cgtsim <csv_cgtsim> --montreal <csv_ou_geojson_montreal>
python3 validate_geojson.py ecoles.geojson
python3 control_data_quality.py ecoles.geojson --report-json qa_report.json
```

### Phase 1: Mise à Jour Rapide (1-2 jours)
1. **Chercher les rapports CGTSIM 2024-2025**
   - Visite: https://www.cgtsim.qc.ca/ressources/ ou /documents/
   - Contact direct: info@cgtsim.qc.ca
   - Chercher: "classification des écoles 2024", "2025"

2. **Vérifier le Portail Données Montréal**
   - URL: https://data.montreal.ca
   - Chercher dataset "écoles" ou "schools"
   - Extraire les coordonnées GPS validées

### Phase 2: Enrichissement des Données (1 semaine)
1. **Combiner plusieurs sources**
   - CGTSIM pour le ranking pédagogique
   - Données Montréal pour géolocalisation validée
   - Google Maps/OSM pour valider/compléter les coordonnées

2. **Automatiser la mise à jour**
   ```python
   # Pseudo-code
   - Scraper CGTSIM pour nouveaux rapports (annuel)
   - Valider GeoJSON contre API géolocalisation
   - Fusionner avec données Montréal
   - Détecter et alerter sur changements
   ```

### Phase 3: Améliorations Long-terme (2-4 semaines)
1. **Ajouter des données supplémentaires**
   - Taux de réussite (ISQ)
   - Photos de façade (Google Street View)
   - Transport scolaire (STCUM)
   - Services spécialisés

2. **Créer une API**
   - Endpoint: `/api/schools`
   - Filtres: rang, type, arrondissement, proximité
   - Format: GeoJSON, JSON

---

## 🔗 Liens Utiles pour Recherche

### Ressources Officielles
- CGTSIM: https://www.cgtsim.qc.ca
- MEQ: https://www.quebec.ca/education
- ISQ: https://www.stat.gouv.qc.ca
- Montréal Données: https://data.montreal.ca

### Données Ouvertes
- Google Dataset Search: https://datasetsearch.research.google.com
- Recherche avancée: "écoles Montréal filetype:csv OR filetype:geojson"

### Outils de Validation
- GeoJSON Validator: https://geojson.io
- Overpass Turbo (OSM): https://overpass-turbo.eu

---

## 📝 Notes de Suivi

- [ ] Contacter CGTSIM pour accès aux rapports 2024-2025
- [ ] Télécharger et analyser dataset Montréal
- [ ] Mettre à jour validate_geojson.py pour inclure checks supplémentaires
- [ ] Créer script d'import pour sources alternatives
- [ ] Documenter processus de mise à jour mensuelle
- [ ] Implémenter alertes pour changeements significatifs

---

**Dernière mise à jour**: 16 juin 2026  
**Statut**: Analyse en cours - À passer en revue
