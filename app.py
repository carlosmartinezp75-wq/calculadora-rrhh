import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.express as px  # Librería para gráficos profesionales

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Calculadora Remuneraciones Pro",
    page_icon="📊",
    layout="wide"
)

# --- 2. ESTILOS VISUALES (CSS BLINDADO) ---
def cargar_estilos():
    # Carga de Fondo Inteligente
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png', 'fondo.png.jpg']
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
        # Fondo degradado elegante si falla la imagen
        css_fondo = ".stApp {background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}"

    st.markdown(
        f"""
        <style>
        {css_fondo}
        
        /* Contenedores */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.96);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        
        /* Tipografía */
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }}
        p, label, .stSelectbox label, .stNumberInput label {{
            color: #003366 !important;
            font-weight: 600;
        }}
        
        /* Métricas (KPIs) */
        [data-testid="stMetricValue"] {{
            color: #0056b3 !important;
            font-size: 26px !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: #666 !important;
        }}

        /* --- BOTÓN DE ACCIÓN (CORREGIDO) --- */
        div.stButton > button {{
            background-color: #004a99 !important;
            color: white !important;
            font-size: 18px !important;
            padding: 0.7rem 2rem;
            border-radius: 8px;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            width: 100%;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.25);
        }}
        div.stButton > button:active {{
            transform: translateY(0px);
        }}
        
        /* Ajustes de Tablas */
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES DE UTILIDAD ---
def fmt(valor):
    """Formato de miles: $1.000.000"""
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    # Valores por defecto PDF Nov 2025
    def_uf = 39643.59
    def_utm = 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except:
        return def_uf, def_utm

# --- 4. MOTOR DE CÁLCULO (PREVIRED NOV 2025) ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, s_min, t_imp_uf, t_sc_uf):
    
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    
    if liq_trib_meta < s_min * 0.4: return None

    # Topes Legales
    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    # Tasas AFP (Nov 2025)
    TASAS_AFP = {
        "Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, 
        "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0
    }
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    
    # AFP Trabajador
    if es_emp:
        tasa_afp_trab = 0.0
    else:
        comision = TASAS_AFP.get(afp_nom, 0)
        tasa_afp_trab = 0.0 if afp_nom == "SIN AFP" else (0.10 + (comision/100))

    # AFC (Seguro Cesantía)
    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    
    # Costos Empleador
    pct_sis = 0.0149
    pct_mut = 0.0093
    
    if es_emp:
        tasa_afc_emp = 0.024 # Asumimos aporte base
    else:
        tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    # Tabla Impuesto (Factores Mensuales)
    TABLA_IMP = [
        (13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74),
        (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80),
        (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)
    ]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    
    for _ in range(150):
        base_test = (min_b + max_b) / 2
        
        # Gratificación (Tope Estricto)
        grat = min(base_test * 0.25, TOPE_GRAT)
        
        tot_imp = base_test + grat
        
        # Bases Topadas
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        # Descuentos
        m_afp = int(b_prev * tasa_afp_trab)
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
            rebaja_trib = legal_7

        # Impuesto Único
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
                "COSTO TOTAL": int(costo_fin),
                "Base Tributable": int(base_trib),
                "Tope Grat": int(TOPE_GRAT)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base_test
        else: max_b = base_test
    return None

# --- 5. INTERFAZ GRÁFICA ---

# BARRA LATERAL (CONTROL)
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=140)
    st.title("Panel de Control")
    
    # 1. Indicadores (Casteo a float para evitar Warning de Streamlit)
    uf_live, utm_live = obtener_indicadores()
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        uf_input = st.number_input("UF ($)", value=float(uf_live), format="%.2f")
    with col_i2:
        utm_input = st.number_input("UTM ($)", value=float(utm_live), format="%.2f")
    
    st.divider()
    
    # 2. Parámetros Legales
    st.subheader("Parámetros Previred")
    sueldo_min = st.number_input("Sueldo Mínimo ($)", value=529000, step=1000)
    
    # Tope Gratificación (Visualización)
    tope_g = (4.75 * sueldo_min) / 12
    st.caption(f"Tope Gratificación (4.75 IMM): {fmt(tope_g)}")
    
    tope_imp_uf = st.number_input("Tope AFP/Salud (UF)", value=87.8, step=0.1)
    tope_afc_uf = st.number_input("Tope AFC (UF)", value=131.9, step=0.1)

# CABECERA PRINCIPAL
st.title("Calculadora de Remuneraciones Pro")
st.markdown("**Simulación Actualizada Noviembre 2025**")

# FORMULARIO DE ENTRADA
with st.container():
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("1. Objetivo Económico")
        # Inputs con ayuda visual del monto
        liq_target = st.number_input("Sueldo Líquido a Pagar ($)", value=1000000, step=10000, format="%d")
        st.caption(f"Valor ingresado: **{fmt(liq_target)}**") # Feedback visual de miles
        
        c_col, c_mov = st.columns(2)
        with c_col:
            colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
        with c_mov:
            movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

    with col2:
        st.subheader("2. Configuración Contractual")
        tipo = st.selectbox("Tipo de Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        
        c_afp, c_salud = st.columns(2)
        with c_afp:
            afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
        with c_salud:
            salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
            
        plan = 0.0
        if salud == "Isapre (UF)":
            plan = st.number_input("Valor Plan (UF)", value=0.0, step=0.01)

st.markdown("---")

# BOTÓN DE ACCIÓN
if st.button("CALCULAR ESCENARIO (VALIDADO)"):
    if (colacion + movilizacion) >= liq_target:
        st.error("❌ Error: Los haberes no imponibles no pueden superar al líquido total.")
    else:
        with st.spinner("Procesando nómina según normativa vigente..."):
            res = calcular_reverso_exacto(
                liq_target, colacion, movilizacion, tipo, afp, salud, plan, 
                uf_input, utm_input, sueldo_min, tope_imp_uf, tope_afc_uf
            )
        
        if res:
            st.success("✅ Cálculo Generado Exitosamente")
            
            # --- DASHBOARD DE RESULTADOS ---
            
            # 1. KPIs Principales
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Líquido a Pagar", fmt(res['LÍQUIDO']), delta="Objetivo")
            k4.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Inversión", delta_color="inverse")
            
            st.markdown("---")
            
            # 2. PESTAÑAS DETALLADAS (La solución al "no muestra todo")
            tab1, tab2, tab3 = st.tabs(["📄 Liquidación Trabajador", "🏢 Costo Empresa", "📊 Gráfico Distribución"])
            
            with tab1:
                st.markdown("#### Detalle de Liquidación de Sueldo")
                df_liq = pd.DataFrame([
                    ["HABERES", ""],
                    ["Sueldo Base", fmt(res['Sueldo Base'])],
                    [f"Gratificación (Tope: {fmt(res['Tope Grat'])})", fmt(res['Gratificación'])],
                    ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                    ["Movilización y Colación", fmt(res['No Imponibles'])],
                    ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                    ["", ""],
                    ["DESCUENTOS", ""],
                    [f"AFP ({afp})", fmt(-res['AFP'])],
                    [f"Salud ({salud})", fmt(-res['Salud'])],
                    ["Seguro de Cesantía", fmt(-res['AFC'])],
                    ["Impuesto Único (2da Cat)", fmt(-res['Impuesto'])],
                    ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                    ["", ""],
                    ["LÍQUIDO A PAGAR", fmt(res['LÍQUIDO'])]
                ], columns=["Concepto", "Monto"])
                st.table(df_liq)
            
            with tab2:
                st.markdown("#### Costos Patronales (Ocultos al trabajador)")
                st.info("Estos montos son pagados exclusivamente por el empleador y no se descuentan de la liquidación.")
                
                df_emp = pd.DataFrame([
                    ["Sueldo Imponible", fmt(res['Total Imponible'])],
                    ["(+) Aporte SIS (1.49%)", fmt(int(res['Total Imponible']*0.0149))], # Estimado visual
                    ["(+) Aporte AFC Empleador", fmt(int(res['Aportes Empresa'] * 0.6))], # Proporcional visual
                    ["(+) Mutual Seguridad (0.93%)", fmt(int(res['Total Imponible']*0.0093))],
                    ["(=) TOTAL APORTES PATRONALES", fmt(res['Aportes Empresa'])],
                    ["", ""],
                    ["COSTO TOTAL (Haberes + Aportes)", fmt(res['COSTO TOTAL'])]
                ], columns=["Ítem", "Valor"])
                st.table(df_emp)

            with tab3:
                st.markdown("#### Distribución del Costo")
                # Gráfico de Donut
                data_chart = {
                    'Concepto': ['Líquido Trabajador', 'Leyes Sociales (AFP/Salud)', 'Impuesto Único', 'Aportes Empresa'],
                    'Monto': [res['LÍQUIDO'], res['Total Descuentos']-res['Impuesto'], res['Impuesto'], res['Aportes Empresa']]
                }
                fig = px.pie(data_chart, values='Monto', names='Concepto', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("⚠️ No se encontró un sueldo bruto matemático para este líquido. Verifique que el monto no sea inferior al mínimo legal.")
