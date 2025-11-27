import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Calculadora RRHH Pro",
    page_icon="🇨🇱",
    layout="wide" # Cambiado a wide para ver mejor los datos
)

# --- 2. ESTILOS VISUALES (CORRECCIÓN CONTRASTE BOTÓN) ---
def cargar_estilos():
    # Intentar cargar fondo si existe
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        ext = img.split('.')[-1]
        try:
            with open(img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            css_fondo = f"""
            .stApp {{
                background-image: url("data:image/{ext};base64,{b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
        except: pass
    else:
        css_fondo = ".stApp {background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}"

    st.markdown(
        f"""
        <style>
        {css_fondo}
        
        /* Contenedor Principal */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.97);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        /* Textos Azules Corporativos */
        h1, h2, h3, h4, p, label, .stMarkdown, .stSelectbox label, .stNumberInput label {{
            color: #004a99 !important;
            font-family: 'Arial', sans-serif;
        }}
        
        /* Métricas */
        [data-testid="stMetricValue"] {{
            color: #0056b3 !important;
            font-weight: 800;
        }}
        
        /* --- CORRECCIÓN BOTÓN (LETRAS BLANCAS) --- */
        div.stButton > button {{
            background-color: #0056b3 !important;
            color: #ffffff !important; /* BLANCO PURO */
            font-size: 18px !important;
            font-weight: bold !important;
            border: none;
            padding: 0.8rem 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            color: #ffffff !important;
            transform: scale(1.02);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        div.stButton > button:active {{
            color: #ffffff !important;
        }}
        /* ----------------------------------------- */
        
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES DE FORMATO ---
def fmt(valor):
    """Agrega puntos de miles y signo peso: $1.000.000"""
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return 38000.0, 67000.0

# --- 4. BARRA LATERAL (PANEL PREVIRED COMPLETO) ---
with st.sidebar:
    st.title("⚙️ Panel Previred")
    
    # A. Indicadores Económicos
    st.subheader("1. Indicadores al Día")
    uf_live, utm_live = obtener_indicadores()
    c1, c2 = st.columns(2)
    c1.metric("UF", fmt(uf_live).replace("$",""))
    c2.metric("UTM", fmt(utm_live))
    
    st.divider()
    
    # B. Parámetros Legales (Editables)
    st.subheader("2. Límites Legales (Topes)")
    st.caption("Valores por defecto según normativa vigente.")
    
    sueldo_min = st.number_input("Sueldo Mínimo ($)", value=500000, step=1000)
    
    # Cálculo visual del tope gratificación
    tope_grat_anual = 4.75 * sueldo_min
    tope_grat_mensual = tope_grat_anual / 12
    st.info(f"Tope Gratificación (4.75 IMM): {fmt(tope_grat_mensual)}")
    
    tope_imponible_uf = st.number_input("Tope Imponible AFP/Salud (UF)", value=84.3, step=0.1)
    tope_seguro_uf = st.number_input("Tope Seguro Cesantía (UF)", value=126.6, step=0.1)
    
    st.divider()
    
    # C. Tasas Empleador
    st.subheader("3. Tasas Costo Empresa")
    tasa_sis_input = st.number_input("SIS (%)", value=1.49, step=0.01)
    tasa_mutual_input = st.number_input("Mutual Base (%)", value=0.93, step=0.01)

# --- 5. MOTOR DE CÁLCULO (USANDO VARIABLES DEL SIDEBAR) ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, 
                          s_min, t_imp_uf, t_sc_uf, t_sis, t_mut):
    
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    
    if liq_trib_meta < s_min * 0.4: return None

    # Topes en Pesos
    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    # Tasas
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    
    # AFP
    if es_emp:
        tasa_afp = 0.0
    else:
        tasa_afp = 0.10 + (TASAS_AFP.get(afp_nom, 0)/100)
        if afp_nom == "SIN AFP": tasa_afp = 0.0

    # AFC
    # Indef: Trab 0.6 / Emp 2.4
    # Plazo: Trab 0.0 / Emp 3.0
    tasa_afc_trab = 0.0
    tasa_afc_emp = 0.0
    
    if not es_emp:
        if tipo_con == "Indefinido":
            tasa_afc_trab = 0.006
            tasa_afc_emp = 0.024
        elif tipo_con == "Plazo Fijo":
            tasa_afc_trab = 0.0
            tasa_afc_emp = 0.030
    else:
        # Empresarial: Trab 0 / Emp 2.4 (Para efectos de costo empresa simulación)
        tasa_afc_trab = 0.0
        tasa_afc_emp = 0.024 

    # SIS y Mutual (Del Sidebar)
    pct_sis = t_sis / 100
    pct_mut = t_mut / 100

    TABLA_IMP = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (310,0.35,16.80), (99999,0.40,22.80)]

    # Búsqueda
    min_b, max_b = 100000, liq_trib_meta * 2.5
    
    for _ in range(150):
        base_test = (min_b + max_b) / 2
        
        # Gratificación
        grat = min(base_test * 0.25, TOPE_GRAT)
        # Opcional: if es_emp: grat = 0
        
        tot_imp = base_test + grat
        
        # Bases Topadas
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        # Descuentos
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        legal_7 = int(b_prev * 0.07)
        m_salud = 0
        rebaja_trib = 0
        
        if salud_tipo == "Fonasa (7%)":
            m_salud = legal_7
            rebaja_trib = legal_7
        else:
            val_plan = int(plan_uf * uf)
            m_salud = max(val_plan, legal_7)
            rebaja_trib = legal_7 # Tope legal tributario

        # Impuesto
        base_trib = max(0, tot_imp - m_afp - rebaja_trib - m_afc)
        imp = 0
        f_utm = base_trib / utm
        for l, f, r in TABLA_IMP:
            if f_utm <= l:
                imp = (base_trib * f) - (r * utm)
                break
        imp = int(max(0, imp))
        
        liq_calc = tot_imp - m_afp - m_salud - m_afc - imp
        
        if abs(liq_calc - liq_trib_meta) < 5:
            # Costos Empresa
            m_sis = int(b_prev * pct_sis)
            m_afc_e = int(b_afc * tasa_afc_emp)
            m_mut = int(b_prev * pct_mut)
            
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            
            return {
                "Sueldo Base": int(base_test),
                "Gratificación": int(grat),
                "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp),
                "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_salud + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp),
                "Aportes Empresa": aportes,
                "COSTO TOTAL": int(costo_fin)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base_test
        else: max_b = base_test
    return None

# --- 6. INTERFAZ PRINCIPAL ---
st.title("Calculadora de Remuneraciones")

# Columnas de Entrada
c1, c2 = st.columns(2)

with c1:
    st.subheader("1. Objetivo Líquido")
    # Inputs sin puntos visuales al escribir (limitación web), pero formato final con puntos
    liq_target = st.number_input("Sueldo Líquido ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

with c2:
    st.subheader("2. Configuración")
    tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
    
    col_a, col_b = st.columns(2)
    with col_a:
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
    with col_b:
        salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    
    plan = 0.0
    if salud == "Isapre (UF)":
        plan = st.number_input("Valor Plan (UF)", value=0.0, step=0.01)

st.markdown("---")

# BOTÓN DE CÁLCULO
if st.button("CALCULAR (Validado Normativa)"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Haberes no imponibles superan al líquido.")
    else:
        res = calcular_reverso_exacto(
            liq_target, colacion, movilizacion, tipo, afp, salud, plan, 
            uf_live, utm_live, 
            sueldo_min, tope_imponible_uf, tope_seguro_uf, tasa_sis_input, tasa_mutual_input
        )
        
        if res:
            st.success("✅ Cálculo Generado Correctamente")
            
            # Tarjetas Métricas
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown("### 📋 Desglose Oficial")
            
            # TABLA DE RESULTADOS (FORMATO DE MILES FORZADO)
            df = pd.DataFrame([
                ["HABERES", ""],
                ["Sueldo Base", fmt(res['Sueldo Base'])],
                ["Gratificación Legal", fmt(res['Gratificación'])],
                ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                ["Asig. No Imponibles", fmt(res['No Imponibles'])],
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
                ["SIS + Mutual + AFC Empleador", fmt(res['Aportes Empresa'])],
                ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
            ], columns=["Concepto", "Monto"])
            
            # Usar st.table asegura que el formato de texto no se pierda
            st.table(df)
            
        else:
            st.error("No se encontró solución matemática viable.")
