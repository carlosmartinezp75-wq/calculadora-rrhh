import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Calculadora Remuneraciones Pro",
    page_icon="🇨🇱",
    layout="centered"
)

# --- 2. GESTIÓN DE FONDO ---
def cargar_fondo_inteligente():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png', 'fondo.png.jpg']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    if img:
        ext = img.split('.')[-1]
        with open(img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""<style>.stApp {{background-image: url("data:image/{ext};base64,{b64}"); background-size: cover; background-attachment: fixed;}}</style>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown("""<style>.stApp {background: linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%);}</style>""", unsafe_allow_html=True)

# --- 3. ESTILOS ---
def cargar_estilos():
    st.markdown(
        """
        <style>
        .block-container {background-color: rgba(255, 255, 255, 0.95); padding: 2rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); margin-top: 1rem;}
        h1, h2, h3, p, label, .stMarkdown {color: #004a99 !important; font-family: 'Segoe UI', sans-serif;}
        [data-testid="stMetricValue"] {color: #0056b3 !important; font-weight: 800;}
        div.stButton > button {background-color: #0056b3; color: white; width: 100%; border-radius: 8px; font-weight: bold; border: none;}
        div.stButton > button:hover {background-color: #003366;}
        #MainMenu, footer, header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_fondo_inteligente()
cargar_estilos()

# --- 4. DATA Y VARIABLES GLOBALES ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return 38400.0, 67000.0 # Fallback 2025

# --- 5. MOTOR DE CÁLCULO ESTRICTO (PREVIRED) ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, sueldo_minimo, tope_uf_prev, tope_uf_afc):
    
    # Objetivo: Encontrar el SUELDO BASE que genere el líquido.
    # Restamos no imponibles porque no entran en la matemática tributaria
    no_imp = col + mov
    liquido_tributable_meta = liquido_obj - no_imp
    
    if liquido_tributable_meta < sueldo_minimo * 0.7: # Validación básica
        return None

    # --- CONSTANTES LEGALES ---
    TOPE_GRATIFICACION = (4.75 * sueldo_minimo) / 12
    TOPE_IMPONIBLE_PESOS = tope_uf_prev * uf
    TOPE_AFC_PESOS = tope_uf_afc * uf
    
    # Tasas AFP
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    tasa_afp = 0.10 + (TASAS_AFP.get(afp_nom, 0)/100)
    if afp_nom == "SIN AFP": tasa_afp = 0.0

    # Tasas Seguro Cesantía
    # Indefinido: Trab 0.6% / Emp 2.4%
    # Plazo Fijo: Trab 0% / Emp 3.0%
    # Empresarial: 0 / 0
    es_empresarial = (tipo_con == "Sueldo Empresarial")
    tasa_afc_trab = 0.006 if tipo_con == "Indefinido" else 0.0
    tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    # Tabla Impuesto (Factores Mensuales)
    TABLA_IMP = [
        (13.5, 0, 0), (30, 0.04, 0.54), (50, 0.08, 1.08),
        (70, 0.135, 2.73), (90, 0.23, 7.48), (120, 0.304, 12.66), (310, 0.35, 16.80), (99999, 0.40, 22.80)
    ]

    # --- BÚSQUEDA BINARIA SOBRE EL SUELDO BASE ---
    # Iteramos sobre el Sueldo Base, no el Bruto, para calcular bien la Gratificación.
    min_base = 100000
    max_base = liquido_tributable_meta * 2.0
    
    resultado_optimo = None
    
    for _ in range(150): # Más iteraciones para precisión
        base_test = (min_base + max_base) / 2
        
        # 1. Calcular Gratificación Legal
        gratificacion = min(base_test * 0.25, TOPE_GRATIFICACION)
        if es_empresarial: gratificacion = 0 # Empresarial suele ser sueldo plano, pero configurable

        # 2. Total Imponible
        total_imponible = base_test + gratificacion
        
        # 3. Topes Legales
        base_calc_prev = min(total_imponible, TOPE_IMPONIBLE_PESOS)
        base_calc_afc = min(total_imponible, TOPE_AFC_PESOS)

        # 4. Descuentos
        m_afp = int(base_calc_prev * tasa_afp)
        m_afc = int(base_calc_afc * tasa_afc_trab)
        
        # Salud (7% obligatorio o Plan)
        legal_7 = int(base_calc_prev * 0.07)
        if salud_tipo == "Fonasa (7%)":
            m_salud = legal_7
        else: # Isapre
            valor_plan = int(plan_uf * uf)
            m_salud = max(valor_plan, legal_7)
            # Para tributario, el tope de rebaja es el menor entre (Plan, 7% Legal, o Tope UF)
            # Simplificación estándar: Rebaja tributaria tope legal 7% (Criterio SII común)
            rebaja_tributaria_salud = legal_7 

        # 5. Base Tributable
        # Bruto - (AFP + Salud Legal + AFC)
        base_tributable = max(0, total_imponible - m_afp - rebaja_tributaria_salud - m_afc)
        
        # 6. Impuesto Único
        impuesto = 0
        factor_utm = base_tributable / utm
        for lim, fac, reb in TABLA_IMP:
            if factor_utm <= lim:
                impuesto = (base_tributable * fac) - (reb * utm)
                break
        impuesto = int(max(0, impuesto))

        # 7. Líquido Calculado
        liquido_calc = total_imponible - m_afp - m_salud - m_afc - impuesto
        
        # Ajuste de Búsqueda
        diff = liquido_calc - liquido_tributable_meta
        if abs(diff) < 2: # Precisión de $2 pesos
            # CALCULAR COSTOS EMPRESA
            m_sis = int(base_calc_prev * 0.0149) if not es_empresarial else 0
            m_afc_e = int(base_calc_afc * tasa_afc_emp)
            m_mut = int(base_calc_prev * 0.0093) if not es_empresarial else 0 # 0.93% Base
            
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
        elif liquido_calc < liquido_tributable_meta:
            min_base = base_test
        else:
            max_base = base_test
            
    return resultado_optimo

# --- 6. INTERFAZ GRÁFICA ---
st.title("Calculadora de Remuneraciones")

# --- SIDEBAR DE VALIDACIÓN (CRÍTICO PARA USUARIO) ---
with st.sidebar:
    st.header("1. Indicadores (Mindicador.cl)")
    uf_live, utm_live = obtener_indicadores()
    st.metric("UF", fmt(uf_live).replace("$",""))
    st.metric("UTM", fmt(utm_live))
    
    st.divider()
    
    st.header("2. Parámetros Legales")
    st.info("Valide estos montos con Previred.com si cambian.")
    
    # INPUTS EDITABLES POR EL USUARIO (Para que no falle si cambia la ley)
    sueldo_min_input = st.number_input("Sueldo Mínimo", value=500000, step=1000, format="%d")
    tope_uf_prev_input = st.number_input("Tope Imp. AFP/Salud (UF)", value=84.3, step=0.1)
    tope_uf_afc_input = st.number_input("Tope Imp. AFC (UF)", value=126.6, step=0.1)
    
    tope_grat_calc = fmt((4.75 * sueldo_min_input)/12)
    st.caption(f"Tope Gratificación calc: {tope_grat_calc}")

# --- FORMULARIO PRINCIPAL ---
st.markdown("### Objetivo del Trabajador")
col1, col2 = st.columns(2)
with col1:
    liq_target = st.number_input("Líquido a Pagar ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
with col2:
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

st.markdown("### Configuración Contractual")
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

st.markdown("---")

if st.button("CALCULAR (Validado Normativa)", type="primary"):
    # Validaciones lógicas
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Los haberes no imponibles son mayores al sueldo líquido.")
    else:
        # Llamamos al motor con los parámetros del Sidebar
        res = calcular_reverso_exacto(
            liq_target, colacion, movilizacion, tipo, afp, salud, plan, 
            uf_live, utm_live, 
            sueldo_min_input, tope_uf_prev_input, tope_uf_afc_input
        )
        
        if res:
            st.success("Cálculo Cuadrado Exitosamente")
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Gratificación 25%", fmt(res['Gratificación']))
            k3.metric("Total Imponible", fmt(res['Total Imponible']))
            
            st.markdown("---")
            
            # TABLA DETALLADA TIPO LIQUIDACIÓN
            df = pd.DataFrame([
                ["HABERES", ""],
                ["Sueldo Base", fmt(res['Sueldo Base'])],
                [f"Gratificación (Tope: {tope_grat_calc})", fmt(res['Gratificación'])],
                ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                ["Colación y Movilización", fmt(res['No Imponibles'])],
                ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                ["", ""],
                ["DESCUENTOS LEGALES", ""],
                [f"AFP ({afp})", fmt(-res['AFP'])],
                [f"Salud ({salud})", fmt(-res['Salud'])],
                ["Seguro Cesantía", fmt(-res['AFC'])],
                ["Impuesto Único", fmt(-res['Impuesto'])],
                ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                ["", ""],
                ["LÍQUIDO A PAGO", fmt(res['LÍQUIDO'])],
                ["", ""],
                ["COSTOS EMPRESA", ""],
                ["SIS + AFC Empleador + Mutual", fmt(res['Aportes Empresa'])],
                ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
            ], columns=["Concepto", "Monto"])
            
            st.table(df)
        else:
            st.error("No se pudo calcular. Es posible que el líquido sea muy bajo para el sueldo mínimo legal.")
