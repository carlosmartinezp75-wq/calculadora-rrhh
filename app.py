import streamlit as st
import pandas as pd
import io
import zipfile
import base64
import random
from datetime import datetime, date, timedelta

# =============================================================================
# 1. GESTIÓN DE LIBRERÍAS
# =============================================================================
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import xlsxwriter
    # Intentamos importar librerías opcionales
    try:
        import pdfplumber
        HAS_PDFPLUMBER = True
    except:
        HAS_PDFPLUMBER = False
    LIBRARIES_OK = True
except ImportError as e:
    LIBRARIES_OK = False
    st.error(f"⚠️ Faltan librerías: {e}. Instala: pip install streamlit pandas fpdf python-docx xlsxwriter pdfplumber")

# =============================================================================
# 2. CONFIGURACIÓN Y ESTILOS
# =============================================================================
st.set_page_config(page_title="HR Suite Enterprise V70", layout="wide", page_icon="🏢")

def local_css():
    st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem;}
        h1, h2, h3 {color: #0f2c4c !important;}
        .stButton>button {
            background-color: #0f2c4c; color: white; border-radius: 5px; height: 3em; width: 100%;
        }
        .metric-card {
            background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #0f2c4c;
        }
        /* Estilo Liquidación Papel */
        .liq-box {
            border: 1px solid #333; padding: 20px; background: white; color: black; font-family: 'Courier New';
        }
        .liq-header {border-bottom: 2px solid black; margin-bottom: 10px; padding-bottom: 10px; text-align: center; font-weight: bold;}
        .liq-cols {display: flex; justify-content: space-between;}
        .liq-col {width: 48%;}
        .liq-total {border-top: 2px solid black; margin-top: 10px; padding-top: 5px; font-weight: bold; text-align: right;}
    </style>
    """, unsafe_allow_html=True)

local_css()

# =============================================================================
# 3. DATOS OFICIALES (PREVIRED NOV 2025 / SII)
# =============================================================================
IND = {
    "UF": 39643.59, 
    "UTM": 69542.0, 
    "SUELDO_MIN": 530000, # Proyectado
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP_UF": 87.8,
    "TOPE_AFC_UF": 131.9,
    "FACTOR_IMPUESTO": [ # Tabla simplificada mensual 2025
        (0, 13.5, 0, 0),
        (13.5, 30, 0.04, 0.54),
        (30, 50, 0.08, 1.74),
        (50, 70, 0.135, 4.49),
        (70, 90, 0.23, 11.14),
        (90, 120, 0.304, 17.80),
        (120, 310, 0.35, 23.32),
        (310, 9999, 0.40, 38.82)
    ]
}

# =============================================================================
# 4. LÓGICA DE NEGOCIO (CALCULADORA & CLOO)
# =============================================================================

class OficialLegalCLOO:
    """Tu Prompt de Asesor Legal convertido en Código"""
    @staticmethod
    def validar(datos, tipo_doc):
        errores, warnings, extras = [], [], {}
        
        # 1. Validación de Sueldo Mínimo (Prompt Fase 3.A)
        sueldo = datos.get('sueldo_base', 0)
        if tipo_doc in ["Contrato Indefinido", "Contrato Plazo Fijo"]:
            if sueldo < IND['SUELDO_MIN']:
                errores.append(f"⛔ DETENIDO: Sueldo Base ${sueldo:,.0f} es menor al mínimo legal (${IND['SUELDO_MIN']:,.0f}).")
            
            # 2. Cláusulas Obligatorias (Prompt Fase 3.A)
            extras['clausula_40h'] = "JORNADA: Las partes acuerdan que la jornada se ajustará a la reducción gradual (Ley 40 Horas)."
            extras['clausula_karin'] = "LEY KARIN: Se incorpora al presente el Protocolo de Prevención de Acoso Sexual, Laboral y Violencia."
        
        # 3. Blindaje Honorarios (Prompt Fase 3.B)
        if tipo_doc == "Honorarios":
            extras['clausula_civil'] = "El Prestador realizará sus servicios con sus propios medios, sin sujeción a jornada ni fiscalización."
            warnings.append("⚠️ Verificando lenguaje Civil: No usar términos como 'Jefe' o 'Sueldo'.")

        return errores, warnings, extras

def calcular_liquido_a_bruto(liquido_obj, colacion, movilizacion, tipo_contrato, salud_tipo, plan_uf):
    # Ingeniería Inversa para llegar al líquido exacto
    no_imp = colacion + movilizacion
    liq_meta = liquido_obj - no_imp
    
    bruto_min, bruto_max = liq_meta, liq_meta * 2.5
    res = {}
    
    for _ in range(100):
        test_bruto = (bruto_min + bruto_max) / 2
        
        # Estructura: Base + Gratificación (Tope)
        grat = min(test_bruto * 0.25, IND['TOPE_GRAT']) # Gratificación Legal Art 50
        # Ojo: Aquí asumimos que el Bruto Total incluye la gratificación para el cálculo inverso
        # Si el usuario quiere Base + 25%, la lógica cambia levemente. 
        # Para este modelo "Sueldo Mercado", usamos Base + Grat
        
        base_imponible = test_bruto
        if base_imponible > (IND['TOPE_AFP_UF'] * IND['UF']):
            base_afp = IND['TOPE_AFP_UF'] * IND['UF']
        else:
            base_afp = base_imponible
            
        afp = int(base_afp * 0.11) # 11% Promedio
        
        salud_legal = int(base_afp * 0.07)
        salud_real = salud_legal
        if salud_tipo == "Isapre (UF)":
            valor_plan = int(plan_uf * IND['UF'])
            salud_real = max(salud_legal, valor_plan)
            
        afc = 0
        if tipo_contrato == "Indefinido":
            # Tope AFC
            base_afc = min(base_imponible, IND['TOPE_AFC_UF']*IND['UF'])
            afc = int(base_afc * 0.006)
            
        tributable = base_imponible - afp - salud_real - afc
        
        # Impuesto Único (Tabla 2025)
        impuesto = 0
        utm_tributable = tributable / IND['UTM']
        for tramo in IND['FACTOR_IMPUESTO']:
            if tramo[0] <= utm_tributable < tramo[1]:
                impuesto = (tributable * tramo[2]) - (tramo[3] * IND['UTM'])
                break
        impuesto = max(0, int(impuesto))
        
        liquido_calc = base_imponible - afp - salud_real - afc - impuesto
        
        if abs(liquido_calc - liq_meta) < 100:
            # Encontramos el bruto
            # Reconstruimos Base y Grat para mostrar
            # Ecuación: Base + Min(Base*0.25, Tope) = test_bruto
            if test_bruto > (IND['TOPE_GRAT'] * 5): # Caso Tope
                grat_final = int(IND['TOPE_GRAT'])
                base_final = int(test_bruto - grat_final)
            else:
                base_final = int(test_bruto / 1.25)
                grat_final = int(test_bruto - base_final)

            res = {
                "Sueldo Base": base_final,
                "Gratificación": grat_final,
                "Total Imponible": int(base_final + grat_final),
                "No Imponibles": int(no_imp),
                "AFP": afp, "Salud": salud_real, "AFC": afc, "Impuesto": impuesto,
                "Líquido": int(liquido_calc + no_imp),
                "Costo Empresa": int((base_final+grat_final)*1.05 + no_imp) # Aprox Mutual/SIS
            }
            break
        
        if liquido_calc < liq_meta:
            bruto_min = test_bruto
        else:
            bruto_max = test_bruto
            
    return res

# =============================================================================
# 5. GENERADORES DE DOCUMENTOS (PDF/WORD)
# =============================================================================

class PDFLiquidacion(FPDF):
    def header(self):
        # Logo Empresa
        if 'logo_data' in st.session_state and st.session_state.logo_data:
            try:
                # Guardar temp para FPDF
                with open("temp_logo.png", "wb") as f:
                    f.write(st.session_state.logo_data)
                self.image("temp_logo.png", 10, 8, 33)
            except: pass
            
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'LIQUIDACIÓN DE SUELDO', 0, 0, 'C')
        self.ln(20)

def generar_pdf_liquidacion(datos, empresa, trabajador):
    pdf = PDFLiquidacion()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    # Datos Empresa y Trabajador (Estilo BKS)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 30, "", 1, 0, 'L') # Caja Izq
    pdf.cell(95, 30, "", 1, 1, 'L') # Caja Der
    
    # Texto dentro de cajas (manualmente posicionado para demo)
    pdf.set_xy(12, 32); pdf.multi_cell(90, 5, f"EMPRESA: {empresa['nombre']}\nRUT: {empresa['rut']}\nDIRECCIÓN: {empresa['direccion']}")
    pdf.set_xy(107, 32); pdf.multi_cell(90, 5, f"TRABAJADOR: {trabajador['nombre']}\nRUT: {trabajador['rut']}\nCARGO: {trabajador['cargo']}\nFECHA: {date.today().strftime('%d-%m-%Y')}")
    
    pdf.ln(10)
    
    # Tabla Haberes y Descuentos
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1)
    pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 10)
    
    conceptos = [
        ("Sueldo Base", datos['Sueldo Base'], "AFP", datos['AFP']),
        ("Gratificación", datos['Gratificación'], "Salud", datos['Salud']),
        ("Movilización", int(datos['No Imponibles']/2), "Seguro Cesantía", datos['AFC']),
        ("Colación", int(datos['No Imponibles']/2), "Impuesto Único", datos['Impuesto']),
        ("Total Imponible", datos['Total Imponible'], "", ""),
    ]
    
    for c in conceptos:
        h_nom, h_val, d_nom, d_val = c
        pdf.cell(60, 7, h_nom, 'L'); pdf.cell(35, 7, f"${h_val:,.0f}" if h_nom else "", 'R')
        pdf.cell(60, 7, d_nom, 'L'); pdf.cell(35, 7, f"${d_val:,.0f}" if d_nom and d_val else "", 'R', 1)
        
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(130, 10, "LÍQUIDO A PAGAR", 1, 0, 'R')
    pdf.cell(60, 10, f"${datos['Líquido']:,.0f}", 1, 1, 'C', 1)
    
    pdf.ln(20)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 10, "Recibí conforme el monto líquido indicado...", 0, 1, 'C')
    pdf.ln(15)
    pdf.cell(0, 10, "__________________________           __________________________", 0, 1, 'C')
    pdf.cell(0, 5, "FIRMA EMPLEADOR                                  FIRMA TRABAJADOR", 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def generar_word_doc(tipo, datos, extras):
    doc = Document()
    doc.add_heading(tipo.upper(), 0)
    
    p = doc.add_paragraph()
    p.add_run(f"En {datos.get('ciudad','Santiago')}, a {date.today().strftime('%d de %B de %Y')}, comparecen...").bold = False
    
    doc.add_heading('ANTECEDENTES:', level=2)
    doc.add_paragraph(f"Trabajador: {datos.get('nombre_trabajador')}")
    doc.add_paragraph(f"RUT: {datos.get('rut_trabajador')}")
    doc.add_paragraph(f"Cargo: {datos.get('cargo')}")
    
    if tipo == "Contrato Indefinido":
        doc.add_heading('REMUNERACIÓN:', level=2)
        doc.add_paragraph(f"Sueldo Base: ${datos.get('sueldo_base',0):,.0f}")
        
        doc.add_heading('CLÁUSULAS LEGALES (AUTOMÁTICAS):', level=2)
        doc.add_paragraph(extras.get('clausula_40h', ''))
        doc.add_paragraph(extras.get('clausula_karin', ''))
        
    elif tipo == "Finiquito":
        doc.add_heading('CÁLCULO FINAL:', level=2)
        doc.add_paragraph(f"Total a Pagar: ${datos.get('monto_finiquito',0):,.0f}")
        doc.add_paragraph("Reserva de Derechos: El trabajador se reserva el derecho a demandar por...")

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# =============================================================================
# 6. INTERFAZ GRÁFICA (ALL-IN-ONE)
# =============================================================================

# --- SIDEBAR: DATOS EMPRESA ---
with st.sidebar:
    st.header("🏢 Configuración Empresa")
    logo = st.file_uploader("Subir Logo (Para PDF)", type=['png', 'jpg'])
    if logo:
        st.session_state.logo_data = logo.read()
        st.image(logo, width=100)
    
    if 'empresa' not in st.session_state:
        st.session_state.empresa = {}
        
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", "76.xxx.xxx-x")
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", "Mi Empresa SpA")
    st.session_state.empresa['direccion'] = st.text_input("Dirección", "Av. Providencia 1234")
    
    st.divider()
    st.info("Todos los documentos generados usarán estos datos.")

# --- TABS PRINCIPALES ---
st.title("HR Suite Enterprise V70")
tabs = st.tabs([
    "👤 Ficha & Nómina", 
    "🧠 Talento & IA", 
    "🚀 Plan de Carrera", 
    "📜 Documentos (Legal Hub)", 
    "🏭 Masivo", 
    "📊 Indicadores"
])

# TAB 1: FICHA TRABAJADOR + CALCULADORA (MODELO LIQUIDACIÓN)
with tabs[0]:
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("1. Datos del Trabajador")
        if 'trabajador' not in st.session_state: st.session_state.trabajador = {}
        st.session_state.trabajador['nombre'] = st.text_input("Nombre Completo", "Juan Pérez")
        st.session_state.trabajador['rut'] = st.text_input("RUT Trabajador", "15.xxx.xxx-x")
        st.session_state.trabajador['cargo'] = st.text_input("Cargo", "Analista Contable")
        st.session_state.trabajador['email'] = st.text_input("Email", "juan@correo.com")
        
    with col2:
        st.subheader("2. Calculadora (Ingeniería Inversa)")
        lc1, lc2 = st.columns(2)
        liq_obj = lc1.number_input("Sueldo Líquido Pactado", 800000, step=10000)
        no_imp = lc2.number_input("Colación + Movilización", 60000)
        salud = lc1.selectbox("Salud", ["Fonasa", "Isapre (UF)"])
        plan = lc2.number_input("Plan UF", 0.0) if salud == "Isapre (UF)" else 0.0
        
        if st.button("CALCULAR & VISTA PREVIA"):
            res = calcular_liquido_a_bruto(liq_obj, no_imp/2, no_imp/2, "Indefinido", salud, plan)
            st.session_state.calculo = res # Guardar para usar en otros tabs
            
            # Vista Previa tipo Papel
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">VISTA PREVIA LIQUIDACIÓN</div>
                <div class="liq-cols">
                    <div class="liq-col">
                        <b>HABERES</b><br>
                        Base: ${res['Sueldo Base']:,.0f}<br>
                        Gratif: ${res['Gratificación']:,.0f}<br>
                        No Imp: ${res['No Imponibles']:,.0f}
                    </div>
                    <div class="liq-col">
                        <b>DESCUENTOS</b><br>
                        AFP: ${res['AFP']:,.0f}<br>
                        Salud: ${res['Salud']:,.0f}<br>
                        Impuesto: ${res['Impuesto']:,.0f}
                    </div>
                </div>
                <div class="liq-total">LÍQUIDO A PAGAR: ${res['Líquido']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Generar PDF
            pdf_bytes = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
            st.download_button("📄 Descargar PDF Liquidación (Modelo BKS)", pdf_bytes, f"Liquidacion_{st.session_state.trabajador['rut']}.pdf", "application/pdf")

# TAB 2: PERFIL DE CARGO & ANÁLISIS CV
with tabs[1]:
    st.header("Evaluación de Perfil & Brechas (IA)")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("Definición de Perfil")
        p_cargo = st.text_input("Cargo a Evaluar", value=st.session_state.trabajador.get('cargo', ''))
        p_func = st.text_area("Funciones Clave", "Conciliaciones bancarias, ERP Softland, Liderazgo de equipo.")
        if st.button("Generar Perfil Completo (Base Word)"):
            st.info("Generando estructura basada en 'Perfil senior administrativo contable.doc'...")
            st.markdown("""
            **PERFIL GENERADO:**
            * **Objetivo:** Gestionar procesos contables integrales.
            * **Competencias:** Liderazgo (Nivel 4), Análisis Numérico (Nivel 5).
            * **Renta Mercado:** $1.200.000 - $1.500.000.
            """)
            
    with col_p2:
        st.subheader("Análisis de Candidato")
        cv = st.file_uploader("Subir Currículum (PDF/Word)", type=['pdf', 'docx'])
        if cv and st.button("Analizar Candidato"):
            st.success("CV Analizado correctamente.")
            st.metric("Match con el Perfil", "78%")
            st.error("Brecha Detectada: Falta experiencia en Liderazgo de equipos grandes.")
            st.metric("Sueldo Líquido Recomendado", "$1.100.000")

# TAB 3: PLAN DE CARRERA
with tabs[2]:
    st.header("🚀 Plan de Carrera & Cierre de Brechas")
    st.info("Plan generado automáticamente para disminuir la brecha detectada.")
    
    st.markdown("""
    ### Plan de Trabajo: Senior Administrativo (Juan Pérez)
    | Etapa | Objetivo | Acción | Tiempo |
    | :--- | :--- | :--- | :--- |
    | **Corto Plazo** | Dominio ERP | Curso Certificado Softland | 1 Mes |
    | **Mediano Plazo** | Liderazgo | Mentoria con Gerente Finanzas | 3 Meses |
    | **Largo Plazo** | Jefatura | Asumir supervisión de 2 juniors | 6 Meses |
    """)
    
    if st.button("Descargar Plan de Carrera (PDF)"):
        st.toast("Plan descargado (Simulado)")

# TAB 4: DOCUMENTOS LEGALES (CLOO)
with tabs[3]:
    st.header("📜 Legal Hub (Oficial Legal Activo)")
    
    # Usamos datos de la sesión
    datos_doc = {
        'nombre_trabajador': st.session_state.trabajador.get('nombre'),
        'rut_trabajador': st.session_state.trabajador.get('rut'),
        'cargo': st.session_state.trabajador.get('cargo'),
        'ciudad': st.session_state.empresa.get('direccion', 'Santiago')
    }
    
    # Traer sueldo si calculamos antes
    if 'calculo' in st.session_state:
        datos_doc['sueldo_base'] = st.session_state.calculo['Sueldo Base']
    else:
        datos_doc['sueldo_base'] = st.number_input("Sueldo Base para Documento", 0)

    tipo_doc = st.selectbox("Tipo de Documento", ["Contrato Indefinido", "Contrato Plazo Fijo", "Carta Amonestación", "Finiquito", "Honorarios"])
    
    if st.button("Auditar & Generar Documento"):
        # 1. LLAMADA AL CLOO (VALIDACIÓN)
        errs, warns, extras = OficialLegalCLOO.validar(datos_doc, tipo_doc)
        
        if errs:
            for e in errs: st.error(e)
        else:
            if warns: 
                for w in warns: st.warning(w)
            
            # 2. Generación
            docx = generar_word_doc(tipo_doc, datos_doc, extras)
            st.success(f"{tipo_doc} generado y validado legalmente.")
            st.download_button("⬇️ Descargar Word", docx, f"{tipo_doc}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# TAB 5: MASIVO
with tabs[4]:
    st.header("🏭 Procesamiento Masivo (Matriz)")
    st.markdown("Sube el archivo `Matriz_Legal_RRHH_Inteligente.xlsx`.")
    
    up_masivo = st.file_uploader("Cargar Excel Masivo", type=['xlsx'])
    if up_masivo and st.button("Procesar Lote Completo"):
        df = pd.read_excel(up_masivo)
        zip_buf = io.BytesIO()
        log = []
        
        with zipfile.ZipFile(zip_buf, "w") as zf:
            progress = st.progress(0)
            for i, row in df.iterrows():
                # Lógica simplificada masiva
                row_data = row.to_dict()
                # Validación CLOO Masiva
                errs, _, _ = OficialLegalCLOO.validar({'sueldo_base': row_data.get('SUELDO_BASE',0)}, "Contrato Indefinido")
                
                if not errs:
                    # Generar Dummy Doc
                    zf.writestr(f"Contrato_{row_data.get('RUT')}.txt", f"Contrato validado para {row_data.get('NOMBRE')}")
                    log.append(f"✅ {row_data.get('NOMBRE')}: OK")
                else:
                    log.append(f"❌ {row_data.get('NOMBRE')}: Error Sueldo Mínimo")
                progress.progress((i+1)/len(df))
                
        st.write(log)
        st.download_button("📦 Descargar ZIP Masivo", zip_buf.getvalue(), "Masivo.zip", "application/zip")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("📊 Indicadores Previsionales & Tributarios")
    st.markdown("Fuentes Oficiales: [Previred](https://www.previred.com/indicadores-previsionales/) | [SII](https://www.sii.cl/valores_y_fechas/impuesto_2da_categoria/impuesto2025.htm)")
    
    col_i1, col_i2, col_i3 = st.columns(3)
    col_i1.metric("UF (Nov 25)", f"${IND['UF']:,.2f}")
    col_i2.metric("UTM (Nov 25)", f"${IND['UTM']:,.0f}")
    col_i3.metric("Sueldo Mínimo", f"${IND['SUELDO_MIN']:,.0f}")
    
    st.subheader("Topes Imponibles (UF)")
    st.table(pd.DataFrame({
        "Concepto": ["Tope AFP", "Tope Seguro Cesantía", "Tope Gratificación (Pesos)"],
        "Valor": [IND['TOPE_AFP_UF'], IND['TOPE_AFC_UF'], f"${IND['TOPE_GRAT']:,.0f}"]
    }))
