import streamlit as st
import pandas as pd
import base64
import os
import io
import zipfile
import tempfile
from datetime import datetime, date

# =============================================================================
# 1. GESTIÓN DE LIBRERÍAS (SAFE MODE)
# =============================================================================
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import xlsxwriter
    LIBRARIES_OK = True
except ImportError as e:
    LIBRARIES_OK = False
    st.error(f"⚠️ Faltan librerías: {e}. Ejecuta: pip install fpdf python-docx xlsxwriter pandas streamlit")

# =============================================================================
# 2. CONFIGURACIÓN DEL SISTEMA
# =============================================================================
st.set_page_config(page_title="HR Suite Enterprise V44 (Stable)", page_icon="🏢", layout="wide")

# =============================================================================
# 3. MEMORIA DE SESIÓN (ESTADO)
# =============================================================================
def init_state():
    if "empresa" not in st.session_state:
        st.session_state.empresa = {"rut": "", "nombre": "", "giro": "Servicios", "direccion": "Santiago", "rep_nombre": "", "rep_rut": ""}
    if "trabajador" not in st.session_state:
        st.session_state.trabajador = {"rut": "", "nombre": "", "nacionalidad": "Chilena", "domicilio": ""}
    if "calculo_actual" not in st.session_state:
        st.session_state.calculo_actual = None
    if "logo_bytes" not in st.session_state:
        st.session_state.logo_bytes = None

init_state()

# =============================================================================
# 4. DATOS Y CONSTANTES (PREVIRED NOV 2025)
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "SUELDO_MIN": 529000,
    "TOPE_AFP_UF": 87.8, "TOPE_AFC_UF": 131.9
}

def fmt(valor):
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

# =============================================================================
# 5. MOTOR DE CÁLCULO (LÓGICA FINANCIERA)
# =============================================================================
def calcular_sueldo_liquido_a_bruto(liquido_objetivo, colacion, movilizacion, tipo_contrato, afp_nombre, salud_sistema, plan_uf_isapre):
    # Validar sueldo mínimo ético para el cálculo
    if liquido_objetivo < 300000:
        return {"Error": "El sueldo líquido es demasiado bajo para ser legal."}

    no_imponibles = colacion + movilizacion
    liquido_tributable_meta = liquido_objetivo - no_imponibles
    
    # Constantes
    TOPE_IMP_PESOS = IND["TOPE_AFP_UF"] * IND["UF"]
    TASAS_AFP = {"Capital": 11.44, "Cuprum": 11.44, "Habitat": 11.27, "PlanVital": 11.16, "Provida": 11.45, "Modelo": 10.58, "Uno": 10.46, "SIN AFP": 0.0}
    
    tasa_afp = TASAS_AFP.get(afp_nombre, 11.44) / 100
    tasa_salud_legal = 0.07
    
    # Iteración (Búsqueda Binaria)
    min_bruto = liquido_objetivo
    max_bruto = liquido_objetivo * 2.5
    
    resultado_final = None

    for _ in range(100):
        bruto_test = (min_bruto + max_bruto) / 2
        gratificacion = 0 
        # Aquí simplificamos para el ejemplo: Asumimos Bruto incluye gratificación si aplica
        # En una V45 podemos separar Base + Gratificación explícitamente
        
        base_imponible = min(bruto_test, TOPE_IMP_PESOS)
        
        dsc_afp = int(base_imponible * tasa_afp)
        dsc_salud = int(base_imponible * tasa_salud_legal)
        dsc_cesantia = int(base_imponible * 0.006) if tipo_contrato == "Indefinido" else 0
        
        # Ajuste Isapre
        adicional_isapre = 0
        if salud_sistema == "Isapre (UF)":
            valor_plan = int(plan_uf_isapre * IND["UF"])
            if valor_plan > dsc_salud:
                adicional_isapre = valor_plan - dsc_salud
                dsc_salud = valor_plan

        # Impuesto (Simplificado 2da Categoría)
        tributable = bruto_test - dsc_afp - dsc_salud - dsc_cesantia
        impuesto = 0
        # Tabla simplificada 2025
        if tributable > (13.5 * IND["UTM"]): impuesto = (tributable * 0.04) - (0.54 * IND["UTM"])
        if tributable > (30 * IND["UTM"]): impuesto = (tributable * 0.08) - (1.74 * IND["UTM"])
        impuesto = max(0, int(impuesto))
        
        liquido_calc = bruto_test - dsc_afp - dsc_salud - dsc_cesantia - impuesto
        
        if abs(liquido_calc - liquido_tributable_meta) < 100:
            resultado_final = {
                "Sueldo Base": int(bruto_test * 0.8), # Estimación Base vs Grat
                "Gratificación": int(bruto_test * 0.2),
                "Total Imponible": int(bruto_test),
                "No Imponibles": int(no_imponibles),
                "LÍQUIDO_FINAL": int(liquido_calc + no_imponibles),
                "AFP": dsc_afp, "Salud": dsc_salud, "AFC": dsc_cesantia, "Impuesto": impuesto,
                "Costo Empresa": int(bruto_test * 1.05 + no_imponibles) # Aprox SIS/Mutual
            }
            break
        
        if liquido_calc < liquido_tributable_meta:
            min_bruto = bruto_test
        else:
            max_bruto = bruto_test
            
    return resultado_final

