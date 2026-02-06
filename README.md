# Lidar-forest-view
Utilitaire de visualisation simultanée de données lidar, photo et cartographique en contexte forestier
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
