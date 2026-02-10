# Lidar-forest-view
Utilitaire de visualisation simultanée de données lidar, photo et cartographique en contexte forestier

## Entrées au lancement

À l’ouverture, l’app demande **un répertoire de projet** (formulaire). Tous les chemins ci‑dessous sont soit ce dossier, soit relatifs à lui (sauf `memory.json`).

| Entrée | Où | Description |
|--------|-----|-------------|
| **Répertoire de projet** | Saisi au lancement | Dossier du projet. Peut être mémorisé dans `memory.json` (répertoire courant). |
| **`photo_info.csv`** | Dans le projet | CSV : `image`, `x`, `y`, `z` ; optionnel `yaw`, `pitch`, `roll`. Sinon : pas de points photo ni panorama. |
| **`tree_info.csv`** | Dans le projet | CSV : `x`, `y`, `z`, `No_tige` + autres colonnes (propriétés). Sinon : pas de points arbre. |
| **`panoramas/`** | Dans le projet | Dossier d'images ; noms = colonne `image` de `photo_info.csv` (ex. `pano0001.jpg`). |
| **`cloud.laz`** | Dans le projet | Nuage lidar principal. Sinon : console + vue 3D vide. |
| **`aero_cloud.laz`** | Dans le projet | Second nuage (ex. aéroporté). Sinon : message console. |
| **`memory.json`** | Répertoire courant | Pré-remplit le dernier répertoire projet ; mis à jour à chaque soumission. |

### Structure de projet canonique

Arborescence de référence attendue par l’app. Chaque élément est soit **généré par un outil** du dépôt, soit **à ajouter manuellement** (ou via un autre pipeline).

```
<répertoire de projet>/
├── photo_info.csv      # Généré par les outils photo (colonnes : image, timestamp, x, y, z, roll, pitch, yaw)
├── tree_info.csv       # À ajouter manuellement (colonnes : x, y, z, No_tige, + autres)
├── cloud.laz           # À ajouter manuellement (nuage lidar principal)
├── aero_cloud.laz      # À ajouter manuellement (nuage aéroporté)
└── panoramas/          # Généré par les outils photo
    ├── pano0000.jpg
    ├── pano0001.jpg
    └── ...
```

## Structure du code

Le projet est organisé en package Python `forest_view/` pour faciliter le travail en équipe et les évolutions.

### Points d’entrée

| Fichier / commande | Usage |
|--------------------|--------|
| **`main.py`** | Script à la racine : lance l’application de visualisation. Exécuter : `python main.py`. |
| **`python -m forest_view`** | Lance la même application via le module (configure OpenGL puis démarre l’app). |
| **`project_maker.py`** | Outil de création / mise à jour de projets (choix nouveau projet ou ajout de photos). Exécuter : `python project_maker.py`. |
| **`Creation_projets/Trait_photo_v6.py`** | Traitement des photos (paires, trajectoire, Hugin, export `photo_info.csv`). |
| **`Creation_projets/trait_insta360.py`** | Traitement spécifique Insta360. |
| **`Creation_projets/convert_gs_vision_v2.py`** | Conversion GS-Vision vers données projet. |

### Package `forest_view/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Expose `run` pour lancer l’app. |
| **`__main__.py`** | Point d’entrée du module : configuration OpenGL (QSurfaceFormat), création de l’application Qt et appel à `AppManager`. Définit `run()`. |
| **`app_manager.py`** | Orchestration : affiche le formulaire de choix du répertoire projet, charge `photo_info.csv` et `tree_info.csv`, crée `PhotoWindow` et `LidarWindow`, connecte les signaux entre fenêtres, charge les nuages lidar (`cloud.laz`, `aero_cloud.laz`) et les arbres. Gère aussi le changement de site. |
| **`io.py`** | Lecture/écriture fichiers : `readCSV`, `CSV_to_dict`, `writeCSV`, `readJSON`, `writeJSON`, `export_photo_info_to_csv`. Utilisé par l’app, le project maker et les scripts Creation_projets. |
| **`photo_pipeline.py`** | Traitement des photos : `get_valid_pairs`, `stitch_photos` (Hugin), `get_photo_locations`, `quaternion_to_euler`. Utilisé par les scripts Creation_projets. |
| **`forms.py`** | Formulaire de saisie de chemins : classe `DataForm` (fichier/répertoire, mémorisation dans `memory.json`). |

