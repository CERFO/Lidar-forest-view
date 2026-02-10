# Scripts de préparation des données

Ces scripts sont des **outils autonomes** : ils ne sont pas appelés par l’application ni par `project_maker.py`. Chacun peut être lancé directement pour créer ou compléter un répertoire de projet à partir d’une seule source de données.

Ils produisent la même structure que le viewer attend : `panoramas/` et `photo_info.csv` (voir la [structure de projet canonique](../README.md#structure-de-projet-canonique) dans le README principal).

| Script | Source | Usage |
|--------|--------|--------|
| **`Trait_photo_v6.py`** | Hémisphérique (fisheye + Hugin) | Trajectoire, calibration, répertoire des photos brutes, racine Hugin. |
| **`trait_insta360.py`** | Insta 360 | Fichier trajectoire CSV + répertoire des photos panoramiques. |
| **`convert_gs_vision_v2.py`** | GS-Vision | Fichier JSON GS-Vision + répertoire des photos. |

**Alternative :** pour gérer plusieurs types de sources dans une seule interface, utiliser **`project_maker.py`** à la racine du dépôt.

Lancer un script depuis la racine du dépôt :

```bash
python scripts/Trait_photo_v6.py
python scripts/trait_insta360.py
python scripts/convert_gs_vision_v2.py
```
