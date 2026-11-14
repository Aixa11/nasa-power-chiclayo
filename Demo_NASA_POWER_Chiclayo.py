"""Demo NASA POWER para la mentoría NASA Space Apps Chiclayo 2026.

Uso:
    python -m pip install streamlit pandas requests
    streamlit run Demo_NASA_POWER_Chiclayo.py

Si no hay conexión, cargar un archivo JSON descargado previamente de NASA POWER
con el mismo formato. No se generan ni presentan valores sintéticos como observaciones.

API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
NASA POWER: https://power.larc.nasa.gov/
"""

from __future__ import annotations

import json
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = {
    "parameters": "T2M",  # temperatura a 2 metros
    "community": "AG",
    "longitude": -79.84,  # punto aproximado en Chiclayo, no toda la ciudad
    "latitude": -6.77,
    "start": "20240101",
    "end": "20240131",
    "format": "JSON",
    "time-standard": "UTC",
}

st.set_page_config(page_title="NASA POWER | Chiclayo", layout="wide")
st.title("De un dato NASA a una visualización verificable")
st.caption("Demo didáctica · NASA Space Apps 2026 · Chiclayo")
st.info("La serie corresponde a una estimación de grilla de NASA POWER para un punto. "
        "No es una medición tomada por una estación local ni un pronóstico.")


@st.cache_data(ttl=3600, show_spinner=False)
def descargar_power() -> dict:
    response = requests.get(API, params=PARAMS, timeout=25)
    response.raise_for_status()
    data = response.json()
    if "properties" not in data:
        raise ValueError("Respuesta inesperada: no hay properties")
    return data


def preparar_df(data: dict) -> tuple[pd.DataFrame, int]:
    parametros = data.get("properties", {}).get("parameter", {})
    serie = parametros.get("T2M")
    if not isinstance(serie, dict) or not serie:
        raise ValueError("T2M no está disponible en el JSON")
    filas = []
    descartados = 0
    for fecha, valor in serie.items():
        try:
            dt = datetime.strptime(str(fecha), "%Y%m%d")
            t = float(valor)
        except (TypeError, ValueError):
            descartados += 1
            continue
        # Los valores de relleno o de calidad incorrecta no son mediciones de cero.
        if pd.isna(t) or t <= -900:
            descartados += 1
            continue
        filas.append({"Fecha": dt, "T2M (°C)": t})
    if not filas:
        raise ValueError("La respuesta no contiene temperaturas válidas para graficar")
    df = pd.DataFrame(filas).sort_values("Fecha").drop_duplicates(subset=["Fecha"])
    return df, descartados


st.sidebar.header("Procedencia y contingencia")
subido = st.sidebar.file_uploader(
    "Opcional: cargar un JSON NASA POWER descargado previamente",
    type=["json"],
    help="Permite repetir la demo cuando la API no responde; el JSON debe ser de NASA POWER.",
)

try:
    if subido is not None:
        data = json.load(subido)
        origen = "Archivo NASA POWER cargado por el usuario (verificar fecha y procedencia)"
    else:
        with st.spinner("Consultando NASA POWER…"):
            data = descargar_power()
        origen = "Respuesta de NASA POWER consultada en vivo"
    df, descartados = preparar_df(data)
except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
    st.error(f"No fue posible preparar los datos: {exc}")
    st.warning("Verificá conectividad, parámetros o cargá un JSON NASA POWER auténtico guardado antes del evento.")
    st.stop()

st.subheader("Temperatura diaria a 2 metros (T2M)")
st.line_chart(df.set_index("Fecha")[["T2M (°C)"]])

col1, col2, col3 = st.columns(3)
col1.metric("Registros válidos", len(df))
col2.metric("Promedio del período", f"{df['T2M (°C)'].mean():.1f} °C")
col3.metric("Valores descartados", descartados)

with st.expander("Tabla y control de calidad"):
    st.dataframe(df, use_container_width=True)
    st.download_button("Descargar CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name="nasa_power_T2M_Chiclayo_202401.csv", mime="text/csv")

st.markdown("**Fuente:** [NASA POWER](https://power.larc.nasa.gov/) · "
            "[Documentación API diaria](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)")
st.caption(
    f"Origen: {origen} · Coordenadas solicitadas: {PARAMS['latitude']}, "
    f"{PARAMS['longitude']} · Período solicitado: 2024-01-01 a 2024-01-31 · Tiempo: UTC"
)
st.warning("Limitación: la temperatura de NASA POWER para un punto de grilla no prueba "
           "relaciones causales, no reemplaza mediciones locales y no constituye una predicción.")
