import streamlit as st
import pandas as pd
import io
import zipfile
import base64
from datetime import datetime, date

# =============================================================================
# 1. GESTIÓN DE LIBRERÍAS
# =============================================================================
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    import xlsxwriter
    LIBRARIES_OK = True
except ImportError as e:
    st.error(f"⚠️ Error Crítico: Faltan librerías. Instala: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBRARIES_OK = False

# =============================================================================
# 2. CONFIGURACIÓN Y ESTILOS (UX/UI para Terceros)
# =============================================================================
st.set_page_config(page_title="HR Legal Suite SaaS", layout="wide", page_icon="⚖️")

def cargar_estilos():
    st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        h1, h2, h3 {color: #003366 !important;}
        .stButton>button {
            background-color: #003366; color: white; border-radius: 4px; height: 3em; width: 100%; font-weight: bold;
        }
        .stButton>button:hover {background-color: #004080;}
        
        /* Cajas de Alerta Legal */
        .legal-warning {
            padding: 15px; border-left: 5px solid #ff4b4b; background-color: #ffe6e6; color: #990000; margin-bottom: 10px;
        }
        .legal-success {
            padding: 15px; border-left: 5px solid #28a745; background-color: #e6ffec; color: #155724; margin-bottom: 10px;
        }
        
        /* Simulación Liquidación */
        .paper-sheet {
            background: white; border: 1px solid #ccc; padding: 25px; 
            font-family: 'Courier New', monospace; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: #333;
        }
        .paper-header {text-align: center; border-bottom: 2px solid #333; margin-bottom: 15px; font-weight: bold;}
        .paper-row {display: flex; justify-content: space-between; border-bottom: 1px dotted #ddd; padding: 4px 0;}
    </style>
    """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 3. DATOS OFICIALES CHILE (NOV 2025)
# =============================================================================
IND = {
    "UF": 39643.59, 
    "UTM": 69542.0, 
    "SUELDO_MIN": 530000, 
    "TOPE_GRAT": (4.75 * 530000)/12, # Tope mensual gratificación
    "TOPE_AFP": 87.8, # UF
    "TOPE_AFC": 131.9, # UF
    "FACTOR_IMPUESTO": [ # Tabla simplificada 2025 (Mensual)
        (0, 13.5, 0, 0),
        (13.5, 30, 0.04, 0.54),
        (30, 50, 0.08, 1.74),
        (50, 70, 0.135, 4.49),
        (70, 90, 0.23, 11.14),
        (90, 120, 0.304, 17.80)
    ]
}

# =============================================================================
# 4. MOTOR LÓGICO (Backend)
# =============================================================================

class CalculadoraSueldos:
    @staticmethod
    def calcular_bruto_desde_liquido(liquido_objetivo, colacion, movilizacion):
        """
        Paso 1: Calcula el Bruto Base asumiendo Salud 7% (Escenario Estándar).
        Usamos esto para definir el contrato.
        """
        no_imp = colacion + movilizacion
        target_tributable = liquido_objetivo - no_imp
        
        # Iteración binaria
        min_bruto, max_bruto = target_tributable, target_tributable * 2.3
        
        for _ in range(100):
            test_bruto = (min_bruto + max_bruto) / 2
            
            # Estructura: Base + Gratificación (Tope)
            grat = min(test_bruto * 0.25, IND['TOPE_GRAT'])
            # Ecuación inversa: Si asumimos que test_bruto es el Total Imponible
            if test_bruto > (IND['TOPE_GRAT'] * 5):
                base_real = test_bruto - IND['TOPE_GRAT']
            else:
                base_real = test_bruto / 1.25
            
            # Descuentos Estándar (7% salud)
            tope_afp_pesos = IND['TOPE_AFP'] * IND['UF']
            base_imp = min(test_bruto, tope_afp_pesos)
            
            afp = int(base_imp * 0.11) # 11% Promedio
            salud = int(base_imp * 0.07) # 7% Legal
            afc = int(min(test_bruto, IND['TOPE_AFC']*IND['UF']) * 0.006)
            
            tributable = test_bruto - afp - salud - afc
            
            # Impuesto
            impuesto = 0
            utm = tributable / IND['UTM']
            for tr in IND['FACTOR_IMPUESTO']:
                if tr[0] <= utm < tr[1]:
                    impuesto = (tributable * tr[2]) - (tr[3] * IND['UTM'])
                    break
            
            liq_calc = test_bruto - afp - salud - afc - impuesto
            
            if abs(liq_calc - target_tributable) < 500:
                return int(base_real), int(grat), int(test_bruto)
            
            if liq_calc < target_tributable:
                min_bruto = test_bruto
            else:
                max_bruto = test_bruto
                
        return int(base_real), int(grat), int(test_bruto)

    @staticmethod
    def calcular_liquidacion_real(sueldo_base, gratificacion, colacion, movilizacion, salud_tipo, plan_uf):
        """
        Paso 2: Toma el Bruto pactado y aplica la realidad de la Isapre.
        Si Plan > 7%, el líquido baja.
        """
        total_imponible = sueldo_base + gratificacion
        no_imp = colacion + movilizacion
        
        # Topes
        base_calc = min(total_imponible, IND['TOPE_AFP'] * IND['UF'])
        
        # Descuentos
        afp = int(base_calc * 0.11)
        salud_legal_7 = int(base_calc * 0.07)
        
        salud_descuento = salud_legal_7
        diferencia_isapre = 0
        glosa = ""
        
        if salud_tipo == "Isapre (UF)":
            valor_plan_pesos = int(plan_uf * IND['UF'])
            if valor_plan_pesos > salud_legal_7:
                salud_descuento = valor_plan_pesos
                diferencia_isapre = valor_plan_pesos - salud_legal_7
                glosa = f"NOTA: El plan de Isapre ({plan_uf} UF) excede el 7% legal. La diferencia (${diferencia_isapre:,.0f}) disminuye el líquido a percibir."
        
        afc = int(min(total_imponible, IND['TOPE_AFC']*IND['UF']) * 0.006)
        
        # Impuesto (Sobre la base tributable real)
        tributable = total_imponible - afp - salud_descuento - afc
        impuesto = 0
        utm = tributable / IND['UTM']
        for tr in IND['FACTOR_IMPUESTO']:
            if tr[0] <= utm < tr[1]:
                impuesto = (tributable * tr[2]) - (tr[3] * IND['UTM'])
                break
        impuesto = max(0, int(impuesto))
        
        liquido_final = total_imponible - afp - salud_descuento - afc - impuesto + no_imp
        
        return {
            "Sueldo Base": sueldo_base,
            "Gratificación": gratificacion,
            "Total Imponible": total_imponible,
            "AFP": afp,
            "Salud": salud_descuento,
            "AFC": afc,
            "Impuesto": impuesto,
            "No Imponibles": no_imp,
            "Líquido Final": liquido_final,
            "Glosa": glosa
        }

# =============================================================================
# 5. GENERADORES DE DOCUMENTOS (PDF & WORD)
# =============================================================================

class PDFGenerator(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'DOCUMENTO OFICIAL RRHH', 0, 1, 'R')
        self.line(10, 20, 200, 20)
        self.ln(10)

def generar_perfil_pdf(cargo, funciones, competencias, renta):
    pdf = PDFGenerator()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"PERFIL DE CARGO: {cargo.upper()}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. OBJETIVO DEL CARGO", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 7, f"Ejecutar y supervisar las actividades relacionadas con {cargo}, asegurando el cumplimiento de la normativa vigente.")
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. FUNCIONES PRINCIPALES", 0, 1)
    pdf.set_font('Arial', '', 11)
    for f in funciones.split('\n'):
        if f.strip(): pdf.cell(0, 7, f"- {f.strip()}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "3. COMPETENCIAS & RENTA", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 7, f"Competencias Requeridas: {competencias}\nRenta Líquida Referencial: {renta}")
    
    return pdf.output(dest='S').encode('latin-1')

def generar_plan_carrera_pdf(nombre, cargo, brechas):
    pdf = PDFGenerator()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "PLAN DE DESARROLLO INDIVIDUAL", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Colaborador: {nombre}", 0, 1)
    pdf.cell(0, 10, f"Cargo Actual: {cargo}", 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(60, 10, "Brecha Detectada", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Acción Formativa", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Plazo", 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 10)
    # Datos simulados basados en el input
    pdf.cell(60, 10, "Manejo ERP", 1, 0)
    pdf.cell(60, 10, "Curso Certificado", 1, 0)
    pdf.cell(60, 10, "3 Meses", 1, 1)
    
    pdf.cell(60, 10, "Liderazgo", 1, 0)
    pdf.cell(60, 10, "Mentoria Interna", 1, 0)
    pdf.cell(60, 10, "6 Meses", 1, 1)
    
    return pdf.output(dest='S').encode('latin-1')

def generar_contrato_word(datos):
    doc = Document()
    doc.add_heading('CONTRATO DE TRABAJO', 0)
    
    p = doc.add_paragraph()
    p.add_run(f"En {datos.get('ciudad','Santiago')}, a {date.today().strftime('%d/%m/%Y')}, entre la empresa...").bold = False
    
    doc.add_heading('CLÁUSULAS ESENCIALES', level=2)
    doc.add_paragraph(f"1. CARGO: El trabajador se desempeñará como {datos.get('cargo')}.")
    doc.add_paragraph(f"2. REMUNERACIÓN: Sueldo Base de ${datos.get('sueldo_base',0):,.0f}.")
    
    # MOTOR LEGAL CHILENO (HARDCODED)
    doc.add_heading('CUMPLIMIENTO LEGAL (OBLIGATORIO)', level=2)
    doc.add_paragraph("LEY 40 HORAS: Las partes acuerdan que la jornada ordinaria de trabajo se ajustará a la reducción gradual establecida en la Ley N° 21.561, respetando los límites y distribución legal vigente.")
    doc.add_paragraph("LEY KARIN: Conforme a la Ley N° 21.643, la empresa declara contar con un Protocolo de Prevención del Acoso Sexual, Laboral y Violencia en el Trabajo, el cual se entiende incorporado al presente instrumento.")
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# =============================================================================
# 6. INTERFAZ GRÁFICA (ALL-IN-ONE SaaS)
# =============================================================================

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    st.header("⚙️ Configuración Global")
    
    if 'empresa' not in st.session_state: st.session_state.empresa = {}
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", "76.xxx.xxx-x")
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", "Mi Empresa SpA")
    
    st.divider()
    st.markdown("**Indicadores Hoy:**")
    st.metric("UF", f"${IND['UF']:,.2f}")
    st.metric("UTM", f"${IND['UTM']:,.0f}")

st.title("HR Legal Suite SaaS V80")

tabs = st.tabs(["💰 Calculadora Sueldos", "📄 Perfil & Talento", "📜 Legal Hub", "🏭 Procesos Masivos"])

# --- TAB 1: CALCULADORA (Lógica Isapre Corregida) ---
with tabs[0]:
    with st.expander("📘 Guía de Uso: Calculadora", expanded=False):
        st.markdown("""
        Esta herramienta realiza dos procesos:
        1. **Ingeniería Inversa:** Calcula el Sueldo Base necesario para llegar al Líquido que ofreces (bajo condiciones estándar).
        2. **Cálculo Real:** Si el trabajador tiene Isapre en UF, recalcula el líquido final. **Si el plan es caro, el líquido bajará.**
        """)

    col1, col2 = st.columns(2)
    with col1:
        liq_obj = st.number_input("1. ¿Qué Líquido quieres ofrecer?", min_value=400000, value=800000, step=10000)
        no_imp = st.number_input("2. Total Colación + Movilización", value=60000)
    
    with col2:
        salud_tipo = st.radio("3. Previsión de Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan_uf = st.number_input("Valor Plan (UF)", 0.0) if salud_tipo == "Isapre (UF)" else 0.0

    if st.button("CALCULAR LIQUIDACIÓN REAL"):
        # Paso 1: Obtener Estructura de Contrato
        base, grat, bruto_std = CalculadoraSueldos.calcular_bruto_desde_liquido(liq_obj, no_imp/2, no_imp/2)
        
        # Paso 2: Calcular Realidad (Con Isapre)
        res = CalculadoraSueldos.calcular_liquidacion_real(base, grat, no_imp/2, no_imp/2, salud_tipo, plan_uf)
        
        st.session_state.ultimo_calculo = res # Guardar en memoria
        
        # Mostrar Resultados
        if res['Glosa']:
            st.warning(res['Glosa'])
        
        st.markdown(f"""
        <div class="paper-sheet">
            <div class="paper-header">SIMULACIÓN DE LIQUIDACIÓN</div>
            <div class="paper-row"><span>Sueldo Base (Contrato):</span><span>${res['Sueldo Base']:,.0f}</span></div>
            <div class="paper-row"><span>Gratificación Legal:</span><span>${res['Gratificación']:,.0f}</span></div>
            <div class="paper-row"><span>Colación y Movilización:</span><span>${res['No Imponibles']:,.0f}</span></div>
            <hr>
            <div class="paper-row"><span>AFP (11% aprox):</span><span style="color:#b30000">-${res['AFP']:,.0f}</span></div>
            <div class="paper-row"><span>Salud ({'Isapre' if plan_uf > 0 else 'Fonasa'}):</span><span style="color:#b30000">-${res['Salud']:,.0f}</span></div>
            <div class="paper-row"><span>Seguro Cesantía:</span><span style="color:#b30000">-${res['AFC']:,.0f}</span></div>
            <div class="paper-row"><span>Impuesto Único:</span><span style="color:#b30000">-${res['Impuesto']:,.0f}</span></div>
            <br>
            <div style="font-size: 1.2em; font-weight: bold; text-align: right; color: #003366;">
                LÍQUIDO A PAGAR: ${res['Líquido Final']:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: PERFIL & TALENTO (PDFs Reales) ---
with tabs[1]:
    with st.expander("📘 Guía de Uso: Talento", expanded=False):
        st.markdown("Genera perfiles de cargo en PDF y Planes de Carrera para cerrar brechas.")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Generador de Perfil (PDF)")
        p_cargo = st.text_input("Nombre del Cargo", "Jefe de Operaciones")
        p_func = st.text_area("Funciones Principales", "Liderar equipo.\nControlar KPI.\nReportar a Gerencia.")
        
        if st.button("📄 Generar PDF Perfil"):
            pdf_bytes = generar_perfil_pdf(p_cargo, p_func, "Liderazgo, Excel Avanzado", "$1.2M - $1.5M")
            st.download_button("Descargar Perfil.pdf", pdf_bytes, f"Perfil_{p_cargo}.pdf", "application/pdf")
            
    with col_t2:
        st.subheader("Plan de Carrera (Cierre Brechas)")
        st.info("Simulación: Detectamos brecha en 'Manejo de ERP'.")
        if st.button("🚀 Crear Plan de Carrera PDF"):
            plan_bytes = generar_plan_carrera_pdf("Juan Perez", p_cargo, "Brechas")
            st.download_button("Descargar Plan_Carrera.pdf", plan_bytes, "Plan_Carrera.pdf", "application/pdf")

# --- TAB 3: LEGAL HUB (Validación Estricta) ---
with tabs[2]:
    with st.expander("📘 Guía de Uso: Documentos", expanded=False):
        st.markdown("Genera contratos individuales. El sistema inyectará **automáticamente** Ley Karin y 40 Horas.")

    st.subheader("Generación Unitaria de Contrato")
    
    # Usar datos del cálculo si existen
    def_base = 0
    if 'ultimo_calculo' in st.session_state:
        def_base = st.session_state.ultimo_calculo['Sueldo Base']
        st.success(f"Usando Sueldo Base calculado: ${def_base:,.0f}")
        
    l_nombre = st.text_input("Nombre Trabajador")
    l_base = st.number_input("Sueldo Base (Contrato)", value=def_base)
    l_cargo = st.text_input("Cargo Legal", "Administrativo")
    
    if st.button("Auditar y Crear Contrato"):
        # Validación Legal (CLOO)
        if l_base < IND['SUELDO_MIN']:
            st.markdown(f"""
            <div class="legal-warning">
                ⛔ <b>BLOQUEO LEGAL:</b> El sueldo base (${l_base:,.0f}) es inferior al Mínimo Legal (${IND['SUELDO_MIN']:,.0f}).<br>
                No se puede generar el documento. Por favor ajuste el monto.
            </div>
            """, unsafe_allow_html=True)
        else:
            doc_io = generar_contrato_word({'sueldo_base': l_base, 'cargo': l_cargo, 'ciudad': 'Santiago'})
            st.markdown(f"""
            <div class="legal-success">
                ✅ <b>VALIDACIÓN EXITOSA:</b><br>
                - Sueldo sobre el mínimo.<br>
                - Cláusula Ley 40 Horas: INYECTADA.<br>
                - Cláusula Ley Karin: INYECTADA.
            </div>
            """, unsafe_allow_html=True)
            st.download_button("⬇️ Descargar Contrato (Word)", doc_io, f"Contrato_{l_nombre}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# --- TAB 4: MASIVO (Descarga y Carga) ---
with tabs[3]:
    with st.expander("📘 Guía de Uso: Masivo", expanded=True):
        st.markdown("""
        1. **Descarga** la plantilla Excel vacía.
        2. Llénala con los datos de tus trabajadores.
        3. **Súbela** para que el sistema genere todos los contratos en un ZIP.
        """)
        
    # 1. Generador de Plantilla (Lo que faltaba)
    st.subheader("Paso 1: Obtener Plantilla")
    df_template = pd.DataFrame(columns=["NOMBRE", "RUT", "CARGO", "SUELDO_BASE", "CIUDAD"])
    buffer_tpl = io.BytesIO()
    with pd.ExcelWriter(buffer_tpl, engine='xlsxwriter') as writer:
        df_template.to_excel(writer, index=False)
    
    st.download_button("📥 Descargar Plantilla Matriz (.xlsx)", buffer_tpl.getvalue(), "Plantilla_Carga_RRHH.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    st.markdown("---")
    
    # 2. Carga y Proceso
    st.subheader("Paso 2: Procesar Lote")
    up_file = st.file_uploader("Subir Plantilla Completa", type=['xlsx'])
    
    if up_file and st.button("🏭 Generar Lote de Contratos"):
        try:
            df = pd.read_excel(up_file)
            zip_buffer = io.BytesIO()
            log = []
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                progress = st.progress(0)
                for i, row in df.iterrows():
                    # Validación Legal Masiva
                    sueldo = row.get('SUELDO_BASE', 0)
                    nombre = str(row.get('NOMBRE', f'Fila_{i}'))
                    
                    if sueldo < IND['SUELDO_MIN']:
                        log.append(f"❌ {nombre}: Omitido (Sueldo bajo mínimo)")
                        continue
                        
                    # Generar Doc
                    doc_bytes = generar_contrato_word({
                        'sueldo_base': sueldo, 
                        'cargo': row.get('CARGO'),
                        'ciudad': row.get('CIUDAD', 'Santiago')
                    })
                    zf.writestr(f"Contrato_{nombre}.docx", doc_bytes.getvalue())
                    log.append(f"✅ {nombre}: Generado")
                    
                    progress.progress((i+1)/len(df))
            
            st.success("Proceso Terminado")
            with st.expander("Ver Log de Auditoría"):
                st.write(log)
            
            st.download_button("📦 Descargar ZIP Contratos", zip_buffer.getvalue(), "Lote_Contratos.zip", "application/zip")
            
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
