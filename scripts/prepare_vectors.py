# scripts/prepare_vectors.py
"""
Prepara el shapefile de distritos:
- Normaliza nombres (quita diacríticos, mayúsculas)
- Genera/asegura columna UBIGEO (6 dígitos)
- Repara geometrías (buffer(0) donde es necesario)
- Fuerza CRS = EPSG:4326
- Guarda GeoJSON limpio en data/processed/distritos_clean.geojson
- Guarda un CSV de referencia con UBIGEO y NAME_CLEAN en data/processed/distritos_lookup.csv
"""
import geopandas as gpd
from pathlib import Path
import unicodedata
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

IN_PATH = Path("data/DISTRITOS.shp")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_GEOJSON = OUT_DIR / "distritos_clean.geojson"
OUT_CSV = OUT_DIR / "distritos_lookup.csv"

def normalize_text(s):
    if pd.isna(s):
        return s
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.upper().strip()

def main():
    logging.info("Cargando shapefile desde: %s", IN_PATH)
    if not IN_PATH.exists():
        logging.error("Archivo no encontrado: %s", IN_PATH)
        raise FileNotFoundError(f"{IN_PATH} no existe. Coloca el shapefile en data/")

    gdf = gpd.read_file(IN_PATH)

    # seleccionar columna de nombre
    possible_name_cols = [c for c in gdf.columns if c.lower() in ("name","nombre","distrito","distr","nomdist","nombdist")]
    name_col = possible_name_cols[0] if possible_name_cols else None
    if name_col is None:
        logging.warning("No se encontró columna de nombre conocida; se usará la primera columna no geométrica.")
        non_geom = [c for c in gdf.columns if c.lower() != "geometry"]
        name_col = non_geom[0] if non_geom else None

    logging.info("Usando columna de nombre: %s", name_col)

    # Normalizar nombres
    if name_col is not None:
        gdf['NAME_CLEAN'] = gdf[name_col].apply(normalize_text)
    else:
        gdf['NAME_CLEAN'] = [f"DIST_{i}" for i in range(len(gdf))]

    # UBIGEO: buscar columnas con ubi o code
    ubigeo_cols = [c for c in gdf.columns if 'ubi' in c.lower() or 'cod' in c.lower() or 'ubigeo' in c.lower()]
    if ubigeo_cols:
        ub_col = ubigeo_cols[0]
        gdf['UBIGEO'] = gdf[ub_col].astype(str).str.replace(r'\.0+$', '', regex=True).str.zfill(6)
        logging.info("Usando columna UBIGEO detectada: %s", ub_col)
    else:
        logging.warning("No se detectó columna UBIGEO; se generará UBIGEO temporal a partir del índice.")
        gdf['UBIGEO'] = gdf.index.astype(int).astype(str).str.zfill(6)

    # Fix geometrías: buffer(0) para "cleaning", eliminar geometrías vacías
    def safe_fix(geom):
        try:
            if geom is None:
                return None
            if not getattr(geom, "is_valid", True):
                return geom.buffer(0)
            return geom
        except Exception:
            return None

    gdf['geometry'] = gdf['geometry'].apply(safe_fix)
    gdf = gdf[~gdf['geometry'].isna()].copy()

    # filtrar por geometría válida
    gdf = gdf[gdf.is_valid]

    # Forzar CRS a EPSG:4326
    if gdf.crs is None:
        logging.warning("CRS desconocido. Se asume EPSG:4326.")
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)

    # Guardar GeoJSON y CSV de lookup
    gdf.to_file(OUT_GEOJSON, driver="GeoJSON")
    gdf[['UBIGEO', 'NAME_CLEAN']].drop_duplicates().to_csv(OUT_CSV, index=False)

    logging.info("GeoJSON limpio guardado en: %s", OUT_GEOJSON)
    logging.info("CSV de referencia guardado en: %s", OUT_CSV)

if __name__ == "__main__":
    main()
