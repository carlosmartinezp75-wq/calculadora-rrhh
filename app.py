import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.express as px
import plotly.graph_objects as go
import random

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="HR Suite Intelligence",
    page_icon="🇨🇱",
    layout="wide"
)

# --- 2. ESTILOS VISUALES (FONDO FULL SCREEN) ---
def cargar_estilos():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        ext = img.split('.')[-1]
        try:
            with open(img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            
            # CSS CORREGIDO PARA FONDO TOTAL
            css_fondo = f"""
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/{ext};base64,{b64}");
                background-size: cover;
                background-position: center center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            /* Fondo de respaldo para el header */
            [data-testid="stHeader"] {{
                background-color: rgba(0,0,0,0);
            }}
            """
        except: pass
    else:
        css_fondo = """
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        """

    st.markdown(
        f"""
        <style>
        {css_fondo}
        
        /* Contenedor Principal (Tarjeta Blanca) */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            max-width: 95% !important;
        }}
        
        /* Tipografía Azul Corporativa */
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 800;
        }}
        
        p, label, li, .stTable {{
            color: #003366 !important;
            font-weight: 500;
        }}
        
        /* Inputs */
        .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            color: #004a99;
            font-weight: bold;
            border-radius: 8px;
        }}
        
        /* Feedback Visual */
        .miles-feedback {{
            font-size: 0.85rem;
            color: #28a745;
            font-weight: bold;
            margin-top: -10px;
            margin-bottom: 15px;
        }}
        
        /* Botón de Acción */
        div.stButton > button {{
            background-color: #004a99 !important;
            color: white !important;
            font-size: 18px !important;
            border-radius: 10px;
            padding: 0.8rem 2rem;
            border: none;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0,0,0,0.3);
        }}
        
        /* Ajuste Tablas */
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        
        #MainMenu, footer {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def mostrar_feedback_miles(valor):
    if valor > 0:
        st.markdown(f'<p class="miles-feedback">Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Fallback Nov 2025
    def_uf, def_utm = 39643.59, 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except:
        return def_uf, def_utm

# --- 4. DATA TABLES (PREVIRED NOV 2025) ---
def get_tabla_afp():
    # Datos extraídos del PDF Nov 2025
    data = {
        "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
        "Tasa Trabajador": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"],
        "SIS (Empleador)": ["1,49%", "1,49%", "1,49%", "1,49%", "1,49%", "1,49%", "1,49%"],
        "Costo Total (%)": ["12,93%", "12,93%", "12,76%", "12,65%", "12,94%", "12,07%", "11,95%"]
    }
    return pd.DataFrame(data)

def get_tabla_asignacion():
    data = {
        "Tramo": ["A", "B", "C", "D"],
        "Renta Mensual": ["Hasta $620.251", "> $620.251 y <= $905.941", "> $905.941 y <= $1.412.957", "> $1.412.957"],
        "Monto por Carga": ["$22.007", "$13.505", "$4.267", "$0"]
    }
    return pd.DataFrame(data)

def get_tabla_cesantia():
    data = {
        "Contrato": ["Indefinido", "Plazo Fijo", "Casa Particular"],
        "Empleador": ["2,4%", "3,0%", "3,0%"],
        "Trabajador": ["0,6%", "0,0%", "0,0%"]
    }
    return pd.DataFrame(data)

# --- 5. LOGICA NEGOCIO ---
def generar_perfil_detallado(cargo, rubro):
    if not cargo: return None
    contexto = f"en el sector {rubro}" if rubro else ""
    return {
        "titulo": cargo.title(),
        "rubro": rubro,
        "proposito": f"Gestionar y liderar procesos críticos del área {contexto}, asegurando eficiencia y cumplimiento normativo.",
        "funciones": ["Control de gestión y KPIs.", "Liderazgo de equipos.", "Reportabilidad a gerencia.", "Optimización de procesos."],
        "requisitos": ["Título Profesional.", "Experiencia comprobable.", "Manejo de ERP.", "Habilidades blandas."]
    }

def leer_pdf(archivo):
    if not PDF_AVAILABLE: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages: text += (page.extract_text() or "") + "\n"
        return text
    except: return None

# CALCULO REVERSO (MOTOR)
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, s_min, t_imp_uf, t_sc_uf):
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    if liq_trib_meta < s_min * 0.4: return None

    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    # Tasas reales Nov 2025 para cálculo
    TASAS_AFP_CALC = {"Capital": 11.44, "Cuprum": 11.44, "Habitat": 11.27, "PlanVital": 11.16, "Provida": 11.45, "Modelo": 10.58, "Uno": 10.46, "SIN AFP": 0.0}
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    if es_emp: tasa_afp = 0.0
    else:
        # La tabla entrega tasa total, restamos 10 para sacar comisión (aunque para el descuento usamos el total)
        tasa_total = TASAS_AFP_CALC.get(afp_nom, 0)
        tasa_afp = 0.0 if afp_nom == "SIN AFP" else (tasa_total / 100)

    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    tasa_afc_emp = 0.024
    if not es_emp: tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    pct_sis, pct_mut = 0.0149, 0.0093
    TABLA_IMP = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        tot_imp = base + grat
        
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        leg_7 = int(b_prev * 0.07)
        m_sal = leg_7 if salud_tipo == "Fonasa (7%)" else max(int(plan_uf * uf), leg_7)
        reb_trib = leg_7 if salud_tipo == "Fonasa (7%)" else leg_7

        base_trib = max(0, tot_imp - m_afp - reb_trib - m_afc)
        imp = 0
        f_utm = base_trib / utm
        for l, f, r in TABLA_IMP:
            if f_utm <= l:
                imp = (base_trib * f) - (r * utm)
                break
        imp = int(max(0, imp))
        
        liq_calc = tot_imp - m_afp - m_sal - m_afc - imp
        
        if abs(liq_calc - liq_trib_meta) < 5:
            m_sis, m_afc_e, m_mut = int(b_prev * pct_sis), int(b_afc * tasa_afc_emp), int(b_prev * pct_mut)
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Tope Grat": int(TOPE_GRAT),
                "Total Imponible": int(tot_imp), "No Imponibles": int(no_imp), "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_sal, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_sal + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp), "Aportes Empresa": aportes, "COSTO TOTAL": int(costo_fin)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base
        else: max_b = base
    return None

# --- 6. INTERFAZ GRÁFICA ---

# SIDEBAR (CONTROLES)
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=140)
    st.title("Panel de Control")
    uf_v, utm_v = obtener_indicadores()
    
    col_i1, col_i2 = st.columns(2)
    col_i1.metric("UF", fmt(uf_v).replace("$",""))
    col_i2.metric("UTM", fmt(utm_v))
    
    st.divider()
    st.subheader("Parámetros de Cálculo")
    sueldo_min = st.number_input("Sueldo Mínimo ($)", value=529000, step=1000)
    tope_imp_uf = st.number_input("Tope AFP (UF)", value=87.8, step=0.1)
    tope_afc_uf = st.number_input("Tope AFC (UF)", value=131.9, step=0.1)

# CABECERA
st.title("HR Suite Intelligence")
st.markdown("**Gestión Estratégica de Compensaciones y Talento**")

# TABS PRINCIPALES (AHORA SON 4)
tab_calc, tab_perf, tab_cv, tab_ind = st.tabs([
    "💰 Calculadora Sueldos", 
    "📋 Perfil de Cargo", 
    "🧠 Análisis de CV",
    "📊 Indicadores Oficiales"
])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Objetivo Líquido")
            liq_target = st.number_input("Sueldo Líquido ($)", value=1000000, step=50000, format="%d")
            mostrar_feedback_miles(liq_target)
            
            cc1, cc2 = st.columns(2)
            with cc1:
                colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
                mostrar_feedback_miles(colacion)
            with cc2:
                movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")
                mostrar_feedback_miles(movilizacion)

        with c2:
            st.subheader("2. Configuración")
            tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
            ca, cb = st.columns(2)
            with ca: afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
            with cb: salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
            plan = 0.0
            if salud == "Isapre (UF)":
                plan = st.number_input("Plan UF", value=0.0, step=0.01)

    st.markdown("---")
    
    if st.button("CALCULAR NÓMINA"):
        if (colacion + movilizacion) >= liq_target:
            st.error("Error: Haberes no imponibles superan al líquido.")
        else:
            with st.spinner("Procesando..."):
                res = calcular_reverso_exacto(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf_v, utm_v, sueldo_min, tope_imp_uf, tope_afc_uf)
            
            if res:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
                k2.metric("Total Imponible", fmt(res['Total Imponible']))
                k3.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
                k4.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
                
                st.markdown("---")
                
                c_res1, c_res2 = st.columns(2)
                with c_res1:
                    st.markdown("#### 📄 Liquidación Trabajador")
                    df_liq = pd.DataFrame([
                        ["HABERES", ""],
                        ["Sueldo Base", fmt(res['Sueldo Base'])],
                        [f"Gratificación (Tope: {fmt(res['Tope Grat'])})", fmt(res['Gratificación'])],
                        ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                        ["No Imponibles", fmt(res['No Imponibles'])],
                        ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                        ["", ""],
                        ["DESCUENTOS", ""],
                        [f"AFP ({afp})", fmt(-res['AFP'])],
                        [f"Salud ({salud})", fmt(-res['Salud'])],
                        ["Seguro Cesantía", fmt(-res['AFC'])],
                        ["Impuesto Único", fmt(-res['Impuesto'])],
                        ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                        ["", ""],
                        ["LÍQUIDO A PAGAR", fmt(res['LÍQUIDO'])]
                    ], columns=["Concepto", "Monto"])
                    st.table(df_liq)
                
                with c_res2:
                    st.markdown("#### 🏢 Costos Empresa")
                    df_emp = pd.DataFrame([
                        ["Sueldo Imponible", fmt(res['Total Imponible'])],
                        ["(+) SIS, Mutual, AFC Empleador", fmt(res['Aportes Empresa'])],
                        ["(+) Asignaciones No Imponibles", fmt(res['No Imponibles'])],
                        ["", ""],
                        ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
                    ], columns=["Ítem", "Valor"])
                    st.table(df_emp)
                    
                    fig = px.pie(values=[res['LÍQUIDO'], res['Total Descuentos'], res['Aportes Empresa']], 
                                 names=['Bolsillo Trabajador', 'Impuestos/Leyes Sociales', 'Costo Patronal'],
                                 color_discrete_sequence=px.colors.sequential.Blues_r, hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("No se encontró solución matemática.")

# --- TAB 2: PERFIL ---
with tab_perf:
    st.header("Generador de Perfiles")
    col_cargo, col_rubro = st.columns(2)
    with col_cargo: cargo_input = st.text_input("Cargo del Candidato", placeholder="Ej: Gerente Comercial")
    with col_rubro: rubro_input = st.selectbox("Rubro / Industria", ["Tecnología", "Minería", "Retail", "Salud", "Construcción", "Banca", "Servicios"])
    
    if cargo_input:
        perfil = generar_perfil_detallado(cargo_input, rubro_input)
        st.markdown(f"### 📋 Perfil: {perfil['titulo']} ({perfil['rubro']})")
        st.info(f"**Propósito:** {perfil['proposito']}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Funciones Clave:**")
            for f in perfil['funciones']: st.success(f"📌 {f}")
        with c2:
            st.markdown("**Requisitos Excluyentes:**")
            for r in perfil['requisitos']: st.markdown(f"✅ {r}")

# --- TAB 3: ANÁLISIS CV ---
with tab_cv:
    st.header("Análisis de Brechas")
    st.markdown("Módulo disponible con librerías de IA activas.")
    # (Código simplificado para evitar errores si no hay librerías PDF)
    if not PDF_AVAILABLE: st.warning("Instale 'pdfplumber' para activar.")

# --- TAB 4: INDICADORES (NUEVA) ---
with tab_ind:
    st.header("📊 Indicadores Previsionales y Tributarios")
    st.markdown("**Valores Oficiales (Referencia Previred Nov 2025)**")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("1. Tasas AFP")
        st.table(get_tabla_afp())
        
        st.subheader("2. Seguro de Cesantía")
        st.table(get_tabla_cesantia())
        
    with col_b:
        st.subheader("3. Asignación Familiar")
        st.table(get_tabla_asignacion())
        
        st.subheader("4. Rentas Topes (Imponibles)")
        st.info(f"""
        * **Para AFP y Salud:** 87,8 UF ({fmt(87.8 * uf_v)})
        * **Para Seguro Cesantía:** 131,9 UF ({fmt(131.9 * uf_v)})
        * **Renta Mínima:** $529.000
        """)

    st.markdown("---")
    st.subheader("5. Tabla Impuesto Único (Mensual)")
    st.caption(f"Cálculo dinámico basado en UTM del día: {fmt(utm_v)}")
    
    # Generar tabla impuesto dinámica
    TABLA_IMP = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
    data_imp = []
    for l, f, r in TABLA_IMP:
        hasta = "Más de" if l == 99999 else fmt(l * utm_v)
        data_imp.append([f"Hasta {l} UTM", hasta, f"{f*100:.2f}%", fmt(r * utm_v)])
    
    df_imp = pd.DataFrame(data_imp, columns=["Tramo (UTM)", "Renta Tope ($)", "Factor", "Rebaja ($)"])
    st.table(df_imp)
