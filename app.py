import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import random
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0. VALIDACIÓN DE ENTORNO Y LIBRERÍAS
# =============================================================================
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA
# =============================================================================
st.set_page_config(
    page_title="HR Suite Enterprise V37",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Estado (Persistencia de Datos)
# Esto asegura que la app no falle si faltan datos
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

# =============================================================================
# 2. ESTILOS VISUALES (CSS)
# =============================================================================
def cargar_estilos():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        try:
            with open(img, "rb") as f: b64 = base64.b64encode(f.read()).decode()
            css_fondo = f"""
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/png;base64,{b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
        except: pass
    else:
        css_fondo = """[data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);}"""

    st.markdown(f"""
        <style>
        {css_fondo}
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98); 
            padding: 2.5rem; 
            border-radius: 15px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }}
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        
        /* Botones */
        .stButton>button {{
            background-color: #004a99 !important;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            width: 100%;
            height: 3rem;
            text-transform: uppercase;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stButton>button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
        }}
        
        /* Cajas de Ayuda */
        .help-box {{
            background-color: #e3f2fd;
            border-left: 5px solid #004a99;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            font-size: 0.95rem;
        }}
        
        /* Liquidación Visual */
        .liq-box {{
            border: 1px solid #ccc; padding: 20px; background: #fff; font-family: 'Courier New', monospace;
            box-shadow: 5px 5px 15px #eee; margin-top: 15px;
        }}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 4px 0;}}
        .liq-total {{background: #e8f5e9; padding: 10px; font-weight: bold; font-size: 1.2em; border: 1px solid #2e7d32; margin-top: 20px; color: #1b5e20; text-align: right;}}
        
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px;}}
        
        #MainMenu, footer {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 3. FUNCIONES UTILITARIAS
# =============================================================================
def fmt(valor):
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0 # Fallback

# =============================================================================
# 4. GENERADORES DE ARCHIVOS (MOTOR DOCUMENTAL)
# =============================================================================

def generar_plantilla_excel():
    """Crea un Excel modelo para que el usuario sepa qué subir"""
    df = pd.DataFrame(columns=[
        "TIPO_DOCUMENTO", "NOMBRE_TRABAJADOR", "RUT_TRABAJADOR", "CARGO", 
        "SUELDO_BASE", "FECHA_INICIO", "EMAIL"
    ])
    df.loc[0] = ["Contrato", "Juan Perez", "12.345.678-9", "Analista", 800000, "2025-01-01", "juan@mail.com"]
    
    buffer = io.BytesIO()
    # Usamos ExcelWriter simple para máxima compatibilidad
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla')
    buffer.seek(0)
    return buffer

