"""
Utilitaires de système de coordonnées : reprojection à la volée du CRS des données (ex. EPSG:2949)
vers WGS84 (EPSG:4326) pour la scène et le fond de carte OSM. Nécessite pyproj si les données ne sont pas déjà en WGS84.
"""
from __future__ import annotations

_TRANSFORMER_CACHE: dict[int, "object"] = {}


def _get_transformer(epsg: int):
    """Retourne un transformateur EPSG -> EPSG:4326 (lon, lat), ou None si identité / pyproj absent."""
    if epsg in _TRANSFORMER_CACHE:
        return _TRANSFORMER_CACHE[epsg]
    if epsg == 4326:
        _TRANSFORMER_CACHE[4326] = None
        return None
    try:
        from pyproj import Transformer
        t = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        _TRANSFORMER_CACHE[epsg] = t
        return t
    except Exception:
        _TRANSFORMER_CACHE[epsg] = None
        return None


def data_to_wgs84(x: float, y: float, crs_epsg: int) -> tuple[float, float]:
    """
    Reprojecte (x, y) du CRS donné vers (longitude, latitude) en WGS84 (EPSG:4326).
    - Si crs_epsg vaut 4326, retourne (x, y) tel quel (lon, lat).
    - Sinon, exige pyproj ; lève une erreur si la transformation est indisponible.
    """
    if crs_epsg == 4326:
        return (float(x), float(y))
    t = _get_transformer(crs_epsg)
    if t is None:
        raise RuntimeError(
            "pyproj est requis pour reprojeter de EPSG:%s vers WGS84 (EPSG:4326) pour le fond de carte OSM. "
            "Installer avec : pip install pyproj" % crs_epsg
        )
    lon, lat = t.transform(x, y)
    return (float(lon), float(lat))


def has_pyproj() -> bool:
    """Retourne True si pyproj est disponible pour la transformation de coordonnées."""
    try:
        from pyproj import Transformer
        return True
    except ImportError:
        return False
