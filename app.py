import streamlit as st
import pandas as pd
import requests
import base64

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Calculadora de Remuneraciones",
    page_icon="💼",
    layout="centered"
)

# --- FUNCIÓN: CARGAR FONDO DESDE GITHUB ---
def set_bg_hack(main_bg):
    """
    Carga una imagen local como fondo de pantalla con estilos corporativos.
    """
    ext = main_bg.split('.')[-1]
    try:
        with open(main_bg, "rb") as f:
            data = f.read()
            bin_str = base64.b64encode(data).decode()
        st.markdown(
            f"""
            <style>
            /* Estilo para el fondo de pantalla completo */
            .stApp {{
                background-image: url("data:image/{ext};base64,{bin_str}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            /* Ocultar la barra superior por defecto de Streamlit */
            header[data-testid="stHeader"] {{
                background-color: transparent;
            }}
            /* Estilo para el contenedor principal (el recuadro blanco) */
            .block-container {{
                background-color: rgba(255, 255, 255, 0.92); /* Blanco semitransparente */
                padding: 2.5rem;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                margin-top: 4rem; /* Espacio para que se vea el logo arriba si lo hubiera */
            }}
            /* Colores corporativos (Azul de la marca) */
            h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
                color: #004a99 !important; /* Azul oscuro corporativo */
            }}
            /* Color para los valores de las métricas */
            [data-testid="stMetricValue"] {{
                color: #0056b3 !important;
                font-weight: 700;
            }}
            /* Estilo de los botones */
            div.stButton > button {{
                background-color: #0056b3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                font-weight: bold;
                transition: background-color 0.3s;
            }}
            div.stButton > button:hover {{
