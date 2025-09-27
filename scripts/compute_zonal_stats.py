import rioxarray as rxr
import rasterio
import rasterio.mask
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# 🔹 Ajusta rutas a tus archivos
RASTER_PATH = Path("data/raw/tmin_raster.tif")  # tu raster
VECTOR_PATH = Path("data/processed/distritos_clean.geojson")  # distritos limpios
OUT_DIR = Path("outputs")
OUT_TABLES = OUT_DIR / "tables"
OUT_MAPS = OUT_DIR / "maps"

# Crear carpetas de salida
OUT_TABLES.mkdir(parents=True, exist_ok=True)
OUT_MAPS.mkdir(parents=True, exist_ok=True)

def compute_stats_for_band(band_index, da, gdf):
    """
    Calcula estadísticas zonales personalizadas para cada distrito.
    """
    stats_list = []
    with rasterio.open(RASTER_PATH) as src:
        nodata = src.nodata
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
            if nodata is not None:
                arr[arr == nodata] = np.nan
            # Reescalar si valores parecen estar *10
            if np.nanmax(arr) > 100:
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
    print("Cargando distritos...")
    gdf = gpd.read_file(VECTOR_PATH).to_crs(epsg=4326)

    print("Abriendo raster...")
    da = rxr.open_rasterio(RASTER_PATH, masked=True)
    bands = da.sizes.get("band", 1)
    print(f"Raster con {bands} banda(s)")

    all_years = []
    for b in range(1, bands + 1):
        year = 2020 + (b - 1)
        print(f"\nProcesando banda {b} -> año {year}")
        stats_list = compute_stats_for_band(b, da, gdf)
        df_stats = pd.DataFrame(stats_list)
        df_out = pd.concat([gdf.reset_index(drop=True), df_stats], axis=1)
        df_out["YEAR"] = year

        export_cols = [
            "UBIGEO", "NAME_CLEAN", "YEAR", "count", "mean",
            "min", "max", "std", "p10", "p90", "pct_below_0C", "geometry"
        ]

        gdf_out = gpd.GeoDataFrame(df_out[export_cols], geometry="geometry", crs=gdf.crs)

        # Guardar resultados
        geojson_path = OUT_TABLES / f"zonalstats_{year}.geojson"
        csv_path = OUT_TABLES / f"zonalstats_{year}.csv"
        gdf_out.to_file(geojson_path, driver="GeoJSON")
        gdf_out.drop(columns="geometry").to_csv(csv_path, index=False)

        print(f"Guardado: {geojson_path}  {csv_path}")
        all_years.append(gdf_out.drop(columns="geometry"))

    # Maestro con todos los años
    df_master = pd.concat(all_years, ignore_index=True)
    df_master.to_csv(OUT_TABLES / "zonalstats_all_years.csv", index=False)
    print("\n✅ Hecho. Archivos en:", OUT_TABLES)

if __name__ == "__main__":
    main()
