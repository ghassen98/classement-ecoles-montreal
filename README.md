# Application SIG Web : Carte Interactive des Écoles

Cette application est un outil SIG Web basé sur [Leaflet.js](https://leafletjs.com/) permettant de visualiser, rechercher et explorer les écoles dans une carte interactive. L'application affiche les écoles sous forme de points avec des styles personnalisés basés sur leur rang. Un outil de recherche intégré permet de localiser les écoles par nom, avec une fonctionnalité d'autocomplétion et de recherche partielle pour une expérience utilisateur plus fluide.

## Fonctionnalités

- **Affichage des écoles** : Les écoles sont représentées par des marqueurs de différentes couleurs selon leur rang.
- **Popup d'information** : Chaque école dispose d'une popup affichant le nom, le rang et l'adresse complète.
- **Recherche par nom** : Un outil de recherche intégré permet de trouver des écoles en tapant partiellement le nom.
- **Style visuel dynamique** : Les points sont colorés selon le rang :
  - **Vert** pour un rang inférieur à 100.
  - **Orange** pour un rang entre 101 et 220.
  - **Rouge** pour un rang supérieur à 220.
- **Clustering intelligent** : Regroupe les écoles superposées avec un clic pour les séparer (spiderfy).
- **Recherche avancée** : Insensible aux accents, tirets, avec distinction des homonymes par adresse et rang.
- **Légende interactive** : Affiche les classes de rang et le total d'écoles visibles.

## Installation

1. **Clonez le dépôt** :
   ```bash
   git clone https://github.com/votre-utilisateur/nom-du-repo.git
   ```

2. **Placez les données** : Assurez-vous que le fichier `ecoles.geojson` est dans le même répertoire que `index.html`.

3. **Lancez un serveur local** : Utilisez Python pour démarrer un serveur local :
    ```bash
    python -m http.server 8000
    ```

4. **Accédez à l'application** : Ouvrez un navigateur et allez à [http://localhost:8000/index.html](http://localhost:8000/index.html).

## Exemple de Données GeoJSON

Les données GeoJSON des écoles sont structurées comme suit :

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "nom": "École A",
        "rang": 1,
        "adresse": "123 Rue Principale"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [-73.6, 45.5]
      }
    }
  ]
}
```

## Validation et Qualité des Données

Un script de validation automatisé est fourni pour vérifier l'intégrité du fichier GeoJSON:

```bash
python3 validate_geojson.py ecoles.geojson
```

### Extraction multi-sources (CGTSIM + Données Montréal)

Un nouveau script permet de fusionner:
- le classement CGTSIM (rang, nom)
- les données ouvertes Montréal (coordonnées, adresse)

Dataset Montréal branché (URL exacte):
- `https://donnees.montreal.ca/dataset/763fe3b8-cdc3-4b8a-bbbd-a0a9bc587c56/resource/5ca7cdb8-f86f-4038-b5a8-657446c75427/download/lieux_d_interet.geojson`
- filtre recommandé: `Catégorie = Établissement scolaire`

Pré-requis:
- convertir la source CGTSIM en CSV tabulaire (colonnes minimales: nom + rang)
- récupérer un CSV ou GeoJSON Montréal contenant nom + longitude + latitude

Note pipeline:
- si `data/cgtsim_classement.csv` est absent, le script one-shot le génère automatiquement depuis la source CGTSIM en ligne (PDF officiel), via `extract_cgtsim_pdf_to_csv.py`.

Exemple d'exécution:

```bash
python3 build_cgtsim_montreal_geojson.py \
  --cgtsim data/cgtsim_classement.csv \
  --montreal "https://donnees.montreal.ca/dataset/763fe3b8-cdc3-4b8a-bbbd-a0a9bc587c56/resource/5ca7cdb8-f86f-4038-b5a8-657446c75427/download/lieux_d_interet.geojson" \
  --montreal-filter-field "Catégorie" \
  --montreal-filter-value "Établissement scolaire" \
  --montreal-filter-mode equals \
  --out ecoles.geojson \
  --unmatched-out unmatched_cgtsim_montreal.csv
```

Le script produit:
- `ecoles.geojson` (fusion finale)
- `unmatched_cgtsim_montreal.csv` (écoles CGTSIM sans correspondance)

### Contrôle des données (nouveau)

Un second script complète la validation structurelle avec des contrôles métier:
- cohérence des rangs (doublons, trous)
- doublons de noms exacts et normalisés
- points superposés
- coordonnées invalides

Commande:

```bash
python3 control_data_quality.py ecoles.geojson --report-json qa_report.json
```

Pipeline recommandé:

