# app/app.py
import streamlit as st
import pandas as pd
import geopandas as gpd
from pathlib import Path
from PIL import Image

st.set_page_config(page_title="Tmin Perú — Dashboard", layout="wide")
st.title("Tmin Perú — Estadísticas zonales y políticas públicas")

# Base del proyecto (un nivel arriba de app/)
BASE_DIR = Path(__file__).resolve().parent.parent
OUT_TABLES = BASE_DIR / "outputs" / "tables"
OUT_MAPS = BASE_DIR / "outputs" / "maps"

# detectar años disponibles
files = list(OUT_TABLES.glob("zonalstats_*.csv"))
years = []
for f in files:
    try:
        year = int(f.stem.split("_")[1])
        years.append(year)
    except ValueError:
        continue  # ignora archivos como zonalstats_all.csv
years = sorted(years) if years else [2020]

# Sidebar
with st.sidebar:
    st.header("Filtros")
    year = st.selectbox("Año", years)
    dept_filter = st.text_input("Filtrar por departamento (nombre, opcional)", value="")
    threshold = st.slider("Umbral Tmin (°C) para resaltar", -20, 10, 0)
    top_n = st.slider("Top N distritos (clasificación)", 5, 50, 15)

# Cargar datos
csv_path = OUT_TABLES / f"zonalstats_{year}.csv"
if not csv_path.exists():
    st.error(f"No se encontró {csv_path}. Ejecuta scripts/compute_zonal_stats.py primero.")
    st.stop()

df = pd.read_csv(csv_path)
# aplicar filtro simple por departamento si existe columna
if dept_filter.strip():
    df = df[df['NAME_CLEAN'].str.contains(dept_filter.upper()) | df['NAME_CLEAN'].str.contains(dept_filter.capitalize())]

st.markdown(f"### Datos: año {year} — {len(df)} distritos")

# Mostrar mapa pre-renderizado si existe
map_png = OUT_MAPS / f"choropleth_tmin_{year}.png"
if map_png.exists():
    img = Image.open(map_png)
    st.image(img, use_column_width=True)
else:
    st.info("Mapa estático no encontrado. Ejecuta notebooks/01_EDA.py para generarlo.")

# Distribución
st.subheader("Distribución de Tmin media")
hist_png = OUT_MAPS / f"hist_mean_tmin_{year}.png"
if hist_png.exists():
    st.image(hist_png, use_column_width=True)
else:
    st.info("Histograma no encontrado.")

# Clasificaciones
st.subheader(f"Top {top_n} distritos con Tmin media más baja (riesgo heladas)")
df_sorted = df.sort_values("mean")
st.dataframe(df_sorted.head(top_n)[['UBIGEO','NAME_CLEAN','mean','p10','pct_below_0C']])

st.subheader(f"Top {top_n} distritos con Tmin media más alta")
st.dataframe(df_sorted.tail(top_n)[['UBIGEO','NAME_CLEAN','mean','p90']])

# Descarga CSV
csv_bytes = df.to_csv(index=False).encode('utf-8')
st.download_button("Descargar tabla (CSV)", csv_bytes, file_name=f"zonalstats_{year}.csv", mime='text/csv')

# Políticas públicas (breve)
st.header("Políticas públicas — Propuestas priorizadas")
st.markdown("""
- **Medida 1:** Kits térmicos para hogares en distritos de mayor riesgo (p10 ≤ -5°C).  
- **Medida 2:** Refugios y capacitación para productores ganaderos en zonas altoandinas.  
- **Medida 3:** Sistema de alerta temprana + campañas escolares en regiones amazónicas por oleadas de frío.  
(Ver `docs/politicas.md` para detalle de objetivos, población objetivo, costos y KPIs.)
""")