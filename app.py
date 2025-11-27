import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN (OBLIGATORIO AL INICIO) ---
st.set_page_config(
    page_title="Calculadora RRHH Pro",
    page_icon="💼",
    layout="centered"
)

# --- 2. GESTIÓN DE FONDO INTELIGENTE ---
def cargar_fondo_inteligente():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png', 'fondo.png.jpg']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    if img:
        ext = img.split('.')[-1]
        try:
            with open(img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <style>
                .stApp {{
                    background-image: url("data:image/{ext};base64,{b64}");
                    background-size: cover;
                    background-position: center;
                    background-attachment: fixed;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
        except:
            pass

# --- 3. ESTILOS VISUALES (CORREGIDO BOTÓN) ---
def cargar_estilos():
    st.markdown(
        """
        <style>
        .block-container {
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            margin-top: 1rem;
        }
        h1, h2, h3, p, label, .stMarkdown {
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
        }
        [data-testid="stMetricValue"] {
            color: #0056b3 !important;
            font-weight: 800;
        }
        
        /* --- CORRECCIÓN DEL BOTÓN --- */
        div.stButton > button {
            background-color: #0056b3;
            color: #ffffff !important; /* Texto BLANCO forzado */
            border-radius: 8px;
            font-weight: bold;
            border: none;
            width: 100%;
            padding: 0.8rem;
            font-size: 16px;
            text-shadow: 0px 1px 2px rgba(0,0,0,0.2); /* Sombra para legibilidad */
        }
        div.stButton > button:hover {
            background-color: #003366;
            color: #ffffff !important;
        }
        /* --------------------------- */

        #MainMenu, footer, header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_fondo_inteligente()
cargar_estilos()

# --- 4. FUNCIONES AUXILIARES ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return 38000.0, 67000.0

# --- 5. MOTOR DE CÁLCULO ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, sueldo_minimo, tope_uf_prev, tope_uf_afc):
    no_imp = col + mov
    liquido_tributable_meta = liquido_obj - no_imp
    
    if liquido_tributable_meta < sueldo_minimo * 0.5: return None

    TOPE_GRATIFICACION = (4.75 * sueldo_minimo) / 12
    TOPE_IMPONIBLE_PESOS = tope_uf_prev * uf
    TOPE_AFC_PESOS = tope_uf_afc * uf
    
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    tasa_afp = 0.10 + (TASAS_AFP.get(afp_nom, 0)/100)
    if afp_nom == "SIN AFP": tasa_afp = 0.0

    es_empresarial = (tipo_con == "Sueldo Empresarial")
    tasa_afc_trab = 0.006 if tipo_con == "Indefinido" else 0.0
    tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    TABLA_IMP = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (310,0.35,16.80), (99999,0.40,22.80)]

    min_base = 100000
    max_base = liquido_tributable_meta * 2.5
    resultado_optimo = None
    
    for _ in range(150):
        base_test = (min_base + max_base) / 2
        gratificacion = min(base_test * 0.25, TOPE_GRATIFICACION)
        if es_empresarial: gratificacion = 0

        total_imponible = base_test + gratificacion
        base_calc_prev = min(total_imponible, TOPE_IMPONIBLE_PESOS)
        base_calc_afc = min(total_imponible, TOPE_AFC_PESOS)

        m_afp = int(base_calc_prev * tasa_afp)
        m_afc = int(base_calc_afc * tasa_afc_trab)
        
        legal_7 = int(base_calc_prev * 0.07)
        m_salud = 0
        rebaja_tributaria_salud = 0
        
        if salud_tipo == "Fonasa (7%)":
            m_salud = legal_7
            rebaja_tributaria_salud = legal_7
        else:
            valor_plan = int(plan_uf * uf)
            m_salud = max(valor_plan, legal_7)
            rebaja_tributaria_salud = legal_7

        base_tributable = max(0, total_imponible - m_afp - rebaja_tributaria_salud - m_afc)
        
        impuesto = 0
        factor_utm = base_tributable / utm
        for lim, fac, reb in TABLA_IMP:
            if factor_utm <= lim:
                impuesto = (base_tributable * fac) - (reb * utm)
                break
        impuesto = int(max(0, impuesto))

        liquido_calc = total_imponible - m_afp - m_salud - m_afc - impuesto
        
        if abs(liquido_calc - liquido_tributable_meta) < 5:
            m_sis = int(base_calc_prev * 0.0149) if not es_empresarial else 0
            m_afc_e = int(base_calc_afc * tasa_afc_emp)
            m_mut = int(base_calc_prev * 0.0093) if not es_empresarial else 0
            total_aportes = m_sis + m_afc_e + m_mut
            costo_total = total_imponible + no_imp + total_aportes
            
            resultado_optimo = {
                "Sueldo Base": int(base_test),
                "Gratificación": int(gratificacion),
                "Total Imponible": int(total_imponible),
                "No Imponibles": int(no_imp),
                "TOTAL HABERES": int(total_imponible + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc, "Impuesto": impuesto,
                "Total Descuentos": m_afp + m_salud + m_afc + impuesto,
                "LÍQUIDO": int(liquido_calc + no_imp),
                "Aportes Empresa": total_aportes,
                "COSTO TOTAL": int(costo_total)
            }
            break
        elif liquido_calc < liquido_tributable_meta: min_base = base_test
        else: max_base = base_test
    return resultado_optimo

# --- 6. INTERFAZ GRÁFICA ---
st.title("Calculadora de Remuneraciones")

with st.sidebar:
    st.header("1. Indicadores")
    uf_live, utm_live = obtener_indicadores()
    st.metric("UF", fmt(uf_live).replace("$",""))
    st.metric("UTM", fmt(utm_live))
    st.divider()
    st.header("2. Parámetros Legales")
    st.caption("Validar con Previred.")
    sueldo_min_input = st.number_input("Sueldo Mínimo", value=500000, step=1000)
    tope_uf_prev_input = st.number_input("Tope Imp. UF (AFP)", value=84.3, step=0.1)
    tope_uf_afc_input = st.number_input("Tope Imp. UF (AFC)", value=126.6, step=0.1)

st.markdown("### Objetivo Económico")
col1, col2 = st.columns(2)
with col1:
    liq_target = st.number_input("Líquido a Pagar ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
with col2:
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

st.markdown("### Configuración")
c1, c2, c3 = st.columns(3)
with c1:
    tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
with c2:
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
with c3:
    salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan = 0.0
    if salud == "Isapre (UF)":
        plan = st.number_input("Plan UF", value=0.0, step=0.01)

st.divider()

# --- BOTÓN CORREGIDO ---
if st.button("CALCULAR (Validado Normativa)", type="primary"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Los haberes no imponibles son mayores al sueldo líquido.")
    else:
        res = calcular_reverso_exacto(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf_live, utm_live, sueldo_min_input, tope_uf_prev_input, tope_uf_afc_input)
        
        if res:
            st.success("Cálculo Exitoso")
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown("### Detalle Liquidación")
            df = pd.DataFrame([
                ["HABERES", ""],
                ["Sueldo Base", fmt(res['Sueldo Base'])],
                [f"Gratificación (Tope Legal)", fmt(res['Gratificación'])],
                ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                ["Colación y Movilización", fmt(res['No Imponibles'])],
                ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                ["", ""],
                ["DESCUENTOS", ""],
                [f"AFP ({afp})", fmt(-res['AFP'])],
                [f"Salud ({salud})", fmt(-res['Salud'])],
                ["Seguro Cesantía", fmt(-res['AFC'])],
                ["Impuesto Único", fmt(-res['Impuesto'])],
                ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                ["", ""],
                ["LÍQUIDO A PAGO", fmt(res['LÍQUIDO'])],
                ["", ""],
                ["COSTOS EMPRESA", ""],
                ["Aportes Patronales", fmt(res['Aportes Empresa'])],
                ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
            ], columns=["Concepto", "Monto"])
            st.table(df)
        else:
            st.error("No se pudo calcular. Verifique montos.")