# =============================================================================
# 6. GENERADORES DOCUMENTALES (Corregidos)
# =============================================================================
def generar_contrato_word(datos_fin, datos_emp, datos_trab, datos_cargo):
    if not LIBRARIES_OK: return None
    doc = Document()
    
    # Título
    doc.add_heading('CONTRATO DE TRABAJO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    texto = f"""
    En {datos_emp.get('ciudad', 'Santiago')}, a {datetime.now().strftime('%d de %B de %Y')}, entre {datos_emp.get('nombre', 'LA EMPRESA')}, RUT {datos_emp.get('rut', '')}, y don/ña {datos_trab.get('nombre', 'EL TRABAJADOR')}, RUT {datos_trab.get('rut', '')}, se acuerda:
    
    PRIMERO: El trabajador se desempeñará como {datos_cargo.get('cargo', 'Cargo no definido')}.
    
    SEGUNDO: La remuneración se desglosa en:
    - Sueldo Base: {fmt(datos_fin.get('Sueldo Base', 0))}
    - Gratificación: {fmt(datos_fin.get('Gratificación', 0))}
    - Colación/Mov: {fmt(datos_fin.get('No Imponibles', 0))}
    
    TERCERO (Ley 40 Horas): La jornada se ajustará a la normativa vigente de reducción gradual.
    CUARTO (Ley Karin): Se incorpora el protocolo de prevención de acoso y violencia.
    """
    doc.add_paragraph(texto)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

def generar_perfil_robusto(cargo, rubro):
    """Genera un perfil estructurado (Simulación IA)"""
    return {
        "titulo": cargo,
        "objetivo": f"Liderar procesos de {cargo} en el rubro {rubro}.",
        "funciones": ["Gestión operativa diaria", "Reportes a gerencia", "Cumplimiento normativo"],
        "requisitos": ["Experiencia 3+ años", "Manejo de ERP", "Título profesional"],
        "competencias": ["Liderazgo", "Proactividad"]
    }

# =============================================================================
# 7. INTERFAZ GRÁFICA (FRONTEND)
# =============================================================================
# Sidebar
with st.sidebar:
    st.header("Configuración")
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
    st.session_state.empresa['nombre'] = st.text_input("Nombre Empresa", st.session_state.empresa['nombre'])

st.title("🚀 HR Suite V44: Edición CTO")

tab1, tab2, tab3 = st.tabs(["💰 Calculadora", "📂 Carga Masiva Real", "📋 Perfil Cargo"])

# --- TAB 1: CALCULADORA ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido a Pagar", value=800000, step=10000)
        col = st.number_input("Colación + Movilización", value=60000)
    with c2:
        afp = st.selectbox("AFP", ["Modelo", "Capital", "Habitat", "PlanVital", "Provida", "Uno"])
        sal = st.radio("Salud", ["Fonasa", "Isapre (UF)"])
        plan = st.number_input("Valor Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("Calcular Nómina"):
        res = calcular_sueldo_liquido_a_bruto(liq, col, 0, "Indefinido", afp, sal, plan)
        if "Error" in res:
            st.error(res["Error"])
        else:
            st.session_state.calculo_actual = res
            st.success("¡Cálculo Exitoso!")
            m1, m2, m3 = st.columns(3)
            m1.metric("Base Imponible", fmt(res['Total Imponible']))
            m2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']))
            m3.metric("Costo Empresa", fmt(res['Costo Empresa']))
            
            # Tabla detalle
            df_show = pd.DataFrame({
                "Concepto": ["Sueldo Base", "Gratificación", "AFP", "Salud", "Impuesto"],
                "Monto": [res['Sueldo Base'], res['Gratificación'], -res['AFP'], -res['Salud'], -res['Impuesto']]
            })
            st.dataframe(df_show)

# --- TAB 2: MASIVO ---
with tab2:
    st.header("Generador Masivo Inteligente")
    st.info("Sube un Excel con columnas: NOMBRE, RUT, CARGO, SUELDO_BASE")
    
    # Generar plantilla descargable
    df_plantilla = pd.DataFrame([{"NOMBRE": "Juan Perez", "RUT": "1-9", "CARGO": "Junior", "SUELDO_BASE": 500000}])
    
    # Botón descarga plantilla
    buffer_plantilla = io.BytesIO()
    with pd.ExcelWriter(buffer_plantilla, engine='xlsxwriter') as writer: df_plantilla.to_excel(writer, index=False)
    st.download_button("Descargar Plantilla Excel", buffer_plantilla.getvalue(), "plantilla_carga.xlsx")
    
    uploaded_file = st.file_uploader("Sube tu Excel lleno aquí", type="xlsx")
    
    if uploaded_file and st.button("PROCESAR LOTE"):
        df = pd.read_excel(uploaded_file)
        zip_buffer = io.BytesIO()
        log_errores = []
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            progress = st.progress(0)
            for i, row in df.iterrows():
                # VALIDACIÓN DE SEGURIDAD
                sueldo = row.get('SUELDO_BASE', 0)
                if sueldo < IND['SUELDO_MIN']:
                    log_errores.append(f"Fila {i}: Sueldo {sueldo} bajo el mínimo legal.")
                    continue
                
                # Mapeo de datos REALES del Excel
                d_fin = {"Sueldo Base": sueldo, "Gratificación": int(sueldo * 0.25), "No Imponibles": 50000}
                d_trab = {"nombre": str(row.get('NOMBRE')), "rut": str(row.get('RUT'))}
                d_cargo = {"cargo": str(row.get('CARGO'))}
                
                # Generar Word
                doc_io = generar_contrato_word(d_fin, st.session_state.empresa, d_trab, d_cargo)
                zf.writestr(f"Contrato_{d_trab['rut']}.docx", doc_io.getvalue())
                
                progress.progress((i + 1) / len(df))
        
        st.success("Proceso Terminado")
        if log_errores:
            st.warning("Algunos archivos no se generaron por errores:")
            st.write(log_errores)
            
        st.download_button("📦 Descargar Todos (ZIP)", zip_buffer.getvalue(), "Contratos_Masivos.zip", "application/zip")

# --- TAB 3: PERFIL ---
with tab3:
    st.header("Diseñador de Cargos")
    c_cargo = st.text_input("Nombre del Cargo", "Administrativo")
    c_rubro = st.selectbox("Industria", ["Minería", "Retail", "Tecnología", "Servicios"])
    
    if st.button("Generar Perfil"):
        # Aquí usamos la función que antes faltaba
        perfil = generar_perfil_robusto(c_cargo, c_rubro)
        
        st.markdown(f"### {perfil['titulo']}")
        st.info(perfil['objetivo'])
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Funciones:**")
            for f in perfil['funciones']: st.markdown(f"- {f}")
        with c2:
            st.markdown("**Requisitos:**")
            for r in perfil['requisitos']: st.markdown(f"- {r}")
