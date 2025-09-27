# notebooks/01_EDA.py
"""
EDA automático — genera por cada archivo outputs/tables/zonalstats_<YEAR>.csv:
 - hist_mean_tmin_<YEAR>.png      (distribución)
 - top15_cold_<YEAR>.png         (top 15 distritos más fríos)
 - top15_hot_<YEAR>.png          (top 15 distritos más cálidos)
 - top15_cold_<YEAR>.csv         (CSV top15 fríos)
 - top15_hot_<YEAR>.csv          (CSV top15 cálidos)
 - choropleth_tmin_<YEAR>.png    (mapa coroplético si existe el geojson correspondiente)
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import warnings
import matplotlib as mpl

# Base (raíz del proyecto)
BASE_DIR = Path(__file__).resolve().parent.parent

OUT_TABLES = BASE_DIR / "outputs" / "tables"
OUT_MAPS = BASE_DIR / "outputs" / "maps"
OUT_MAPS.mkdir(parents=True, exist_ok=True)

# encontrar archivos zonalstats
csv_files = sorted(OUT_TABLES.glob("zonalstats_*.csv"))

if not csv_files:
    print("No se encontraron zonalstats_*.csv en:", OUT_TABLES)
    raise SystemExit(1)

# función auxiliar para dibujar barras horizontales limpias
def save_barh(df, name_col, value_col, outpath, title, top_n=15, invert=True):
    df_plot = df[[name_col, value_col]].dropna().head(top_n)
    if df_plot.empty:
        print(f" - Aviso: no hay datos para {outpath.name}")
        return
    plt.figure(figsize=(8, max(4, 0.35 * len(df_plot))))
    plt.barh(df_plot[name_col], df_plot[value_col])
    if invert:
        plt.gca().invert_yaxis()
    plt.xlabel(f"{value_col} (°C)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.close()

# función para crear choropleth (azul frío → amarillo cálido, blanco = sin datos)
def save_choropleth(gdf, column, outpath, title):
    try:
        gdf = gdf.to_crs(epsg=4326)
        fig, ax = plt.subplots(1, 1, figsize=(10, 14))
        vmin = float(gdf[column].min())
        vmax = float(gdf[column].max())
        norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap("YlGnBu_r")  # 🔵 frío → 🟡 cálido
        # plot con colorbar
        gdf.plot(
            column=column, ax=ax,
            legend=False, cmap=cmap, norm=norm, linewidth=0.1,
            missing_kwds={      # distritos sin datos = blanco
                "color": "white",
                "label": "Sin datos"
            }
        )
        sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm._A = []  # hack para colorbar
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label(f"{column} (°C)")
        ax.set_title(title)
        ax.set_axis_off()
        plt.tight_layout()
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        plt.close(fig)
    except Exception as e:
        # fallback simple
        try:
            ax = gdf.plot(column=column, legend=True, figsize=(10, 14))
            ax.set_title(title)
            ax.set_axis_off()
            fig = ax.get_figure()
            fig.savefig(outpath, dpi=200, bbox_inches="tight")
            plt.close(fig)
        except Exception as e2:
            print(f"  Error generando coropleta {outpath.name}: {e2}")

# main loop: por cada csv disponible
for csv_path in csv_files:
    try:
        stem = csv_path.stem  # zonalstats_2020
        parts = stem.split("_")
        if len(parts) < 2:
            print("Nombre de archivo inesperado (se salta):", csv_path.name)
            continue
        year_token = parts[1]
        try:
            year = int(year_token)
        except ValueError:
            print(f"Archivo {csv_path.name} no parece contener año válido (se salta).")
            continue

        print(f"\nProcesando año: {year}  ({csv_path.name})")

        df = pd.read_csv(csv_path)
        required_cols = {"UBIGEO", "NAME_CLEAN", "mean", "p10", "p90", "pct_below_0C"}
        if not required_cols.intersection(set(df.columns)):
            print(f"  Aviso: {csv_path.name} no contiene todas las columnas esperadas. Columnas encontradas: {list(df.columns)}")

        # 1) Distribución (histograma)
        hist_path = OUT_MAPS / f"hist_mean_tmin_{year}.png"
        vals = df["mean"].dropna() if "mean" in df.columns else pd.Series(dtype=float)
        if not vals.empty:
            plt.figure(figsize=(8,5))
            plt.hist(vals, bins=60)
            plt.title(f"Distribución de Tmin media por distrito - {year}")
            plt.xlabel("Tmin media (°C)")
            plt.ylabel("Número de distritos")
            plt.tight_layout()
            plt.savefig(hist_path, dpi=200, bbox_inches="tight")
            plt.close()
            print("  Guardado:", hist_path.name)
        else:
            print("  No hay valores 'mean' para histogram (se salta).")

        # 2) Clasificación (top 15 más fríos y top 15 más cálidos) + export CSV
        df_sorted = df.sort_values("mean") if "mean" in df.columns else df
        top_n = 15
        top15_cold_path = OUT_MAPS / f"top15_cold_{year}.png"
        top15_hot_path = OUT_MAPS / f"top15_hot_{year}.png"
        top15_cold_csv = OUT_MAPS / f"top15_cold_{year}.csv"
        top15_hot_csv = OUT_MAPS / f"top15_hot_{year}.csv"

        if "NAME_CLEAN" in df_sorted.columns and "mean" in df_sorted.columns:
            save_barh(df_sorted.head(top_n), "NAME_CLEAN", "mean", top15_cold_path,
                      f"Top {top_n} distritos con Tmin media más baja - {year}", top_n=top_n)
            df_sorted.head(top_n)[['UBIGEO','NAME_CLEAN','mean','p10','pct_below_0C']].to_csv(top15_cold_csv, index=False)
            print("  Guardado:", top15_cold_path.name, top15_cold_csv.name)

            save_barh(df_sorted.tail(top_n).iloc[::-1], "NAME_CLEAN", "mean", top15_hot_path,
                      f"Top {top_n} distritos con Tmin media más alta - {year}", top_n=top_n)
            df_sorted.tail(top_n)[['UBIGEO','NAME_CLEAN','mean','p90']].iloc[::-1].to_csv(top15_hot_csv, index=False)
            print("  Guardado:", top15_hot_path.name, top15_hot_csv.name)
        else:
            print("  Columnas NAME_CLEAN/mean no disponibles para generar clasificación.")

        # 3) Mapa coroplético: preferimos el GeoJSON que creó compute_zonal_stats.py
        geojson_path = OUT_TABLES / f"zonalstats_{year}.geojson"
        choropleth_path = OUT_MAPS / f"choropleth_tmin_{year}.png"
        if geojson_path.exists():
            try:
                gdf = gpd.read_file(geojson_path)
                if "mean" in gdf.columns:
                    save_choropleth(gdf, "mean", choropleth_path, f"Tmin media por distrito - {year}")
                    print("  Guardado:", choropleth_path.name)
                else:
                    print("  GeoJSON no contiene columna 'mean' para hacer coropleta.")
            except Exception as e:
                print("  Error leyendo geojson:", e)
        else:
            print(f"  Mapa estático no encontrado para {year}. Ejecuta scripts/compute_zonal_stats.py")

    except Exception as e:
        print("Error procesando", csv_path.name, ":", e)

print("\nTodos los años procesados. PNGs y CSVs en:", OUT_MAPS)
