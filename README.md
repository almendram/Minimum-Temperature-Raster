# Minimum-Temperature-Raster

Aplicación para el análisis de la temperatura mínima (Tmin) del Perú a partir de datos ráster. El objetivo es extraer estadísticas zonales, analizar riesgos climáticos (heladas y oleadas de frío) y proponer políticas públicas basadas en evidencia.

---

## 📂 Estructura del repositorio

```
Minimum-Temperature-Raster/
│
├── app/                # Aplicación Streamlit
├── data/               # Datos: ráster, shapefiles/GeoJSON
├── notebooks/          # Notebooks de análisis y EDA
├── requirements.txt    # Dependencias
├── README.md           # Este archivo
└── app.py              # Script principal de la app
```

---

## ⚙️ Instalación y ejecución

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/usuario/Minimum-Temperature-Raster.git
   cd Minimum-Temperature-Raster
   ```

2. Crear entorno virtual e instalar dependencias:

   ```bash
   conda create -n tmin_env python=3.10
   conda activate tmin_env
   pip install -r requirements.txt
   ```

3. Ejecutar la aplicación Streamlit:

   ```bash
   streamlit run app.py
   ```

---

## 📊 Funcionalidades

* Carga y visualización de ráster GeoTIFF de Tmin.
* Estadísticas zonales por distrito/provincia/departamento: `mean, min, max, std, p10, p90` + métrica personalizada.
* Gráficos de distribución y clasificación de distritos según Tmin.
* Mapa coroplético estático (PNG).
* Descarga de resultados en CSV.
* Sección de **políticas públicas**: diagnóstico + 3 propuestas con población objetivo, presupuesto estimado y KPIs.

---

## 🌍 Políticas Públicas Propuestas

1. **Viviendas térmicas (ISUR) en zonas altoandinas**

   * Objetivo: reducir enfermedades respiratorias por heladas.
   * KPI: -20% casos IRA en MINSA/ESSALUD.

2. **Refugios y kits antiheladas para ganado**

   * Objetivo: reducir mortalidad de alpacas y ovinos.
   * KPI: -15% pérdidas ganaderas en SENASA.

3. **Alertas tempranas y adaptación agrícola**

   * Objetivo: proteger cultivos sensibles a heladas y friaje.
   * KPI: +10% rendimiento agrícola en campañas priorizadas.

---

## 🚀 Implementación pública

La aplicación está disponible en Streamlit Community Cloud:
👉 [https://minimum-temperature-raster.streamlit.app](https://minimum-temperature-raster.streamlit.app)

---

