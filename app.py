import streamlit as st
import pandas as pd
import requests

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Calculadora Sueldos Chile", page_icon="🇨🇱", layout="centered")

# --- ESTILO VISUAL (FONDO AZUL Y FORMATO) ---
st.markdown("""
    <style>
    /* Fondo Azul Degradado Profesional */
    .stApp {
        background: linear-gradient(to bottom, #e3f2fd, #ffffff);
    }
    /* Títulos en Azul Oscuro */
    h1, h2, h3 {
        color: #0d47a1 !important;
    }
    /* Métricas destacadas */
    [data-testid="stMetricValue"] {
        color: #1565c0 !important;
        font-weight: bold;
    }
    /* Botón personalizado */
    div.stButton > button {
        background-color: #1565c0;
        color: white;
        border-radius: 10px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #0d47a1;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN FORMATO CHILENO ---
def fmt(valor):
    """Convierte 1000000 en $1.000.000"""
    return f"${int(valor):,.0f}".replace(",", ".")

# --- 1. DATOS EN VIVO ---
def obtener_indicadores():
    try:
        response = requests.get('https://mindicador.cl/api', timeout=2)
        data = response.json()
        return data['uf']['valor'], data['utm']['valor']
    except:
        return 38000.0, 67000.0

# --- 2. MOTOR DE CÁLCULO ---
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

    # Búsqueda Binaria
    min_bruto = liquido_a_buscar
    max_bruto = liquido_a_buscar * 2.5
    bruto_encontrado = 0
    TABLA_IMPUESTO = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (99999,0.35,16.80)]

    for _ in range(100):
        bruto_test = (min_bruto + max_bruto) / 2
        base_afp = min(bruto_test, tope_pesos_afp)
        base_sc = min(bruto_test, tope_pesos_sc)
        
        monto_afp = int(base_afp * tasa_afp_total)
        monto_afc_trab = int(base_sc * tasa_afc_trab)
        
        legal_7 = int(base_afp * 0.07)
        monto_salud = 0
        if salud_tipo == "Fonasa (7%)":
            monto_salud = legal_7
        else: 
            valor_plan_pesos = int(plan_uf * uf_dia)
            monto_salud = max(valor_plan_pesos, legal_7)
            
        base_tributable = bruto_test - (monto_afp + legal_7 + monto_afc_trab)
        
        impuesto = 0
        base_utm = base_tributable / utm_dia
        for lim, fac, reb in TABLA_IMPUESTO:
            if base_utm <= lim:
                impuesto = (base_tributable * fac) - (reb * utm_dia)
                break
        impuesto = int(max(0, impuesto))
        
        liquido_calculado = bruto_test - monto_afp - monto_salud - monto_afc_trab - impuesto
        
        if abs(liquido_calculado - liquido_a_buscar) < 10:
            bruto_encontrado = bruto_test
            monto_sis = int(base_afp * 0.0149) if not es_empresarial else 0
            monto_afc_emp = int(base_sc * tasa_afc_emp)
            monto_mutual = int(base_afp * 0.0093) if not es_empresarial else 0
            costo_empresa = bruto_encontrado + monto_sis + monto_afc_emp + monto_mutual + no_imponibles
            
            return {
                "Sueldo Base (Bruto)": int(bruto_encontrado),
                "Colación/Mov": int(no_imponibles),
                "TOTAL HABERES": int(bruto_encontrado + no_imponibles),
                "Descuento AFP": int(monto_afp),
                "Descuento Salud": int(monto_salud),
                "Descuento AFC": int(monto_afc_trab),
                "Impuesto Único": int(impuesto),
                "LÍQUIDO FINAL": int(liquido_calculado + no_imponibles),
                "Aportes Empresa": int(monto_sis + monto_afc_emp + monto_mutual),
                "COSTO TOTAL EMPRESA": int(costo_empresa)
            }
            break
        elif liquido_calculado < liquido_a_buscar:
            min_bruto = bruto_test
        else:
            max_bruto = bruto_test
    return None

# --- 3. INTERFAZ GRÁFICA ---
st.title("🇨🇱 Simulador de Sueldos Pro")
st.markdown("Calcula el **Costo Empresa** y el **Bruto** con precisión.")

with st.sidebar:
    st.header("Parámetros Hoy")
    uf_val, utm_val = obtener_indicadores()
    st.metric("UF", fmt(uf_val).replace("$", "") + " / UF") # Formato visual limpio
    st.metric("UTM", fmt(utm_val))
    st.info("Conectado a Mindicador.cl")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Bolsillo Trabajador")
    # format="%d" ayuda a que no aparezcan decimales molestos en el input
    liquido_target = st.number_input("Sueldo Líquido TOTAL ($)", value=1000000, step=50000, format="%d")
    colacion = st.number_input("Bono Colación ($)", value=50000, step=5000, format="%d")
    movilizacion = st.number_input("Bono Movilización ($)", value=50000, step=5000, format="%d")
    
with col2:
    st.subheader("2. Contrato y Previsión")
    tipo = st.selectbox("Tipo Contrato", ["Contrato Indefinido", "Contrato Plazo Fijo", "Sueldo Empresarial"])
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP (Empresarial)"], index=2)
    salud = st.selectbox("Previsión Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan_uf = 0.0
    if salud == "Isapre (UF)":
        plan_uf = st.number_input("Valor Plan (UF)", value=0.0, step=0.1)

st.markdown("---")

if st.button("CALCULAR ESCENARIO", type="primary", use_container_width=True):
    if (colacion + movilizacion) >= liquido_target:
        st.error("❌ Error: Los bonos no imponibles superan al líquido total.")
    else:
        with st.spinner("Calculando..."):
            res = calcular_simulacion_completa(liquido_target, colacion, movilizacion, tipo, afp, salud, plan_uf, uf_val, utm_val)
        
        if res:
            # MÉTRICAS CON FORMATO DE MILES
            m1, m2, m3 = st.columns(3)
            m1.metric("Sueldo Bruto", fmt(res['Sueldo Base (Bruto)']))
            m2.metric("Líquido Bolsillo", fmt(res['LÍQUIDO FINAL']), delta="Objetivo")
            m3.metric("Costo Empresa", fmt(res['COSTO TOTAL EMPRESA']), delta="Total", delta_color="inverse")
            
            st.markdown("### 📋 Desglose de la Liquidación")
            
            # Tabla con formato visual
            df = pd.DataFrame({
                "Concepto": [
                    "Sueldo Base (Imponible)", "(+) Colación y Movilización", "(=) TOTAL HABERES",
                    "(-) AFP", "(-) Salud", "(-) AFC", "(-) Impuesto Único",
                    "(=) LÍQUIDO A PAGO",
                    "(+) Aportes Extra Empresa",
                    "(=) COSTO REAL EMPRESA"
                ],
                "Monto": [
                    fmt(res['Sueldo Base (Bruto)']), fmt(res['Colación/Mov']), fmt(res['TOTAL HABERES']),
                    fmt(-res['Descuento AFP']), fmt(-res['Descuento Salud']), fmt(-res['Descuento AFC']), fmt(-res['Impuesto Único']),
                    fmt(res['LÍQUIDO FINAL']),
                    fmt(res['Aportes Empresa']),
                    fmt(res['COSTO TOTAL EMPRESA'])
                ]
            })
            
            # Mostramos la tabla limpia sin índice
            st.table(df)
            
        else:
            st.error("Error en el cálculo.")