```bash
python3 build_cgtsim_montreal_geojson.py --cgtsim <csv_cgtsim> --montreal <csv_ou_geojson_montreal>
python3 validate_geojson.py ecoles.geojson
python3 control_data_quality.py ecoles.geojson --report-json qa_report.json
```

### Commande unique (script shell)

Un script one-shot exécute extraction + validation + contrôle:

```bash
./run_cgtsim_montreal_pipeline.sh data/cgtsim_classement.csv ecoles.geojson qa_report.json
```

Forcer une autre URL CGTSIM (ex: nouvelle année):

```bash
CGTSIM_PDF_URL="https://www.cgtsim.qc.ca/.../classification.pdf" \
./run_cgtsim_montreal_pipeline.sh data/cgtsim_classement.csv
```

Variables d'environnement optionnelles:

```bash
MONTREAL_SOURCE="https://donnees.montreal.ca/dataset/763fe3b8-cdc3-4b8a-bbbd-a0a9bc587c56/resource/5ca7cdb8-f86f-4038-b5a8-657446c75427/download/lieux_d_interet.geojson" \
MONTREAL_FILTER_FIELD="Catégorie" \
MONTREAL_FILTER_VALUE="Établissement scolaire" \
MONTREAL_FILTER_MODE="equals" \
FUZZY_THRESHOLD="0.86" \
./run_cgtsim_montreal_pipeline.sh data/cgtsim_classement.csv
```

Le script rapporte:
- Erreurs structurelles (géométrie invalide, champs manquants, types incorrects)
- Avertissements (doublons de noms, points superposés, rangs hors plage)
- Distribution des rangs et statistiques générales

### Résultats actuels
- **346 écoles** valides
- **6 doublons** de noms (écoles avec annexes portant le même nom)
- **33 points superposés** (écoles partageant la même coordonnée, notamment annexes)

## Source des Données

Les données des écoles et de leur classement proviennent du rapport officiel de la Commission de gouvernance et de vérification du rendement:
- Document: [Classification des écoles 2022](https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf)
- Autorité: Centre de gestion et de technologies de l'information scolaire de Montréal (CGTSIM)

### Processus de mise à jour
1. **Récupérer la source** : Télécharger le dernier rapport PDF du classement des écoles.
2. **Extraire les données** : Convertir le PDF en format tabulaire (Excel/CSV) avec colonnes: nom, rang, adresse, longitude, latitude.
3. **Valider** : Exécuter le script `validate_geojson.py` pour contrôler la cohérence.
4. **Remplacer** : Substituer le fichier `ecoles.geojson` avec les nouvelles données.
5. **Tester** : Ouvrir `http://localhost:8000/index.html` pour vérifier le rendu et la recherche.
6. **Committer** : Créer un commit avec le message `chore: update school rankings from CGTSIM YYYY`.

### Fréquence recommandée
- Vérification mensuelle de la source officielle
- Mise à jour complète annuelle (généralement février/mars)

## Technologies Utilisées

- **Leaflet.js 1.9.4** : Bibliothèque JavaScript pour cartes interactives (sécurisée avec crossorigin).
- **Leaflet MarkerCluster** : Clustering automatique des écoles superposées.
- **Leaflet MarkerCluster Spiderfy** : Séparation des points au clic (spiderfy).
- **Leaflet Search** : Recherche par nom d'école avec filtrage avancé.
- **HTML5, CSS3, JavaScript ES6** : Technologies front-end modernes.

## Historique des Améliorations

### v1.0 (initiale)
- Affichage basique des écoles sur carte Leaflet
- Popup simple avec nom, rang, adresse
- Recherche basique par nom

### v2.0 
- ✅ **Sécurité CDN**: Leaflet 1.9.4 avec crossorigin
- ✅ **Robustesse**: Gestion d'erreur HTTP + message utilisateur
- ✅ **Sécurité popup**: Contenu échappé (pas d'injection HTML)
- ✅ **Recherche**: Insensible aux accents et tirets
- ✅ **Superpositions**: Clustering automatique des points proches
- ✅ **UX**: Légende interactive + compteur d'écoles + fitBounds
- ✅ **Validation**: Script de QA automatisé pour les données

### v3.0
- ✅ **Affichage homonymes**: Liste enrichie avec adresse et rang pour distinguer les écoles portant le même nom
- ✅ **Clustering amélioré**: Configuration fine avec `disableClusteringAtZoom`, `maxClusterRadius`, icônes personnalisées
- ✅ **Spiderfy avancé**: Séparation automatique des points superposés au clic avec hint utilisateur
- ✅ **Zoom intelligent**: Navigation fluide via `spiderfyZoomToShowLayer` pour recherche/homonymes

## Auteur

Créé par **Ghassen Aouinti** dans le cadre d'un projet open source.