### Sous-package `forest_view/widgets/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Réexporte `GLWidget`, `CustomMapWidget`, `Pointer`, `PhotoPoint`, `TreePoint`, `ProprietyWidget`. |
| **`gl_panorama.py`** | Widget OpenGL `GLWidget` : affichage des panoramas équirectangulaires (sphère texturée), rotation souris, zoom molette, signaux direction caméra et pointeur. |
| **`map.py`** | Carte des points d’intérêt : `CustomMapWidget` (scène, photo/arbres, zoom, signaux panorama/caméra/propriétés) et `Pointer` (flèche direction de vue). |
| **`map_items.py`** | Éléments de la carte : `PhotoPoint` (clic = charger panorama + mettre à jour caméra) et `TreePoint` (clic = afficher propriétés, sélection). |
| **`properties.py`** | Widget `ProprietyWidget` : affichage des champs (ex. propriétés d’un arbre sélectionné). |

### Sous-package `forest_view/windows/`

| Fichier | Rôle |
|---------|------|
| **`__init__.py`** | Réexporte `PhotoWindow` et `LidarWindow`. |
| **`photo_window.py`** | Fenêtre principale photo : `PhotoWindow` (layout avec `GLWidget`, carte, groupe propriétés, bouton « Changer de site »). Gère `change_site` (réinit carte, propriétés, panorama). |
| **`lidar_window.py`** | Fenêtre 3D lidar : `LidarWindow` (PyVista), chargement nuages `.laz`, affichage des arbres, synchronisation caméra avec la fenêtre photo, picking sur les arbres, changement de site. |

### Racine du dépôt

| Fichier | Rôle |
|---------|------|
| **`Librairie.py`** | Stub de compatibilité : réexporte PyQt6, stdlib et symboles `forest_view` (forms, io, photo_pipeline, widgets) pour que les scripts qui font `from Librairie import *` (`project_maker.py`, `Creation_projets/*.py`) fonctionnent sans modification. À terme, migrer ces scripts vers des imports explicites depuis `forest_view.*`. |

## Contexte de développement
# Guide d'utilisateur
## Table des matières
[Environnement](#environnement)

[Lancement](#lancement)

[Navigation](#navigation)

[Création de projets](#création-de-projets)
## Environnement
Python
- PyQt
- Pyvista et PyvistaQt
- OpenGL
- numpy
- laspy et laszip

## Lancement

### Mise en page
Mettre des images!

## Navigation
### Carte
- La carte (en bas à gauche), permet de naviguer entre les différentes photos (points bleus) et arbres (points verts).
- Cliquer sur un point de photo affichera la photo dans l'espace prévu à cet effet.
- Cliquer sur un point d'arbre affichera la donnée disponible sur celui-ci dans la liste de propriétés. Ce point deviendra jaune sur la carte et dans le nuage lidar.
- La roue permet de zoomer
- Les déplacements sont fait en tenant le bouton gauche de la souris et en la déplaçant.
### Photo
- En tenant le bouton gauche de la souris et en la déplaçant, l'orientation de l'image change.
- La roue gère le zoom
### Lidar
- En tenant le bouton gauche de la souris et en la déplaçant, l'orientation du nuage de points change.
- En appuyant plutôt sur la roue, la position d'observation change
- La roue gère le zoom.
- En appuyant sur un point d'arbre avec le bouton droit de la souris, les données de celui-ci s'affichent. Ce point deviendr jaune dans le nuage lidar et sur la carte
### Changement de site
- Cliquer sur le bouton à cet effet en bas à droite de la fenêtre photo
- Sélectionner l'emplacement du dossier du nouveau site dans l'explorateur de données
- Attendre que le nouveau site charge

## Création de projets
