# scripts/compute_zonal_stats.py

import rioxarray as rxr
import rasterio
import rasterio.mask
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

RASTER_PATH = Path("data/raw/tmin_raster.tif")
VECTOR_PATH = Path("data/processed/distritos_clean.geojson")
OUT_DIR = Path("outputs")
OUT_TABLES = OUT_DIR / "tables"
OUT_MAPS = OUT_DIR / "maps"

OUT_TABLES.mkdir(parents=True, exist_ok=True)
OUT_MAPS.mkdir(parents=True, exist_ok=True)

def compute_stats_for_band(band_index, src_path, gdf):
    """
    Para una banda dada (index empieza en 1), recorre las geometrías y calcula
    las estadísticas requeridas. Devuelve lista de dicts (orden coincidente con gdf).
    """
    stats_list = []
    with rasterio.open(src_path) as src:
        nodata = src.nodata
        meta_dtype = src.dtypes[0]
        logging.info("  Banda %s: dtype=%s nodata=%s", band_index, meta_dtype, nodata)
        for _, row in tqdm(gdf.iterrows(), total=len(gdf), desc=f"Banda {band_index}"):
            geom = [row.geometry.__geo_interface__]
            try:
                out_image, out_transform = rasterio.mask.mask(src, geom, crop=True, indexes=band_index)
            except Exception:
                stats = dict(count=0, mean=np.nan, min=np.nan, max=np.nan, std=np.nan,
                             p10=np.nan, p90=np.nan, pct_below_0C=np.nan)
                stats_list.append(stats)
                continue

            arr = out_image.astype("float32")[0]
            # nodata -> NaN
            if nodata is not None:
                arr = np.where(arr == nodata, np.nan, arr)

            # si el raster está en °C*10 (valores grandes), reescalar
            maxval = np.nanmax(arr)
            if np.isfinite(maxval) and maxval > 100:
                arr = arr / 10.0

            vals = arr[~np.isnan(arr)]
            if vals.size == 0:
                stats = dict(count=0, mean=np.nan, min=np.nan, max=np.nan, std=np.nan,
                             p10=np.nan, p90=np.nan, pct_below_0C=np.nan)
            else:
                stats = dict(
                    count=int(vals.size),
                    mean=float(np.nanmean(vals)),
                    min=float(np.nanmin(vals)),
                    max=float(np.nanmax(vals)),
                    std=float(np.nanstd(vals, ddof=0)),
                    p10=float(np.nanpercentile(vals, 10)),
                    p90=float(np.nanpercentile(vals, 90)),
                    pct_below_0C=float((vals <= 0).sum() / vals.size)
                )
            stats_list.append(stats)
    return stats_list

def main():
    logging.info("Leyendo vectores desde: %s", VECTOR_PATH)
    if not VECTOR_PATH.exists():
        logging.error("GeoJSON de vectores no encontrado. Ejecuta scripts/prepare_vectors.py")
        raise FileNotFoundError(VECTOR_PATH)

    gdf = gpd.read_file(VECTOR_PATH).to_crs(epsg=4326)

    logging.info("Abriendo ráster: %s", RASTER_PATH)
    if not RASTER_PATH.exists():
        logging.error("Ráster no encontrado en: %s", RASTER_PATH)
        raise FileNotFoundError(RASTER_PATH)

    da = rxr.open_rasterio(RASTER_PATH, masked=True)
    # detectar número de bandas (rioxarray usa 'band' en sizes)
    bands = int(da.sizes.get("band", 1))
    logging.info("Raster con %d banda(s).", bands)

    all_years = []
    for b in range(1, bands + 1):
        year = 2020 + (b - 1)
        logging.info("Procesando banda %d -> año %d", b, year)
        stats_list = compute_stats_for_band(b, RASTER_PATH, gdf)
        df_stats = pd.DataFrame(stats_list)
        df_out = pd.concat([gdf.reset_index(drop=True), df_stats], axis=1)
        df_out["YEAR"] = year

        export_cols = [
            "UBIGEO", "NAME_CLEAN", "YEAR", "count", "mean",
            "min", "max", "std", "p10", "p90", "pct_below_0C", "geometry"
        ]
        # Asegurar columnas existentes
        existing = [c for c in export_cols if c in df_out.columns]
        gdf_out = gpd.GeoDataFrame(df_out[existing], geometry="geometry", crs=gdf.crs)

        geojson_path = OUT_TABLES / f"zonalstats_{year}.geojson"
        csv_path = OUT_TABLES / f"zonalstats_{year}.csv"
        # Guardar GeoJSON y CSV (CSV sin geometría)
        gdf_out.to_file(geojson_path, driver="GeoJSON")
        gdf_out.drop(columns="geometry").to_csv(csv_path, index=False)
        logging.info("Guardado: %s  %s", geojson_path, csv_path)
        all_years.append(gdf_out.drop(columns="geometry"))

    # Maestro multi-año
    if all_years:
        df_master = pd.concat(all_years, ignore_index=True)
        df_master.to_csv(OUT_TABLES / "zonalstats_all_years.csv", index=False)
        logging.info("Archivo maestro guardado: %s", OUT_TABLES / "zonalstats_all_years.csv")

    logging.info("✅ Hecho. Archivos en: %s", OUT_TABLES)

if __name__ == "__main__":
    main()
