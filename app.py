import streamlit as st
import pandas as pd
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Calculadora Inversa RRHH", page_icon="💰", layout="centered")

# --- 1. CONEXIÓN BANCO CENTRAL ---
def obtener_indicadores():
    try:
        response = requests.get('https://mindicador.cl/api', timeout=3)
        data = response.json()
        return data['uf']['valor'], data['utm']['valor']
    except:
        return 38000.0, 67000.0 # Fallback si falla la API

# --- 2. MOTOR DE CÁLCULO INVERSO (Gross-up) ---
def calcular_bruto_desde_liquido(liquido_objetivo, tipo_contrato, nombre_afp, salud_tipo, plan_uf, uf_dia, utm_dia):
    
    # --- CONFIGURACIÓN DE TASAS ---
    # Tasas AFP (Nov 2024 aprox)
    TASAS_AFP = {
        "Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58,
        "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP (Empresarial)": 0.0
    }
    
    # 1. Configurar AFP
    tasa_afp_base = 0.10
    comision_afp = TASAS_AFP.get(nombre_afp, 0) / 100
    
    # Excepción Sueldo Empresarial / Pensionado
    if nombre_afp == "SIN AFP (Empresarial)":
        tasa_afp_base = 0.0
        comision_afp = 0.0

    tasa_afp_total = tasa_afp_base + comision_afp
    
    # 2. Configurar Seguro Cesantía (AFC)
    # Reglas: 
    # - Indefinido: Trab 0.6% / Emp 2.4%
    # - Plazo Fijo: Trab 0.0% / Emp 3.0%
    # - Empresarial: Trab 0.0% / Emp 0.0%
    
    es_empresarial = (tipo_contrato == "Sueldo Empresarial")
    
    tasa_afc_trab = 0.0
    tasa_afc_emp = 0.0
    
    if tipo_contrato == "Contrato Indefinido":
        tasa_afc_trab = 0.006
        tasa_afc_emp = 0.024
    elif tipo_contrato == "Contrato Plazo Fijo":
        tasa_afc_trab = 0.000 # Trabajador no paga en plazo fijo
        tasa_afc_emp = 0.030
    
    # 3. Otros Aportes Empresa
    tasa_sis = 0.0149 if not es_empresarial else 0.0
    tasa_mutual = 0.0093 if not es_empresarial else 0.0

    # Topes Legales (UF)
    TOPE_IMP_UF = 84.3
    TOPE_SC_UF = 126.6
    
    tope_pesos_afp = TOPE_IMP_UF * uf_dia
    tope_pesos_sc = TOPE_SC_UF * uf_dia

    # --- ALGORITMO DE BÚSQUEDA BINARIA ---
    # Buscamos el Bruto que genere exactamente el Líquido deseado
    min_bruto = liquido_objetivo
    max_bruto = liquido_objetivo * 2.5
    bruto_final = 0
    data_final = {}
    
    # Tabla Impuesto Único (Factores Mensuales)
    TABLA_IMPUESTO = [
        (13.5, 0, 0), (30, 0.04, 0.54), (50, 0.08, 1.08),
        (70, 0.135, 2.73), (90, 0.23, 7.48), (120, 0.304, 12.66), (99999, 0.35, 16.80)
    ]

    for _ in range(100): # 100 iteraciones para precisión máxima
        bruto_test = (min_bruto + max_bruto) / 2
        
        # Bases Imponibles con Tope
        base_afp = min(bruto_test, tope_pesos_afp)
        base_sc = min(bruto_test, tope_pesos_sc)

        # Descuentos Trabajador
        monto_afp = int(base_afp * tasa_afp_total)
        monto_afc_trab = int(base_sc * tasa_afc_trab)
        
        # Salud
        monto_salud = 0
        legal_7 = int(base_afp * 0.07)
        if salud_tipo == "Fonasa (7%)":
            monto_salud = legal_7
        else: # Isapre
            valor_plan_pesos = int(plan_uf * uf_dia)
            # El descuento legal para tributar es el 7%, el resto es voluntario, 
            # pero para el líquido se resta todo.
            monto_salud = max(valor_plan_pesos, legal_7)
        
        # Base Tributable (Bruto - Leyes Sociales Obligatorias)
        # Nota: Para el impuesto, Isapre se considera hasta el 7% tope legal en muchos casos,
        # pero para simplificar usaremos el descuento efectivo legal.
        base_tributable = bruto_test - (monto_afp + legal_7 + monto_afc_trab)
        
        # Impuesto Único
        impuesto = 0
        base_utm = base_tributable / utm_dia
        for limite, factor, rebaja in TABLA_IMPUESTO:
            if base_utm <= limite:
                impuesto = (base_tributable * factor) - (rebaja * utm_dia)
                break
        impuesto = int(max(0, impuesto))
        
        # Líquido Resultante
        liquido_calculado = bruto_test - monto_afp - monto_salud - monto_afc_trab - impuesto
        
        if abs(liquido_calculado - liquido_objetivo) < 10: # Tolerancia $10 pesos
            bruto_final = bruto_test
            
            # Calcular Costo Empresa Final
            monto_sis = int(base_afp * tasa_sis)
            monto_afc_emp = int(base_sc * tasa_afc_emp)
            monto_mutual = int(base_afp * tasa_mutual)
            costo_empresa = bruto_final + monto_sis + monto_afc_emp + monto_mutual
            
            data_final = {
                "Sueldo Bruto Base": int(bruto_final),
                "Descuento AFP": int(monto_afp),
                "Descuento Salud": int(monto_salud),
                "Descuento AFC (Trab)": int(monto_afc_trab),
                "Impuesto Único": int(impuesto),
                "Líquido Estimado": int(liquido_calculado),
                "Aporte SIS": int(monto_sis),
                "Aporte AFC (Emp)": int(monto_afc_emp),
                "Aporte Mutual": int(monto_mutual),
                "COSTO TOTAL EMPRESA": int(costo_empresa)
            }
            break
        elif liquido_calculado < liquido_objetivo:
            min_bruto = bruto_test
        else:
            max_bruto = bruto_test
            
    return data_final

