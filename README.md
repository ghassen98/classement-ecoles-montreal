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

## Source des Données

Les données des écoles et de leur classement proviennent du rapport officiel :  
[Classification des écoles, CGTSIM 2022](https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf).

## Technologies Utilisées

- **Leaflet.js** : Bibliothèque JavaScript pour la création de cartes interactives.
- **Leaflet Search** : Extension Leaflet pour intégrer la recherche par nom d'école.
- **HTML, CSS, JavaScript** : Technologies de base pour le front-end.

## Auteur

Créé par **Ghassen Aouinti** dans le cadre d'un projet open source.