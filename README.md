# Lidar-forest-view

Utilitaire de visualisation simultanée de données lidar, photo et cartographique en contexte forestier.

## Table des matières

- [Entrées au lancement](#entrées-au-lancement)
- [Système de coordonnées (CRS) et carte](#système-de-coordonnées-crs-et-carte)
- [Structure du code](#structure-du-code)
- [Environnement et dépendances](#environnement-et-dépendances)
- [Scripts batch (Windows)](#scripts-batch-windows)
- [Lancement](#lancement)
- [Guide d'utilisateur](#guide-dutilisateur)
- [Création de projets](#création-de-projets)

---

## Entrées au lancement

À l'ouverture, l'application demande **un répertoire de projet** (formulaire). Tous les chemins ci‑dessous sont soit ce dossier, soit relatifs à lui (sauf `appsettings.json`). Pour le **type et le format** de chaque entrée, voir [docs/formats_entrees.md](docs/formats_entrees.md).

| Entrée | Où | Description |
|--------|-----|-------------|
| **Répertoire de projet** | Saisi au lancement | Dossier du projet. Peut être mémorisé dans `appsettings.json` (répertoire courant). |
| **`photo_info.csv`** | Dans le projet | CSV : `image`, `x`, `y`, `z` ; optionnel `yaw`, `pitch`, `roll`. Les colonnes `x`, `y` sont interprétées dans le CRS choisi (voir [CRS et carte](#système-de-coordonnées-crs-et-carte)). |
| **`tree_info.csv`** | Dans le projet | CSV : `x`, `y`, `z`, `No_tige` + autres colonnes (propriétés). `x`, `y` dans le même CRS que la carte. |
| **`panoramas/`** | Dans le projet | Dossier d'images ; noms = colonne `image` de `photo_info.csv` (ex. `pano0001.jpg`). |
| **`cloud.laz`** | Dans le projet | Nuage lidar principal. Sinon : console + vue 3D vide. |
| **`aero_cloud.laz`** | Dans le projet | Second nuage (ex. aéroporté). Sinon : message console. |
| **`appsettings.json`** | Répertoire courant | Pré-remplit le dernier répertoire projet ; mis à jour à chaque soumission. |

### Structure de projet canonique

```
<répertoire de projet>/
├── photo_info.csv      (colonnes : image, x, y, z, optionnel yaw, pitch, roll)
├── tree_info.csv       (colonnes : x, y, z, No_tige, + autres)
├── cloud.laz
├── aero_cloud.laz
└── panoramas/
    ├── pano0000.jpg
    ├── pano0001.jpg
    └── ...
```

### Outils de préparation des données

| Outil | Rôle |
|-------|------|
| **`project_maker.py`** | Crée le projet + `panoramas/` + `photo_info.csv` à partir de GS-vision, Insta 360, Eagle ou Hémisphérique. |
| **`scripts/Trait_photo_v6.py`** | Flux Hémisphérique seul. Script autonome. |
| **`scripts/trait_insta360.py`** | Flux Insta 360 seul. Script autonome. |
| **`scripts/convert_gs_vision_v2.py`** | Conversion GS-Vision vers structure projet. Script autonome. |

Voir [scripts/README.md](scripts/README.md) pour l'usage des scripts. Ils ne génèrent pas `tree_info.csv`, `cloud.laz` ni `aero_cloud.laz` ; à ajouter séparément pour la visualisation complète.

---

## Système de coordonnées (CRS) et carte

### Coordonnées des données

Les colonnes **`x`** et **`y`** de `photo_info.csv` et `tree_info.csv` ne sont **pas nécessairement** en longitude/latitude (WGS84). Elles peuvent être dans un système projeté, par exemple **EPSG:2949** (NAD83(CSRS) / MTM zone 7), en mètres.

L'application effectue une **reprojection à la volée** du CRS des données vers **WGS84 (EPSG:4326)** pour :

- afficher les points sur la **carte** (scène en degrés) ;
- aligner les données avec le **fond de carte OSM** (WGS84).

Si le CRS choisi n'est pas 4326, le module **pyproj** est requis (`pip install pyproj`). Sans pyproj et avec un CRS autre que WGS84, un message d'erreur explicite s'affiche.

### Menu Carte > CRS

Dans la fenêtre unifiée, le menu **Carte** permet de définir le CRS des données :

- **CRS > EPSG:2949 – NAD83(CSRS) / MTM zone 7** (valeur par défaut au démarrage) ;
- **CRS > EPSG:4326 – WGS84** (données déjà en lon/lat) ;
- **CRS > Autre…** : saisie d'un code EPSG personnalisé (ex. 2950).

Après changement de CRS, la carte est redessinée : points et fond OSM restent alignés.

### Carte : étendue et fond OSM

- L'**étendue** de la carte est calculée à partir des points (photos et arbres), avec une marge, afin que le jeu de données reste entièrement visible.
- Le **fond de carte** est constitué de tuiles OpenStreetMap (WGS84). Les points sont dessinés au-dessus des tuiles.
- La **synchronisation carte ↔ table d'attributs** : clic sur un point sur la carte sélectionne la ligne correspondante dans la table ; sélection d'une ligne dans la table met en surbrillance le point correspondant sur la carte (sans déplacer la vue, pour conserver le fond de carte et les points à l'écran).

---

## Structure du code

Le projet est organisé en package Python **`forest_view/`**.

### Points d'entrée

| Fichier / commande | Usage |
|--------------------|--------|
| **`main.py`** | Lance l'application de visualisation : `python main.py`. |
| **`python -m forest_view`** | Même application via le module (configure OpenGL puis démarre l'app). |
| **`project_maker.py`** | Création ou mise à jour de projets : `python project_maker.py`. |
| **`scripts/Trait_photo_v6.py`** | Traitement Hémisphérique. Script autonome. |
| **`scripts/trait_insta360.py`** | Traitement Insta360. Script autonome. |
| **`scripts/convert_gs_vision_v2.py`** | Conversion GS-Vision. Script autonome. |

### Package `forest_view/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Expose `run` pour lancer l'app. |
| **`__main__.py`** | Point d'entrée du module : configuration OpenGL, création de l'application Qt, appel à `AppManager`. |
| **`app_manager.py`** | Orchestration : formulaire répertoire projet, chargement CSV et nuages lidar, création des fenêtres (Photo, Lidar, unifiée), connexion des signaux, gestion du CRS de la carte et du changement de site. |
| **`crs_utils.py`** | Reprojection des coordonnées : `data_to_wgs84(x, y, crs_epsg)` vers WGS84 pour la scène et OSM ; nécessite pyproj si CRS ≠ 4326. |
| **`io.py`** | Lecture/écriture : `readCSV`, `CSV_to_dict`, `writeCSV`, `readJSON`, `writeJSON`, `export_photo_info_to_csv`. |
| **`photo_pipeline.py`** | Traitement des photos : `get_valid_pairs`, `stitch_photos` (Hugin), `get_photo_locations`, `quaternion_to_euler`. |
| **`forms.py`** | Formulaire de saisie de chemins (`DataForm`) et mémorisation dans `appsettings.json`. |
| **`logger.py`** | Logging avec rotation quotidienne et archivage. |

### Sous-package `forest_view/widgets/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Réexporte `GLWidget`, `CustomMapWidget`, `Pointer`, `PhotoPoint`, `TreePoint`, `ProprietyWidget`, `LoadingOverlay`, `show_overlay`. |
| **`gl_panorama.py`** | Widget OpenGL `GLWidget` : panoramas équirectangulaires, rotation, zoom, signaux caméra et pointeur. |
| **`map.py`** | `CustomMapWidget` : scène en WGS84 (lon, -lat), points photo/arbres, fond OSM, étendue calée sur les données, signaux panorama/caméra/propriétés ; `Pointer` (direction de vue). |
| **`map_items.py`** | `PhotoPoint` (clic = charger panorama, mise à jour caméra) ; `TreePoint` (clic = propriétés, sélection, alignement avec la table par index de ligne). |
| **`properties.py`** | `ProprietyWidget` : table d'attributs (ex. arbres), synchronisation avec la carte (sélection ligne ↔ point). |
| **`loading_overlay.py`** | `LoadingOverlay` et `show_overlay` : superposition de chargement (message + barre) sur toute la fenêtre au démarrage de la navigation. |

### Sous-package `forest_view/windows/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Réexporte `PhotoWindow` et `LidarWindow`. |
| **`photo_window.py`** | `PhotoWindow` : GLWidget (panorama), carte, propriétés, case « Vérouiller la vue à l'arbre ». Gère `change_site` et `replot_map` (CRS). |
| **`lidar_window.py`** | `LidarWindow` : vue 3D PyVista, nuages `.laz`, arbres, synchronisation caméra avec la fenêtre photo, picking arbres. |
| **`unified_window.py`** | Fenêtre unifiée : panneaux Lidar et Photo côte à côte, carte et propriétés en overlay ; menu **Fichier** (Changer de site, Quitter), menu **Carte** (CRS). |

### Racine du dépôt

| Fichier | Rôle |
|---------|------|
| **`Librairie.py`** | Stub de compatibilité pour les scripts utilisant `from Librairie import *` (`project_maker.py`, `scripts/*.py`). |

---

## Environnement et dépendances

- **Python** (3.x). L’application a été développée et testée sous **Python 3.12** (et versions antérieures compatibles).
- **PyQt6**
- **PyVista** et **PyVistaQt**
- **OpenGL**
- **numpy**
- **pyproj** (reprojection CRS pour la carte ; requis si les données ne sont pas en WGS84)
- **laspy** et **laszip** (nuages de points)

---

## Scripts batch (Windows)

Sous Windows, deux scripts batch permettent de configurer un environnement virtuel et de lancer l’application sans activer le venv à la main.

| Script | Rôle |
|--------|------|
| **`create_venv.bat`** | Crée un environnement virtuel `.venv` à la racine du dépôt, active pip à jour, puis installe toutes les dépendances listées dans `requirements.txt`. À exécuter une fois après un clône ou pour recréer l’environnement. Si `.venv` existe déjà, le script ne fait rien. |
| **`run_app.bat`** | Lance l’application avec le Python du venv (`.venv\Scripts\python.exe main.py`). Vérifie que `.venv` existe ; sinon, affiche un message invitant à exécuter d’abord `create_venv.bat`. Les arguments éventuels sont transmis à `main.py`. |

**Utilisation :**

1. Double-cliquer sur `create_venv.bat` (ou l’exécuter en ligne de commande) pour créer le venv et installer les dépendances.
2. Double-cliquer sur `run_app.bat` (ou l’exécuter en ligne de commande) pour démarrer l’application.

Les deux scripts se placent automatiquement dans le répertoire du dépôt (là où se trouvent `main.py` et `requirements.txt`), quel que soit le répertoire courant au moment de l’appel.

---

## Lancement

1. Exécuter `python main.py` ou `python -m forest_view` (ou sous Windows : `run_app.bat` après avoir exécuté `create_venv.bat` une fois ; voir [Scripts batch (Windows)](#scripts-batch-windows)).
2. Choisir le répertoire du projet (mémorisé dans `appsettings.json`).
3. La fenêtre unifiée s'ouvre (Lidar | Photo + carte + propriétés). Un overlay « Chargement des nuages de points… » couvre toute la fenêtre pendant le chargement, puis disparaît.

---

## Guide d'utilisateur

### Carte

- La carte (panneau latéral) affiche les points de **photos** (bleus) et d'**arbres** (verts). L'étendue est calée sur les données.
- **Cliquer sur un point photo** : affiche le panorama et met à jour la caméra (lidar + pointeur).
- **Cliquer sur un point arbre** : affiche les propriétés dans la table ; le point devient jaune sur la carte et dans le nuage lidar.
- **Sélectionner une ligne dans la table d'attributs** : le point correspondant est mis en surbrillance sur la carte (sans déplacer la vue).
- **Zoom** : molette. **Déplacement** : glisser avec le bouton gauche de la souris.
- **CRS** : menu **Carte > CRS** pour choisir le système de coordonnées des données (ex. EPSG:2949, 4326 ou autre).

### Photo (panorama)

- Glisser avec le bouton gauche pour changer l'orientation.
- Molette pour le zoom.

### Lidar

- Glisser avec le bouton gauche pour faire tourner le nuage.
- Molette centrale pour déplacer la position d'observation ; molette pour le zoom.
- Clic droit sur un point d'arbre : affichage des données ; le point devient jaune dans le lidar et sur la carte.

### Vérouillage à l'arbre

- Cocher **« Vérouiller la vue à l'arbre »** : l'arbre sélectionné reste centré dans les vues photo et lidar.
- Changer de photo ou d'arbre recentre sur le nouvel élément.
- Décocher pour désactiver le mode.

### Changement de site

- Menu **Fichier > Changer de site** (ou bouton dédié selon la disposition).
- Choisir le répertoire du nouveau projet.
- Attendre la fin du chargement.

---

## Création de projets

1. Lancer **`python project_maker.py`**.
2. Choisir **« Créer un nouveau projet »** ou **« Ajouter des photos à un projet existant »**.
   - **Nouveau projet** : indiquer l'emplacement du dossier, puis le nom du projet.
   - **Ajout de scans** : indiquer le dossier du projet existant.
3. Saisir le nombre de scans et remplir le formulaire (type de données, champs). Pour **Insta 360**, voir [docs/formats_scan_insta360.md](docs/formats_scan_insta360.md).
4. Soumettre et attendre la fin du traitement.
5. Pour une visualisation complète, ajouter manuellement **`tree_info.csv`**, **`cloud.laz`** et **`aero_cloud.laz`** dans le dossier projet si nécessaire.
