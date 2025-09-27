# scripts/prepare_vectors.py
import geopandas as gpd
from pathlib import Path
import unicodedata
import pandas as pd

IN_PATH = Path("data/DISTRITOS.shp")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_GEOJSON = OUT_DIR / "distritos_clean.geojson"

def normalize_text(s):
    if pd.isna(s):
        return s
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.upper().strip()

def main():
    print("Cargando shapefile...")
    gdf = gpd.read_file(IN_PATH)
    # revisar columnas comunes
    possible_name_cols = [c for c in gdf.columns if c.lower() in ("name","nombre","distrito","distr")]
    name_col = possible_name_cols[0] if possible_name_cols else gdf.columns[0]
    print("Usando columna de nombre:", name_col)
    # Normalizar
    gdf['NAME_CLEAN'] = gdf[name_col].apply(normalize_text)
    # UBIGEO
    ubigeo_cols = [c for c in gdf.columns if 'ubi' in c.lower() or 'code' in c.lower()]
    if ubigeo_cols:
        gdf['UBIGEO'] = gdf[ubigeo_cols[0]].astype(str).str.zfill(6)
    else:
        # crear UBIGEO con índice si no existe (temporal)
        gdf['UBIGEO'] = gdf.index.astype(str).str.zfill(6)
    # Fix geometries
    gdf['geometry'] = gdf['geometry'].buffer(0)
    gdf = gdf[gdf.is_valid]
    # Forzar CRS a EPSG:4326
    if gdf.crs is None:
        print("Advertencia: CRS desconocido. Se asume EPSG:4326.")
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)
    # guardar
    gdf.to_file(OUT_GEOJSON, driver="GeoJSON")
    print("GeoJSON limpio guardado en:", OUT_GEOJSON)

if __name__ == "__main__":
    main()
