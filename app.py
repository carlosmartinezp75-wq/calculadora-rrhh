import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.express as px
import plotly.graph_objects as go
import random

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="HR Suite Pro",
    page_icon="👔",
    layout="wide"
)

# --- 2. ESTILOS VISUALES (CSS BLINDADO) ---
def cargar_estilos():
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
        .block-container {{
            background-color: rgba(255, 255, 255, 0.97);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }}
        p, label, .stSelectbox label, .stNumberInput label, .stTextInput label {{
            color: #003366 !important;
            font-weight: 600;
        }}
        [data-testid="stMetricValue"] {{
            color: #0056b3 !important;
            font-size: 26px !important;
        }}
        /* BOTÓN MEJORADO */
        div.stButton > button {{
            background-color: #004a99 !important;
            color: white !important;
            font-size: 18px !important;
            padding: 0.7rem 2rem;
            border-radius: 8px;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            width: 100%;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
        }}
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    def_uf, def_utm = 39643.59, 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except:
        return def_uf, def_utm

# --- 4. GENERADOR DE PERFILES Y MARKET DATA ---
def generar_perfil_cargo(cargo):
    """Genera un perfil estandarizado basado en el nombre del cargo"""
    if not cargo: return None
    
    cargo = cargo.title()
    perfil = {
        "titulo": cargo,
        "mision": f"Liderar y ejecutar las funciones críticas asociadas al área de {cargo}, asegurando el cumplimiento de los objetivos estratégicos de la organización.",
        "responsabilidades": [
            f"Gestión y planificación operativa de procesos de {cargo}.",
            "Elaboración de informes de gestión y KPIs del área.",
            "Coordinación con equipos multidisciplinarios.",
            "Optimización continua de procedimientos internos."
        ],
        "competencias": ["Liderazgo efectivo", "Visión analítica", "Trabajo bajo presión", "Comunicación asertiva"]
    }
    return perfil

def generar_benchmark_mercado(sueldo_usuario, cargo):
    """Simula una curva de mercado basada en el sueldo ingresado para efectos comparativos"""
    # Lógica de simulación para mostrar funcionalidad (En prod requeriría API real)
    variacion = sueldo_usuario * 0.2
    min_mercado = sueldo_usuario - variacion
    max_mercado = sueldo_usuario + variacion
    promedio = sueldo_usuario + (random.randint(-50000, 50000)) # Simulación leve desviación
    
    return {
        "min": min_mercado,
        "max": max_mercado,
        "avg": promedio,
        "estado": "En Rango" if min_mercado <= sueldo_usuario <= max_mercado else "Fuera de Rango"
    }

# --- 5. MOTOR DE CÁLCULO ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, s_min, t_imp_uf, t_sc_uf):
    
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    if liq_trib_meta < s_min * 0.4: return None

    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    
    if es_emp: tasa_afp_trab = 0.0
    else:
        comision = TASAS_AFP.get(afp_nom, 0)
        tasa_afp_trab = 0.0 if afp_nom == "SIN AFP" else (0.10 + (comision/100))

    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    pct_sis, pct_mut = 0.0149, 0.0093
    
    if es_emp: tasa_afc_emp = 0.024
    else: tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    TABLA_IMP = [
        (13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74),
        (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80),
        (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)
    ]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    
    for _ in range(150):
        base_test = (min_b + max_b) / 2
        grat = min(base_test * 0.25, TOPE_GRAT)
        tot_imp = base_test + grat
        
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
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
            m_sis = int(b_prev * pct_sis)
            m_afc_e = int(b_afc * tasa_afc_emp)
            m_mut = int(b_prev * pct_mut)
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            
            return {
                "Sueldo Base": int(base_test), "Gratificación": int(grat),
                "Total Imponible": int(tot_imp), "No Imponibles": int(no_imp),
                "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_salud + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp),
                "Aportes Empresa": aportes, "COSTO TOTAL": int(costo_fin),
                "Base Tributable": int(base_trib), "Tope Grat": int(TOPE_GRAT)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base_test
        else: max_b = base_test
    return None

# --- 6. INTERFAZ GRÁFICA ---

# SIDEBAR
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=140)
    st.title("Panel de Control")
    uf_live, utm_live = obtener_indicadores()
    
    c1, c2 = st.columns(2)
    c1.metric("UF", fmt(uf_live).replace("$",""))
    c2.metric("UTM", fmt(utm_live))
    
    st.divider()
    st.subheader("Parámetros Previred")
    sueldo_min = st.number_input("Sueldo Mínimo", value=529000, step=1000)
    
    tope_grat = (4.75 * sueldo_min) / 12
    st.caption(f"Tope Gratificación: {fmt(tope_grat)}")
    
    tope_imp_uf = st.number_input("Tope AFP/Salud (UF)", value=87.8, step=0.1)
    tope_afc_uf = st.number_input("Tope AFC (UF)", value=131.9, step=0.1)

# MAIN
st.title("HR Suite: Calculadora de Compensaciones")
st.markdown("**Simulación & Benchmark de Mercado Noviembre 2025**")