def crear_documento_word_masivo(tipo_doc, datos, empresa):
    """Genera un DOCX individual basado en una fila de Excel"""
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    # Encabezado
    doc.add_heading(str(tipo_doc).upper(), 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Datos Seguros (Evita errores si la columna no existe)
    def g(key): 
        # Busca la columna ignorando mayúsculas
        key_upper = key.upper()
        for col in datos.index:
            if str(col).upper() == key_upper:
                return str(datos[col])
        return "________________"

    # Cuerpo
    intro = f"""En {empresa.get('ciudad','Santiago')}, entre "{empresa.get('nombre','EMPRESA')}", RUT {empresa.get('rut','XX')}, y don/ña {g('NOMBRE_TRABAJADOR')}, RUT {g('RUT_TRABAJADOR')}, se acuerda:"""
    doc.add_paragraph(intro)
    
    if "CONTRATO" in str(tipo_doc).upper():
        doc.add_paragraph(f"1. CARGO: El trabajador se desempeñará como {g('CARGO')}.")
        doc.add_paragraph(f"2. RENTA: Sueldo Base de {fmt(g('SUELDO_BASE'))} más gratificación legal.")
        doc.add_paragraph(f"3. JORNADA: 44 Horas semanales.")
    elif "FINIQUITO" in str(tipo_doc).upper():
        doc.add_paragraph("1. CAUSAL: Se pone término a la relación laboral por necesidades de la empresa.")
        doc.add_paragraph("2. PAGO: El trabajador recibe a entera conformidad sus haberes.")
        
    doc.add_paragraph("\n\n\n__________________\nFIRMA EMPLEADOR\n\n__________________\nFIRMA TRABAJADOR")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def procesar_lote_masivo(df, empresa_data):
    zip_buffer = io.BytesIO()
    reporte = []
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                tipo = str(row.get('TIPO_DOCUMENTO', 'Contrato'))
                nombre = str(row.get('NOMBRE_TRABAJADOR', f'Trab_{idx}'))
                
                # Crear DOCX
                docx = crear_documento_word_masivo(tipo, row, empresa_data)
                
                # Añadir al ZIP
                clean_name = "".join([c for c in nombre if c.isalnum() or c==' ']).strip().replace(" ", "_")
                zf.writestr(f"{tipo}_{clean_name}.docx", docx.getvalue())
            except Exception as e:
                reporte.append(f"Error Fila {idx}: {str(e)}")
                
    zip_buffer.seek(0)
    return zip_buffer, reporte

# =============================================================================
# 5. MOTORES DE INTELIGENCIA DE NEGOCIO
# =============================================================================

def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    
    skills_map = {
        "Tecnología": ["Cloud Computing (AWS/Azure)", "Scrum/Agile", "Python/SQL", "Cybersecurity"],
        "Minería": ["Normativa Sernageomin", "Gestión de Activos", "Seguridad Industrial", "Lean Mining"],
        "Retail": ["E-commerce", "Logística Última Milla", "Customer Experience", "Visual Merchandising"],
        "Salud": ["Gestión Clínica", "Calidad Acreditación", "Bioestadística", "Normativa Minsal"],
        "Construcción": ["Autocad/BIM", "Control de Costos", "Prevención de Riesgos", "Gestión de Obras"],
        "Banca": ["Riesgo Financiero", "Compliance", "Normativa CMF", "Inversiones"]
    }
    
    hard_skills = skills_map.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "ERP", "Inglés"])
    
    return {
        "titulo": cargo.title(),
        "objetivo": f"Dirigir y controlar las operaciones de {cargo} en el sector {rubro}, asegurando KPIs y normativa.",
        "dependencia": "Gerencia General / Gerencia de Área",
        "nivel": "Profesional Senior / Jefatura",
        "funciones": [
            "Planificación estratégica y operativa del área.",
            "Control presupuestario (CAPEX/OPEX) y gestión de recursos.",
            "Liderazgo de equipos multidisciplinarios.",
            "Reportabilidad a Gerencia y stakeholders."
        ],
        "requisitos_duros": [
            "Título Profesional Universitario.",
            f"Experiencia mínima de 4-5 años en rubro {rubro}.",
            "Manejo de ERP (SAP/Oracle) y Office Avanzado.",
            f"Conocimientos: {', '.join(hard_skills[:2])}."
        ],
        "competencias": ["Liderazgo Transformacional", "Visión Estratégica", "Negociación", "Resiliencia"],
        "condiciones": ["Jornada Art. 22", "Modalidad Híbrida/Presencial", "Seguro Complementario"]
    }

def motor_analisis_cv(texto, perfil):
    # Análisis semántico simulado
    kws = [k.lower() for k in perfil['competencias'] + perfil['requisitos_duros']]
    txt = texto.lower()
    
    enc = list(set([k.title() for k in kws if k.split()[0] in txt]))
    fal = list(set([k.title() for k in kws if k.split()[0] not in txt]))
    
    score = int((len(enc) / len(kws)) * 100) + random.randint(10, 20)
    score = min(99, max(15, score))
    nivel = "Senior" if score > 75 else "Semi-Senior" if score > 45 else "Junior"
    
    return score, enc, fal, nivel

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# =============================================================================
# 6. CÁLCULO FINANCIERO
# =============================================================================

