# app/app.py
import streamlit as st
import pandas as pd
import geopandas as gpd
from pathlib import Path
from PIL import Image

# -------------------------------
# Configuración de la página
# -------------------------------
st.set_page_config(
    page_title="Tmin Perú — Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🌡️ Tmin Perú — Estadísticas zonales y políticas públicas")

# -------------------------------
# Directorios base
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
OUT_TABLES = BASE_DIR / "outputs" / "tables"
OUT_MAPS = BASE_DIR / "outputs" / "maps"

# -------------------------------
# Detectar años disponibles
# -------------------------------
files = list(OUT_TABLES.glob("zonalstats_*.csv"))
years = []
for f in files:
    try:
        year = int(f.stem.split("_")[1])
        years.append(year)
    except ValueError:
        continue  # ignora archivos como zonalstats_all_years.csv
years = sorted(years) if years else [2020]

# -------------------------------
# Sidebar (filtros)
# -------------------------------
with st.sidebar:
    st.header("⚙️ Filtros")
    year = st.selectbox("Año", years)
    dept_filter = st.text_input("Filtrar por departamento (opcional)", value="")
    threshold = st.slider("Umbral Tmin (°C) para resaltar", -20, 10, 0)
    top_n = st.slider("Top N distritos (clasificación)", 5, 50, 15)

# -------------------------------
# Cargar datos
# -------------------------------
csv_path = OUT_TABLES / f"zonalstats_{year}.csv"
if not csv_path.exists():
    st.error(f"No se encontró {csv_path}. Ejecuta `scripts/compute_zonal_stats.py` primero.")
    st.stop()

df = pd.read_csv(csv_path)

# aplicar filtro simple por departamento si existe
if dept_filter.strip():
    df = df[
        df['NAME_CLEAN'].str.contains(dept_filter.upper()) |
        df['NAME_CLEAN'].str.contains(dept_filter.capitalize())
    ]

st.markdown(f"### 📅 Año {year} — {len(df)} distritos disponibles")

# -------------------------------
# Tabs principales
# -------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["🌍 Mapa", "📊 Distribución", "🏆 Rankings", "📑 Políticas"]
)

# ----- TAB 1: MAPA -----
with tab1:
    st.header("🌍 Mapa de Tmin media")
    map_png = OUT_MAPS / f"choropleth_tmin_{year}.png"
    if map_png.exists():
        img = Image.open(map_png)
        st.image(img, use_column_width=True)
    else:
        st.info("Mapa estático no encontrado. Ejecuta `notebooks/01_EDA.py` para generarlo.")

# ----- TAB 2: DISTRIBUCIÓN -----
with tab2:
    st.header("📊 Distribución de Tmin media")
    hist_png = OUT_MAPS / f"hist_mean_tmin_{year}.png"
    if hist_png.exists():
        img = Image.open(hist_png)
        st.image(img, use_column_width=True)
    else:
        st.info("Histograma no encontrado.")

# ----- TAB 3: RANKINGS -----
with tab3:
    st.header(f"🏆 Top {top_n} distritos")
    df_sorted = df.sort_values("mean")

    st.subheader("❄️ Más fríos (riesgo heladas)")
    st.dataframe(df_sorted.head(top_n)[['UBIGEO','NAME_CLEAN','mean','p10','pct_below_0C']])

    st.subheader("🔥 Más cálidos")
    st.dataframe(df_sorted.tail(top_n)[['UBIGEO','NAME_CLEAN','mean','p90']])

    # Botón de descarga
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Descargar tabla completa (CSV)",
        csv_bytes,
        file_name=f"zonalstats_{year}.csv",
        mime='text/csv'
    )

# ----- TAB 4: POLÍTICAS -----
with tab4:
    st.header("📑 Políticas públicas — Propuestas priorizadas")
    st.markdown("""
    - **Medida 1:** Kits térmicos para hogares en distritos de mayor riesgo (p10 ≤ -5°C).  
    - **Medida 2:** Refugios y capacitación para productores ganaderos en zonas altoandinas.  
    - **Medida 3:** Sistema de alerta temprana + campañas escolares en regiones amazónicas por oleadas de frío.  

    📌 Ver archivo `docs/politicas.md` para detalle de:
    - Objetivos  
    - Población objetivo  
    - Costos estimados  
    - KPIs de seguimiento  
    """)
