import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Calculadora RRHH Pro",
    page_icon="⚖️",
    layout="centered"
)

# --- 2. FONDO Y ESTILOS ---
def cargar_recursos_visuales():
    # 1. Fondo Inteligente
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    if img:
        ext = img.split('.')[-1]
        try:
            with open(img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""<style>.stApp {{background-image: url("data:image/{ext};base64,{b64}"); background-size: cover; background-position: center; background-attachment: fixed;}}</style>""",
                unsafe_allow_html=True
            )
        except: pass

    # 2. CSS Corporativo (Letras Azules y Botón Blanco)
    st.markdown(
        """
        <style>
        .block-container {background-color: rgba(255, 255, 255, 0.96); padding: 2.5rem; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); margin-top: 1rem;}
        h1, h2, h3, p, label, .stMarkdown, .stNumberInput label, .stSelectbox label {color: #004a99 !important; font-family: 'Segoe UI', sans-serif;}
        [data-testid="stMetricValue"] {color: #0056b3 !important; font-weight: 800;}
        
        /* Botón con texto blanco forzado y sombra */
        div.stButton > button {
            background-color: #0056b3 !important;
            color: white !important;
            font-weight: bold;
            border: none;
            width: 100%;
            padding: 0.8rem;
            font-size: 16px;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        div.stButton > button:hover {
            background-color: #003366 !important;
            color: white !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_recursos_visuales()

# --- 3. FUNCIONES AUXILIARES ---
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

# --- 4. MOTOR DE CÁLCULO CIENTÍFICO ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, sueldo_minimo, tope_uf_prev, tope_uf_afc):
    
    # Objetivo: Buscar el Bruto
    no_imp = col + mov
    liquido_tributable_meta = liquido_obj - no_imp
    
    if liquido_tributable_meta < sueldo_minimo * 0.4: return None

    # --- CONSTANTES DE LEY ---
    # Tope Gratificación: 4.75 IMM anuales prorrateados
    TOPE_GRATIFICACION_MENSUAL = (4.75 * sueldo_minimo) / 12
    
    # Topes Imponibles (UF a Pesos)
    TOPE_IMPONIBLE_PESOS = tope_uf_prev * uf
    TOPE_AFC_PESOS = tope_uf_afc * uf
    
    # Tasas
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    
    es_empresarial = (tipo_con == "Sueldo Empresarial")
    
    # Configuración AFP (Trabajador)
    if es_empresarial:
        tasa_afp = 0.0 # Empresarial no paga AFP (Liquidez)
    else:
        tasa_afp = 0.10 + (TASAS_AFP.get(afp_nom, 0)/100)
        if afp_nom == "SIN AFP": tasa_afp = 0.0

    # Configuración AFC (Seguro Cesantía)
    tasa_afc_trab = 0.006 if tipo_con == "Indefinido" and not es_empresarial else 0.0
    
    # Costos Empresa (Tasas)
    tasa_sis = 0.0149 # SIS siempre paga empresa (salvo excepciones muy raras, asumimos SI para costo real)
    tasa_mutual = 0.0093 # Tasa base
    
    if tipo_con == "Indefinido": tasa_afc_emp = 0.024
    elif tipo_con == "Plazo Fijo": tasa_afc_emp = 0.030
    else: tasa_afc_emp = 0.024 # Asumimos que para costo empresa empresarial se reserva el 2.4% o similar.

    # Tabla Impuesto
    TABLA_IMP = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (310,0.35,16.80), (99999,0.40,22.80)]

    # --- ALGORITMO DE BÚSQUEDA ---
    min_base = 100000
    max_base = liquido_tributable_meta * 2.5
    optimo = None
    
    for _ in range(150):
        base_test = (min_base + max_base) / 2
        
        # 1. CÁLCULO GRATIFICACIÓN (CON TOPE ESTRICTO)
        grat_teorica = base_test * 0.25
        gratificacion = min(grat_teorica, TOPE_GRATIFICACION_MENSUAL)
        
        # 2. TOTAL IMPONIBLE
        total_imponible = base_test + gratificacion
        
        # 3. TOPES DE DESCUENTO
        base_prev = min(total_imponible, TOPE_IMPONIBLE_PESOS)
        base_afc = min(total_imponible, TOPE_AFC_PESOS)

        # 4. DESCUENTOS TRABAJADOR
        m_afp = int(base_prev * tasa_afp)
        m_afc = int(base_afc * tasa_afc_trab)
        
        legal_7 = int(base_prev * 0.07)
        m_salud = 0
        rebaja_impuesto = 0
        
        if salud_tipo == "Fonasa (7%)":
            m_salud = legal_7
            rebaja_impuesto = legal_7
        else: # Isapre
            valor_plan = int(plan_uf * uf)
            m_salud = max(valor_plan, legal_7)
            rebaja_impuesto = legal_7 # Tope legal tributario

        # 5. IMPUESTO ÚNICO
        base_tributable = max(0, total_imponible - m_afp - rebaja_impuesto - m_afc)
        
        impuesto = 0
        factor_utm = base_tributable / utm
        for lim, fac, reb in TABLA_IMP:
            if factor_utm <= lim:
                impuesto = (base_tributable * fac) - (reb * utm)
                break
        impuesto = int(max(0, impuesto))

        # 6. LÍQUIDO FINAL
        liquido_calc = total_imponible - m_afp - m_salud - m_afc - impuesto
        
        diff = liquido_calc - liquido_tributable_meta
        
        if abs(diff) < 5:
            # Encontrado! Calculamos Costos Empresa
            m_sis = int(base_prev * tasa_sis)
            m_afc_e = int(base_afc * tasa_afc_emp)
            m_mut = int(base_prev * tasa_mutual)
            
            total_aportes = m_sis + m_afc_e + m_mut
            costo_total = total_imponible + no_imp + total_aportes
            
            optimo = {
                "Sueldo Base": int(base_test),
                "Gratificación": int(gratificacion),
                "Tope Grat": int(TOPE_GRATIFICACION_MENSUAL),
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
    return optimo

# --- 5. INTERFAZ GRÁFICA ---
st.title("Calculadora de Remuneraciones")

with st.sidebar:
    st.header("1. Indicadores (Hoy)")
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))
    st.divider()
    st.header("2. Parámetros Legales")
    st.caption("Ajuste estos valores si cambia la ley.")
    
    sueldo_min = st.number_input("Sueldo Mínimo ($)", value=500000, step=1000)
    
    # Cálculo visual del tope
    tope_visual = (4.75 * sueldo_min) / 12
    st.info(f"Tope Gratificación Vigente: {fmt(tope_visual)}")
    
    tope_prev = st.number_input("Tope UF (AFP/Salud)", value=84.3, step=0.1)
    tope_afc = st.number_input("Tope UF (AFC)", value=126.6, step=0.1)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Objetivo Líquido")
    liq_target = st.number_input("Sueldo a Pagar ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
with col2:
    st.subheader("Configuración")
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")
    tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])

c1, c2, c3 = st.columns(3)
with c1:
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
with c2:
    salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
with c3:
    plan = 0.0
    if salud == "Isapre (UF)":
        plan = st.number_input("Plan UF", value=0.0, step=0.01)

st.divider()

if st.button("CALCULAR (Validado Normativa)"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Los haberes no imponibles superan al líquido.")
    else:
        res = calcular_reverso_exacto(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf_v, utm_v, sueldo_min, tope_prev, tope_afc)
        
        if res:
            st.success("Cálculo Cuadrado Exitosamente")
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.subheader("Detalle Liquidación")
            
            # Etiqueta dinámica para la gratificación
            lbl_grat = f"Gratificación (Tope: {fmt(res['Tope Grat'])})" if res['Gratificación'] == res['Tope Grat'] else "Gratificación (25%)"
            
            df = pd.DataFrame([
                ["HABERES", ""],
                ["Sueldo Base", fmt(res['Sueldo Base'])],
                [lbl_grat, fmt(res['Gratificación'])],
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
                ["COSTOS EMPRESA (Ocultos al trabajador)", ""],
                ["SIS + Mutual + AFC Empleador", fmt(res['Aportes Empresa'])],
                ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
            ], columns=["Concepto", "Monto"])
            st.table(df)
        else:
            st.error("No se pudo calcular. Verifique los montos.")