def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Habitat":1.27,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
    tasa_afc_emp = 0.024
    tasa_afc_trab = 0.006 if contrato == "Indefinido" and contrato != "Sueldo Empresarial" else 0.0
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8*uf)
        b_afc = min(tot_imp, 131.9*uf)
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        # Lógica Isapre Target (7%)
        legal_7 = int(b_prev * 0.07)
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04)
        if base_trib > 30*utm: imp = int((base_trib*0.08) - (1.74*utm))
        imp = max(0, imp)
        
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc_base - liq_meta) < 500:
            salud_real = legal_7
            adicional = 0
            warning = None
            
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * uf)
                if plan_pesos > legal_7:
                    salud_real = plan_pesos
                    adicional = plan_pesos - legal_7
                    warning = f"⚠️ Plan Isapre excede el 7%. Líquido baja en {fmt(adicional)}."
            
            liq_final = tot_imp - m_afp - salud_real - m_afc - imp + no_imp
            ap_sis, ap_mut, ap_afc_e = int(b_prev*0.0149), int(b_prev*0.0093), int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional, "Salud_Total": salud_real,
                "AFC": m_afc, "Impuesto": imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

# =============================================================================
# 7. INTERFAZ GRÁFICA PRINCIPAL
# =============================================================================

# SIDEBAR: DATOS MAESTROS
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 1. Configuración Empresa", expanded=True):
        st.caption("Estos datos son obligatorios para generar documentos legales.")
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Enterprise V37")
st.markdown("**Sistema Integral de Gestión de Personas y Contratos**")

tabs = st.tabs(["📂 Carga Masiva", "💰 Calculadora", "📋 Perfil Cargo", "🧠 Análisis CV", "🚀 Carrera", "📜 Legal Hub", "📊 Indicadores"])

# --- TAB 1: CARGA MASIVA ---
with tabs[0]:
    st.header("Procesamiento por Lotes")
    
    with st.expander("📘 Guía de Uso: Carga Masiva"):
        st.markdown("""
        **Función:** Generar múltiples contratos o finiquitos simultáneamente.
        **Pasos:**
        1. Descarga la plantilla Excel.
        2. Llena los datos de tus trabajadores.
        3. Sube el archivo y presiona 'Procesar'.
        4. Descarga el archivo ZIP con todos los documentos listos.
        """)
    
    # 1. Descarga Plantilla
    excel_plantilla = generar_plantilla_excel()
    st.download_button("⬇️ Descargar Plantilla Excel (.xlsx)", excel_plantilla, "Plantilla_Carga.xlsx")
    
    # 2. Subida y Proceso
    st.markdown("---")
    up_excel = st.file_uploader("Subir Nómina Completa", type="xlsx")
    
    if up_excel:
        if not st.session_state.empresa['rut']:
            st.warning("⚠️ Complete los Datos de Empresa en el menú lateral antes de procesar.")
        elif st.button("PROCESAR LOTE COMPLETO"):
            try:
                df = pd.read_excel(up_excel)
                zip_data, errs = procesar_lote_masivo(df, st.session_state.empresa)
                st.success(f"Procesamiento finalizado. {len(errs)} errores detectados.")
                if errs: st.error("\n".join(errs))
                st.download_button("⬇️ Descargar Documentos (.ZIP)", zip_data, "documentos_rrhh.zip", "application/zip")
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