# --- 3. INTERFAZ GRÁFICA (UI STREAMLIT) ---
st.title("🇨🇱 Calculadora de Costo Empresa")
st.markdown("Obtén el **Sueldo Bruto** y el **Costo Real** a partir de lo que el trabajador quiere ganar.")
st.markdown("---")

# Barra Lateral
with st.sidebar:
    st.header("Indicadores Hoy")
    uf_val, utm_val = obtener_indicadores()
    st.metric("Valor UF", f"${uf_val:,.2f}")
    st.metric("Valor UTM", f"${utm_val:,.2f}")
    st.info("Datos del Banco Central actualizados.")

# Formulario
col1, col2 = st.columns(2)

with col1:
    st.subheader("Datos Contrato")
    tipo = st.selectbox("Tipo de Contrato", ["Contrato Indefinido", "Contrato Plazo Fijo", "Sueldo Empresarial"])
    liquido = st.number_input("Sueldo Líquido Esperado ($)", value=1000000, step=50000, help="Lo que llega al bolsillo")

with col2:
    st.subheader("Datos Previsionales")
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP (Empresarial)"], index=2)
    salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan_uf = 0.0
    if salud == "Isapre (UF)":
        plan_uf = st.number_input("Plan Isapre (UF)", value=0.0, step=0.1)

# Botón Calcular
if st.button("CALCULAR COSTO EMPRESA", type="primary", use_container_width=True):
    with st.spinner("Calculando impuestos y leyes sociales..."):
        res = calcular_bruto_desde_liquido(liquido, tipo, afp, salud, plan_uf, uf_val, utm_val)
    
    if res:
        st.success("✅ Cálculo Completado")
        
        # Tarjetas de Resumen
        c1, c2, c3 = st.columns(3)
        c1.metric("Sueldo Bruto", f"${res['Sueldo Bruto Base']:,.0f}", delta="Contrato")
        c2.metric("Líquido", f"${res['Líquido Estimado']:,.0f}", delta="Bolsillo")
        c3.metric("Costo Empresa", f"${res['COSTO TOTAL EMPRESA']:,.0f}", delta="Total", delta_color="inverse")
        
        st.markdown("---")
        
        # Detalle Tabular
        st.subheader("Desglose Detallado")
        
        df_detalle = pd.DataFrame({
            "Concepto": [
                "SUELDO BRUTO", 
                "(-) AFP", "(-) Salud", "(-) AFC Trabajador", "(-) Impuesto Único",
                "(=) LÍQUIDO", 
                "(+) SIS Empresa", "(+) AFC Empresa", "(+) Mutual",
                "(=) COSTO EMPRESA"
            ],
            "Monto": [
                res['Sueldo Bruto Base'],
                -res['Descuento AFP'], -res['Descuento Salud'], -res['Descuento AFC (Trab)'], -res['Impuesto Único'],
                res['Líquido Estimado'],
                res['Aporte SIS'], res['Aporte AFC (Emp)'], res['Aporte Mutual'],
                res['COSTO TOTAL EMPRESA']
            ]
        })
        
        # Formatear números
        # df_detalle['Monto'] = df_detalle['Monto'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(df_detalle, use_container_width=True, hide_index=True)
        
    else:
        st.error("No se pudo calcular. Revisa los valores ingresados.")