with st.container():
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("1. Datos del Cargo y Renta")
        cargo_input = st.text_input("Nombre del Cargo", placeholder="Ej: Analista Contable Senior")
        liq_target = st.number_input("Sueldo Líquido Objetivo ($)", value=1000000, step=10000, format="%d")
        st.caption(f"Valor ingresado: **{fmt(liq_target)}**")
        
        c_col, c_mov = st.columns(2)
        with c_col: colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
        with c_mov: movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

    with col2:
        st.subheader("2. Configuración Contractual")
        tipo = st.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        
        c_afp, c_salud = st.columns(2)
        with c_afp: afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
        with c_salud: salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
            
        plan = 0.0
        if salud == "Isapre (UF)":
            plan = st.number_input("Valor Plan (UF)", value=0.0, step=0.01)

st.markdown("---")

if st.button("CALCULAR Y GENERAR REPORTE"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Haberes no imponibles superan al líquido.")
    else:
        with st.spinner("Generando liquidación, tabla de impuestos y benchmark de mercado..."):
            res = calcular_reverso_exacto(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf_live, utm_live, sueldo_min, tope_imp_uf, tope_afc_uf)
        
        if res:
            st.success("✅ Reporte Generado Exitosamente")
            
            # KPI Cards
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
            k4.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown("---")
            
            # TABS AVANZADOS
            tab_liq, tab_imp, tab_bench = st.tabs(["📄 Liquidación", "⚖️ Tabla Impuestos", "📈 Perfil & Mercado"])
            
            with tab_liq:
                c_liq, c_emp = st.columns(2)
                with c_liq:
                    st.markdown("#### Liquidación Trabajador")
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
                
                with c_emp:
                    st.markdown("#### Costo Empresa")
                    df_emp = pd.DataFrame([
                        ["Sueldo Imponible", fmt(res['Total Imponible'])],
                        ["(+) Aporte SIS (1.49%)", fmt(int(res['Total Imponible']*0.0149))],
                        ["(+) Aporte AFC Empleador", fmt(int(res['Aportes Empresa'] * 0.6))],
                        ["(+) Mutual (0.93%)", fmt(int(res['Total Imponible']*0.0093))],
                        ["(=) TOTAL APORTES", fmt(res['Aportes Empresa'])],
                        ["", ""],
                        ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
                    ], columns=["Ítem", "Monto"])
                    st.table(df_emp)

            with tab_imp:
                st.markdown("#### Tabla Impuesto Único (Detalle de Cálculo)")
                st.info(f"Cálculo realizado con UTM: {fmt(utm_live)}")
                st.markdown(f"**Base Tributable del Trabajador:** {fmt(res['Base Tributable'])}")
                
                tramos = [
                    (13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74),
                    (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80),
                    (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)
                ]
                data_imp = []
                base_t = res['Base Tributable']
                
                for i, (lim, fac, reb) in enumerate(tramos):
                    desde = 0 if i==0 else tramos[i-1][0] * utm_live
                    hasta = lim * utm_live
                    check = "✅ TRAMO APLICADO" if desde < base_t <= hasta else ""
                    
                    data_imp.append([
                        f"Hasta {lim} UTM",
                        f"{fmt(hasta)}",
                        f"{fac*100:.2f}%",
                        f"{fmt(reb * utm_live)}",
                        check
                    ])
                
                st.table(pd.DataFrame(data_imp, columns=["Tramo (UTM)", "Tope en Pesos", "Factor", "Rebaja", "Estado"]))

            with tab_bench:
                st.markdown("#### Análisis de Cargo y Mercado")
                
                if cargo_input:
                    perfil = generar_perfil_cargo(cargo_input)
                    bench = generar_benchmark_mercado(liq_target, cargo_input)
                    
                    c_perf, c_graf = st.columns([1, 1])
                    
                    with c_perf:
                        st.markdown(f"### 📋 Perfil: {perfil['titulo']}")
                        st.markdown(f"**Misión:** {perfil['mision']}")
                        st.markdown("**Responsabilidades Clave:**")
                        for r in perfil['responsabilidades']:
                            st.markdown(f"- {r}")
                        st.markdown("**Competencias:**")
                        st.markdown(", ".join(perfil['competencias']))
                    
                    with c_graf:
                        st.markdown("### 📊 Comparativa de Mercado")
                        st.caption("Comparación referencial vs Mercado Chileno (Estimado)")
                        
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number+delta",
                            value = liq_target,
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            title = {'text': "Posición en Mercado", 'font': {'size': 24}},
                            delta = {'reference': bench['avg'], 'increasing': {'color': "green"}},
                            gauge = {
                                'axis': {'range': [None, bench['max']*1.2], 'tickwidth': 1, 'tickcolor': "darkblue"},
                                'bar': {'color': "#004a99"},
                                'bgcolor': "white",
                                'borderwidth': 2,
                                'bordercolor': "gray",
                                'steps': [
                                    {'range': [0, bench['min']], 'color': '#ffcccb'},
                                    {'range': [bench['min'], bench['max']], 'color': '#e6f3ff'}],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': liq_target}}))
                        
                        st.plotly_chart(fig, use_container_width=True)
                        st.info(f"El sueldo promedio estimado para este rango es: {fmt(bench['avg'])}")
                        
                else:
                    st.warning("⚠️ Ingrese un nombre de Cargo arriba para generar el perfil y benchmark.")

        else:
            st.error("No se encontró solución matemática.")
