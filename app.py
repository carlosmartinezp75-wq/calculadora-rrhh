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

# --- 1. FUNCIÓN DE FONDO (Corregida) ---
def set_bg_hack(main_bg):
    """
    Carga la imagen de fondo de forma segura.
    """
    ext = main_bg.split('.')[-1]
    try:
        with open(main_bg, "rb") as f:
            data = f.read()
            bin_str = base64.b64encode(data).decode()
        
        # Inyectamos SOLO el fondo (Usamos dobles llaves {{ }} para escapar el CSS)
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/{ext};base64,{bin_str}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        pass # Si no hay imagen, no hace nada (se queda blanco)

# --- 2. ESTILOS VISUALES (Separados para evitar error de sintaxis) ---
def cargar_estilos():
    st.markdown(
        """
        <style>
        /* Ocultar barra superior */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }
        /* Contenedor blanco semitransparente */
        .block-container {
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            margin-top: 2rem;
        }
        /* Colores Corporativos */
        h1, h2, h3, p, label, .stMarkdown {
            color: #004a99 !important;
        }
        [data-testid="stMetricValue"] {
            color: #0056b3 !important;
            font-weight: bold;
        }
        /* Botones */
        div.stButton > button {
            background-color: #0056b3;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: bold;
        }
        div.stButton > button:hover {
            background-color: #003d80;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- EJECUCIÓN DE ESTILOS ---
# 1. Cargar fondo (Asegúrate de tener 'fondo_marca.png' en GitHub)
set_bg_hack('fondo_marca.png')
# 2. Cargar estilos visuales
cargar_estilos()

# --- FUNCIÓN FORMATO CHILENO ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

# --- DATOS EN VIVO ---
def obtener_indicadores():
    try:
        response = requests.get('https://mindicador.cl/api', timeout=3)
        data = response.json()
        return data['uf']['valor'], data['utm']['valor']
    except:
        return 38000.0, 67000.0

# --- MOTOR DE CÁLCULO ---
def calcular_simulacion_completa(liquido_total_objetivo, colacion, movilizacion, tipo_contrato, nombre_afp, salud_tipo, plan_uf, uf_dia, utm_dia):
    
    no_imponibles = colacion + movilizacion
    liquido_a_buscar = liquido_total_objetivo - no_imponibles
    
    if liquido_a_buscar < 0: return None

    # Parámetros
    TASAS_AFP = {
        "Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58,
        "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP (Empresarial)": 0.0
    }
    tasa_afp_base = 0.10 if nombre_afp != "SIN AFP (Empresarial)" else 0.0
    comision_afp = TASAS_AFP.get(nombre_afp, 0) / 100
    tasa_afp_total = tasa_afp_base + comision_afp
    
    es_empresarial = (tipo_contrato == "Sueldo Empresarial")
    tasa_afc_trab = 0.006 if tipo_contrato == "Contrato Indefinido" else 0.0
    tasa_afc_emp = 0.024 if tipo_contrato == "Contrato Indefinido" else (0.03 if tipo_contrato == "Contrato Plazo Fijo" else 0.0)
    
    tope_pesos_afp = 84.3 * uf_dia
    tope_pesos_sc = 126.6 * uf_dia

    min_bruto = liquido_a_buscar
    max_bruto = liquido_a_buscar * 2.2
    bruto_encontrado = 0
    
    TABLA_IMPUESTO = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (310,0.35,16.80), (99999,0.40,22.80)]

    for _ in range(100):
        bruto_test = (min_bruto + max_bruto) / 2
        
        base_afp = min(bruto_test, tope_pesos_afp)
        base_sc = min(bruto_test, tope_pesos_sc)
        
        monto_afp = int(base_afp * tasa_afp_total)
        monto_afc_trab = int(base_sc * tasa_afc_trab)