# --- TAB 2: CALCULADORA ---
with tabs[1]:
    with st.expander("📘 Guía de Uso: Calculadora"):
        st.markdown("Calcula el sueldo bruto y costo empresa a partir de un **Líquido Objetivo**.")
    
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo ($)", value=1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000, format="%d"); mov = st.number_input("Movilización", 50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']))
            
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#f0f0f0;"><span><b>TOTAL IMPONIBLE:</b></span><span><b>{fmt(res['Total Imponible'])}</b></span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:red">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud Total:</span><span style="color:red">-{fmt(res['Salud_Total'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 3: PERFIL CARGO ---
with tabs[2]:
    with st.expander("📘 Guía de Uso: Perfiles"):
        st.markdown("Genera descripciones de cargo profesionales basadas en competencias por industria.")
        
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Jefe de Ventas")
    rubro = c2.selectbox("Rubro", ["Minería", "Tecnología", "Retail", "Salud", "Construcción", "Banca"])
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_robusto(cargo, rubro)
        st.session_state.perfil_actual = perf
        
        st.info(f"**Misión:** {perf['objetivo']}")
        
        c_a, c_b = st.columns(2)
        c_a.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c_b.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_duros']]))
        st.write(f"**Competencias:** {', '.join(perf['competencias'])}")

# --- TAB 4: ANÁLISIS CV ---
with tabs[3]:
    with st.expander("📘 Guía de Uso: Análisis CV"):
        st.markdown("Sube un CV en PDF. El sistema comparará las competencias del candidato contra el Perfil generado en la Pestaña 3.")
        
    if not LIBRARIES_OK: st.warning("Faltan librerías.")
    else:
        up = st.file_uploader("Subir CV", type="pdf")
        if up and st.session_state.perfil_actual:
            if st.button("ANALIZAR"):
                txt = leer_pdf(up)
                if txt:
                    an = motor_analisis_cv(txt, st.session_state.perfil_actual)
                    st.metric("Score de Ajuste", f"{an['score']}%")
                    st.info(f"Nivel Detectado: **{an['nivel']}**")
                    st.success(f"✅ Fortalezas: {', '.join(an['encontradas'])}")
                    st.error(f"⚠️ Brechas: {', '.join(an['faltantes'])}")
        elif not st.session_state.perfil_actual:
            st.warning("⚠️ Primero genera un perfil en la Pestaña 3.")

# --- TAB 5: CARRERA ---
with tabs[4]:
    with st.expander("📘 Guía de Uso: Carrera"):
        st.markdown("Muestra un plan de desarrollo profesional sugerido.")
    
    if st.session_state.cargo_actual:
        plan = generar_plan_carrera(st.session_state.cargo_actual, st.session_state.rubro_actual)
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### Corto Plazo"); c1.write("\n".join(plan['corto']))
        c2.markdown("#### Mediano Plazo"); c2.write("\n".join(plan['mediano']))
        c3.markdown("#### Largo Plazo"); c3.write("\n".join(plan['largo']))
    else: st.info("Defina un cargo primero.")

# --- TAB 6: LEGAL HUB ---
with tabs[5]:
    with st.expander("📘 Guía de Uso: Documentos Legales"):
        st.markdown("Genera contratos individuales o finiquitos. Requiere datos de empresa.")
        
    tipo = st.radio("Documento", ["Contrato de Trabajo", "Finiquito"], horizontal=True)
    
    if tipo == "Contrato de Trabajo":
        if st.session_state.calculo_actual and st.session_state.empresa['rut']:
            # Formulario rápido para datos faltantes del trabajador
            col_a, col_b = st.columns(2)
            nombre = col_a.text_input("Nombre Trabajador")
            rut = col_b.text_input("RUT Trabajador")
            
            if st.button("GENERAR CONTRATO"):
                # Crear diccionario temporal uniendo datos
                datos_fila = {
                    "NOMBRE_TRABAJADOR": nombre, "RUT_TRABAJADOR": rut, 
                    "CARGO": st.session_state.cargo_actual,
                    "SUELDO": st.session_state.calculo_actual['Sueldo Base']
                }
                docx = crear_documento_word_masivo("Contrato", datos_fila, st.session_state.empresa)
                st.download_button("Descargar Contrato", docx, "contrato.docx")
        else: st.warning("Calcule sueldo en Pestaña 2 y complete Datos Empresa.")

# --- TAB 7: INDICADORES ---
with tabs[6]:
    st.header("Indicadores Previred")
    st.info(f"UF: {fmt(uf_v)} | UTM: {fmt(utm_v)} | Sueldo Mín: $529.000")
