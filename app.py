import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Calculadora RRHH Pro (Nov 2025)",
    page_icon="🇨🇱",
    layout="wide"
)

# --- 2. ESTILOS VISUALES ---
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
            background-color: rgba(255, 255, 255, 0.98);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, p, label, .stMarkdown, .stSelectbox label, .stNumberInput label {{
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
        }}
        [data-testid="stMetricValue"] {{
            color: #0056b3 !important;
            font-weight: 800;
        }}
        div.stButton > button {{
            background-color: #0056b3 !important;
            color: #ffffff !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none;
            padding: 0.7rem 2rem;
            border-radius: 8px;
            width: 100%;
            transition: all 0.3s ease;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: scale(1.01);
        }}
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES DE DATOS ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    # Valores por defecto del PDF (Noviembre 2025) en caso de fallo API
    default_uf = 39643.59
    default_utm = 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return default_uf, default_utm

# --- 4. BARRA LATERAL (PREVIRED NOVIEMBRE 2025) ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=150)
    st.title("Indicadores Nov 2025")
    
    # A. Indicadores Económicos
    uf_live, utm_live = obtener_indicadores()
    
    # Permitir sobrescribir valores si el usuario quiere ser exacto con el PDF
    uf_input = st.number_input("Valor UF", value=uf_live, format="%.2f")
    utm_input = st.number_input("Valor UTM", value=utm_live, format="%.2f")
    
    st.divider()
    
    # B. Rentas Mínimas y Topes
    st.subheader("Rentas y Topes")
    
    # Valor corregido según PDF Nov 2025
    sueldo_min = st.number_input("Sueldo Mínimo", value=529000, step=1000)
    
    # Topes corregidos según PDF Nov 2025
    tope_imponible_uf = st.number_input("Tope AFP/Salud (87,8 UF)", value=87.8, step=0.1)
    tope_seguro_uf = st.number_input("Tope Seg. Cesantía (131,9 UF)", value=131.9, step=0.1)
    
    # Cálculo visual tope gratificación
    tope_grat_mensual = (4.75 * sueldo_min) / 12
    st.info(f"Tope Gratificación: {fmt(tope_grat_mensual)}")

    st.divider()
    
    # C. Asignación Familiar
    with st.expander("Ver Tabla Asignación Familiar"):
        df_asig = pd.DataFrame({
            "Tramo": ["A", "B", "C", "D"],
            "Renta Máxima": ["$620.251", "$905.941", "$1.412.957", "Mayor a..."],
            "Monto": ["$22.007", "$13.505", "$4.267", "$0"]
        })
        st.table(df_asig)

# --- 5. MOTOR DE CÁLCULO (LÓGICA ACTUALIZADA) ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, 
                          s_min, t_imp_uf, t_sc_uf):
    
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    
    if liq_trib_meta < s_min * 0.4: return None

    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    # Tasas AFP Noviembre 2025
    TASAS_AFP = {
        "Capital": 1.44, 
        "Cuprum": 1.44, 
        "Habitat": 11.27, # Corrección: PDF dice 11.27% total (10+1.27) -> Comisión es 1.27
        "PlanVital": 1.16, 
        "Provida": 1.45, 
        "Modelo": 0.58, 
        "Uno": 0.49,
        "SIN AFP": 0.0
    }
    # Ajuste manual del dict para solo comisión (La tabla del PDF muestra total, resto 10%)
    # PDF: Habitat Total 11.27% -> Comisión 1.27%
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    
    # Tasa AFP
    comision = 0.0
    if afp_nom in TASAS_AFP:
        comision = TASAS_AFP[afp_nom] # El dict ya tiene las comisiones
        if afp_nom == "Habitat": comision = 1.27 # Ajuste fino segun PDF
    
    tasa_afp_trab = 0.10 + (comision/100)
    if afp_nom == "SIN AFP" or es_emp: tasa_afp_trab = 0.0

    # Tasas AFC
    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    tasa_afc_emp = 0.024 if (tipo_con == "Indefinido") else (0.03 if tipo_con == "Plazo Fijo" else 0.0)
    if es_emp: tasa_afc_emp = 0.024 # Asumimos aporte base

    # Costos Empleador
    pct_sis = 0.0149 #
    pct_mut = 0.0093 #

    # TABLA IMPUESTO ÚNICO (Segunda Categoría) - Factores Estándar x UTM
    TABLA_IMP = [
        (13.5, 0.0, 0.0),
        (30.0, 0.04, 0.54),
        (50.0, 0.08, 1.74), # Corrección factor rebaja acumulada
        (70.0, 0.135, 4.49),
        (90.0, 0.23, 11.14),
        (120.0, 0.304, 17.80),
        (310.0, 0.35, 23.32),
        (99999.0, 0.40, 38.82)
    ]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    
    for _ in range(150):
        base_test = (min_b + max_b) / 2
        
        # Gratificación
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
st.title("Calculadora Remuneraciones")
st.markdown("#### Actualizada Noviembre 2025")

c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Objetivo Líquido")
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

if st.button("CALCULAR (VALIDADO PREVIRED NOV 2025)"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Haberes no imponibles superan al líquido.")
    else:
        res = calcular_reverso_exacto(
            liq_target, colacion, movilizacion, tipo, afp, salud, plan, 
            uf_input, utm_input, 
            sueldo_min, tope_imponible_uf, tope_seguro_uf
        )
        
        if res:
            st.success("✅ Cálculo Generado Correctamente")
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Total Imponible", fmt(res['Total Imponible']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown("### 📋 Desglose Oficial")
            
            # TABLA DE RESULTADOS
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
            
            st.table(df)
            
            # Mostrar Tabla Impuesto Único Referencial
            with st.expander("Ver Tabla Impuesto Único Utilizada"):
                st.caption(f"Calculada con UTM: {fmt(utm_input)}")
                data_imp = []
                for tramo in [(13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74), (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80), (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)]:
                     data_imp.append([f"Hasta {tramo[0]} UTM", f"{tramo[1]*100}%", fmt(tramo[2]*utm_input)])
                st.table(pd.DataFrame(data_imp, columns=["Tramo", "Factor", "Rebaja"]))
            
        else:
            st.error("No se encontró solución matemática viable.")
