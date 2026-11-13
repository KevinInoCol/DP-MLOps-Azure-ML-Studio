"""
Interfaz Streamlit para consumir el online endpoint del modelo VotingEnsemble.

No reimplementa la llamada HTTP: importa `invocar()` de
`consumir_realtime_endpoint.py`, que ya construye los headers (incluido
`azureml-model-deployment`) y mide la latencia. Esta capa solo arma el payload
desde el formulario o desde un CSV y presenta el resultado.

El modelo predice `charges` (costo anual del plan de salud) a partir de
age, sex, bmi, children, smoker y region.

Ejecutar:
    streamlit run app_streamlit.py
"""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from consumir_realtime_endpoint import invocar

load_dotenv()

ONLINE_ENDPOINT_URL = os.getenv("ONLINE_ENDPOINT_URL")
ONLINE_ENDPOINT_KEY = os.getenv("ONLINE_ENDPOINT_KEY")
ONLINE_DEPLOYMENT_NAME = os.getenv("ONLINE_DEPLOYMENT_NAME")

ARCHIVO_EJEMPLO = Path(__file__).parent / "datos" / "datos_entrada.csv"

COLUMNAS_MODELO = ["age", "sex", "bmi", "children", "smoker", "region"]

# Dominios tomados de insurance.csv (el dataset de entrenamiento, n=1338).
# Salir de estos rangos es extrapolacion: el modelo no vio esos casos.
OPCIONES_SEXO = ["female", "male"]
OPCIONES_FUMADOR = ["no", "yes"]
OPCIONES_REGION = ["northeast", "northwest", "southeast", "southwest"]
RANGO_EDAD = (18, 64)
RANGO_BMI = (15.96, 53.13)
MAX_HIJOS = 5


def verificar_configuracion() -> list[str]:
    """Devuelve la lista de variables de entorno obligatorias que faltan."""
    faltantes = []
    if not ONLINE_ENDPOINT_URL:
        faltantes.append("ONLINE_ENDPOINT_URL")
    if not ONLINE_ENDPOINT_KEY:
        faltantes.append("ONLINE_ENDPOINT_KEY")
    return faltantes


def construir_payload(df: pd.DataFrame) -> dict:
    """Convierte un DataFrame al formato que espera el scoring script de AutoML."""
    return {
        "input_data": {
            "columns": df.columns.tolist(),
            "index": df.index.tolist(),
            "data": df.values.tolist(),
        }
    }


def extraer_predicciones(resultado) -> list:
    """
    Normaliza la respuesta del endpoint a una lista de numeros.

    AutoML devuelve una lista plana, pero segun la version del scoring script
    puede venir envuelta en {"predictions": [...]} o {"result": [...]}.
    """
    if isinstance(resultado, list):
        return resultado
    if isinstance(resultado, dict):
        for clave in ("predictions", "result", "forecast"):
            if clave in resultado:
                return resultado[clave]
    raise ValueError(f"Formato de respuesta no reconocido: {type(resultado)}")


def predecir(df: pd.DataFrame) -> list:
    """Envia el DataFrame al endpoint y devuelve las predicciones."""
    resultado = invocar(construir_payload(df[COLUMNAS_MODELO]))
    return extraer_predicciones(resultado)


st.set_page_config(page_title="Plan de Salud - VotingEnsemble", page_icon="🏥")

st.title("🏥 Estimador de costo de plan de salud")
st.caption(
    "Modelo VotingEnsemble entrenado con Azure AutoML, servido en un "
    "managed online endpoint."
)

faltantes = verificar_configuracion()
if faltantes:
    st.error(
        "Falta configurar en el archivo `.env`: " + ", ".join(f"`{v}`" for v in faltantes)
    )
    st.stop()

with st.sidebar:
    st.subheader("Endpoint")
    st.text_input("Scoring URI", ONLINE_ENDPOINT_URL, disabled=True)
    st.text_input("Deployment", ONLINE_DEPLOYMENT_NAME or "(default)", disabled=True)
    st.success("Key cargada desde .env")
    st.divider()
    st.caption(
        f"Rangos del entrenamiento: edad {RANGO_EDAD[0]}-{RANGO_EDAD[1]}, "
        f"BMI {RANGO_BMI[0]}-{RANGO_BMI[1]}, hijos 0-{MAX_HIJOS}."
    )

tab_individual, tab_lote = st.tabs(["Una persona", "Lote (CSV)"])

with tab_individual:
    with st.form("formulario_individual"):
        col_izq, col_der = st.columns(2)
        with col_izq:
            edad = st.slider("Edad", RANGO_EDAD[0], RANGO_EDAD[1], 35)
            bmi = st.slider("BMI", RANGO_BMI[0], RANGO_BMI[1], 28.0, step=0.1)
            hijos = st.selectbox("Hijos a cargo", list(range(MAX_HIJOS + 1)))
        with col_der:
            sexo = st.selectbox("Sexo", OPCIONES_SEXO)
            fumador = st.selectbox("Fumador", OPCIONES_FUMADOR)
            region = st.selectbox("Region", OPCIONES_REGION)
        enviado = st.form_submit_button("Estimar costo", type="primary")

    if enviado:
        df_entrada = pd.DataFrame(
            [
                {
                    "age": edad,
                    "sex": sexo,
                    "bmi": bmi,
                    "children": hijos,
                    "smoker": fumador,
                    "region": region,
                }
            ]
        )
        try:
            with st.spinner("Consultando el endpoint..."):
                predicciones = predecir(df_entrada)
        except Exception as error:
            st.error(f"Fallo la llamada al endpoint: {error}")
        else:
            st.metric("Costo anual estimado", f"$ {predicciones[0]:,.2f}")
            if fumador == "yes":
                st.info(
                    "`smoker` es el predictor mas fuerte del dataset: cambialo a "
                    "`no` y compara el resultado."
                )
            with st.expander("Payload enviado"):
                st.json(construir_payload(df_entrada))

with tab_lote:
    st.write(
        "Sube un CSV con las columnas "
        f"`{'`, `'.join(COLUMNAS_MODELO)}` o usa el archivo de ejemplo."
    )
    archivo = st.file_uploader("CSV", type="csv")

    usar_ejemplo = False
    if archivo is None and ARCHIVO_EJEMPLO.exists():
        usar_ejemplo = st.checkbox(f"Usar `datos/{ARCHIVO_EJEMPLO.name}`")

    df_lote = None
    if archivo is not None:
        df_lote = pd.read_csv(archivo)
    elif usar_ejemplo:
        df_lote = pd.read_csv(ARCHIVO_EJEMPLO)

    if df_lote is not None:
        ausentes = [c for c in COLUMNAS_MODELO if c not in df_lote.columns]
        if ausentes:
            st.error(f"Al CSV le faltan columnas: {', '.join(ausentes)}")
        else:
            st.dataframe(df_lote, width="stretch")
            if st.button(f"Estimar {len(df_lote)} filas", type="primary"):
                try:
                    with st.spinner("Consultando el endpoint..."):
                        predicciones = predecir(df_lote)
                except Exception as error:
                    st.error(f"Fallo la llamada al endpoint: {error}")
                else:
                    df_salida = df_lote.copy()
                    df_salida["charges_estimado"] = predicciones
                    st.dataframe(df_salida, width="stretch")
                    st.metric(
                        "Promedio estimado",
                        f"$ {df_salida['charges_estimado'].mean():,.2f}",
                    )
                    st.download_button(
                        "Descargar resultados",
                        df_salida.to_csv(index=False).encode("utf-8"),
                        "predicciones.csv",
                        "text/csv",
                    )
