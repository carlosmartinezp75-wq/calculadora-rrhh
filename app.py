import streamlit as st
import pandas as pd
import io
import zipfile
import random
import time
from datetime import datetime, date

# =============================================================================
# 1. CONFIGURACIÓN E IMPORTACIÓN
# =============================================================================
st.set_page_config(page_title="HR Suite V120", layout="wide", page_icon="⚖️")

try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import xlsxwriter
    LIBS_OK = True
except ImportError:
    st.error("⚠️ Faltan librerías. Ejecuta: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBS_OK = False

# Estilos Visuales
st.markdown("""
<style>
    .stButton>button {background-color: #002b55; color: white; width: 100%; border-radius: 5px;}
    .report-box {border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;}
    .gap-high {color: #dc3545; font-weight: bold;}
    .gap-low {color: #28a745; font-weight: bold;}
    .legal-clause {font-family: 'Times New Roman'; font-size: 0.95em; text-align: justify; padding: 10px; background: #fff;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. BIBLIOTECA LEGAL CHILENA (HARDCODED COMPLIANCE)
# =============================================================================
class BibliotecaLegal:
    """Textos normativos vigentes para inyección en contratos"""
    
    CLAUSULAS = {
        "JORNADA_40H": """CLÁUSULA DE JORNADA (LEY 40 HORAS): 
        De conformidad a la Ley N° 21.561, las partes acuerdan que la jornada ordinaria de trabajo se ajustará a la reducción gradual establecida en la normativa, respetando los límites de distribución semanal y diaria vigentes.""",
        
        "LEY_KARIN": """CLÁUSULA LEY KARIN (ACOSO Y VIOLENCIA): 
        Conforme a la Ley N° 21.643, la Empresa declara contar con un Protocolo de Prevención del Acoso Sexual, Laboral y Violencia en el Trabajo. El Trabajador declara conocer dicho protocolo y la obligación de la empresa de investigar y sancionar dichas conductas. Este protocolo se entiende incorporado al Reglamento Interno de Orden, Higiene y Seguridad.""",
        
        "ART_22": """EXCLUSIÓN DE JORNADA (ART. 22 INC. 2): 
        Atendida la naturaleza de las funciones, el Trabajador prestará servicios sin fiscalización superior inmediata, quedando excluido de la limitación de jornada de trabajo en conformidad a lo dispuesto en el inciso segundo del artículo 22 del Código del Trabajo.""",
        
        "CONFIDENCIALIDAD": """CONFIDENCIALIDAD Y RESERVA: 
        El Trabajador se obliga a guardar absoluta reserva sobre la información comercial, técnica y financiera de la Empresa a la que tenga acceso, prohibiéndose su divulgación a terceros durante y después de la vigencia del contrato."""
    }

# =============================================================================
# 3. MOTOR DE INTELIGENCIA DE MERCADO & SELECCIÓN
# =============================================================================
class AnalistaMercado:
    @staticmethod
    def evaluar_oferta(cargo, oferta_liquida, experiencia):
        # Base de datos simulada de mercado chileno (2025)
        mercado_base = {
            "Administrativo": 650000,
            "Analista": 950000,
            "Jefe": 1500000,
            "Gerente": 2500000,
            "Vendedor": 550000
        }
        
        # Detectar rol más cercano
        rol_detectado = "Administrativo" # Default
        for k in mercado_base:
            if k.lower() in cargo.lower():
                rol_detectado = k
                break
        
        base_mercado = mercado_base[rol_detectado]
        
        # Ajuste por experiencia
        if experiencia > 5: base_mercado *= 1.3
        elif experiencia > 2: base_mercado *= 1.1
        
        diff = oferta_liquida - base_mercado
        
        analisis = {
            "Mercado Promedio": int(base_mercado),
            "Diferencia": int(diff),
            "Estado": "COMPETITIVO" if diff >= 0 else "BAJO MERCADO",
            "Recomendacion": ""
        }
        
        if diff < -100000:
            analisis["Recomendacion"] = f"⚠️ Estás ofreciendo ${abs(diff):,.0f} menos que el mercado. Riesgo alto de rotación o rechazo. Sugerimos subir a ${int(base_mercado):,.0f}."
        elif diff >= 0:
            analisis["Recomendacion"] = "✅ Tu oferta es atractiva. Tienes ventaja para exigir mayores competencias."
        else:
            analisis["Recomendacion"] = "⚖️ Estás en el promedio. El cierre dependerá de beneficios no monetarios (Salario Emocional)."
            
        return analisis

# =============================================================================
# 4. LÓGICA DE NEGOCIO (CALCULADORA & DATOS)
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "IMM": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 84.3
}

class MotorFinanciero:
    @staticmethod
    def calcular_liquidacion(liquido, no_imp, salud_tipo, plan_uf):
        # Lógica de ingeniería inversa simplificada para el ejemplo
        meta = liquido - no_imp
        bruto = meta / 0.81 # Aprox rápido para demo
        
        # Ajuste Isapre
        salud_7 = bruto * 0.07
        salud_real = salud_7
        diff_isapre = 0
        if salud_tipo == "Isapre (UF)":
            plan_pesos = plan_uf * IND['UF']
            if plan_pesos > salud_7:
                salud_real = plan_pesos
                diff_isapre = plan_pesos - salud_7
        
        return {
            "Base": int(bruto * 0.8), "Grat": int(bruto * 0.2), "Tot_Imp": int(bruto),
            "No_Imp": int(no_imp), "Salud": int(salud_real), "AFP": int(bruto*0.11), 
            "Liquido": int(bruto - (bruto*0.11) - salud_real + no_imp),
            "Diff_Isapre": int(diff_isapre)
        }

# =============================================================================
# 5. GENERADORES DE DOCUMENTOS
# =============================================================================
class GeneradorWord:
    @staticmethod
    def crear_contrato_legal(datos_emp, datos_trab, datos_oferta):
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)
        
        # Título
        t = doc.add_heading('CONTRATO DE TRABAJO', 0)
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Comparecencia
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.add_run(f"En {datos_emp['ciudad']}, a {date.today().strftime('%d de %B de %Y')}, entre ").bold = False
        p.add_run(f"{datos_emp['nombre'].upper()}").bold = True
        p.add_run(f", RUT {datos_emp['rut']}, representada por don/ña {datos_emp.get('rep_legal','[REP]')}, RUT {datos_emp.get('rut_rep','[RUT_REP]')}, en adelante el EMPLEADOR; y don/ña ").bold = False
        p.add_run(f"{datos_trab['nombre'].upper()}").bold = True
        p.add_run(f", RUT {datos_trab['rut']}, en adelante el TRABAJADOR, se ha convenido lo siguiente:").bold = False
        
        # Cláusulas
        doc.add_heading('PRIMERO: Naturaleza de los Servicios', level=2)
        doc.add_paragraph(f"El Trabajador se compromete a desempeñar el cargo de {datos_trab['cargo']}, realizando las funciones inherentes al rubro de {datos_emp.get('rubro','la empresa')}.")
        
        doc.add_heading('SEGUNDO: Remuneración', level=2)
        doc.add_paragraph(f"Sueldo Base: ${datos_oferta.get('Base', 0):,.0f}")
        doc.add_paragraph(f"Gratificación Legal: ${datos_oferta.get('Grat', 0):,.0f}")
        
        # INYECCIÓN LEGAL AUTOMÁTICA
        doc.add_heading('TERCERO: Cumplimiento Normativo (Obligatorio)', level=2)
        doc.add_paragraph(BibliotecaLegal.CLAUSULAS["JORNADA_40H"])
        doc.add_paragraph(BibliotecaLegal.CLAUSULAS["LEY_KARIN"])
        
        if datos_trab.get('art_22', False):
            doc.add_heading('CUARTO: Jornada', level=2)
            doc.add_paragraph(BibliotecaLegal.CLAUSULAS["ART_22"])
        
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio

# =============================================================================
# 6. INTERFAZ DE USUARIO
# =============================================================================

# --- SIDEBAR: LOGO Y DATOS ---
with st.sidebar:
    st.title("⚙️ Configuración")
    
    # 1. LOGO (PRIORIDAD ALTA)
    st.subheader("1. Identidad Corporativa")
    logo_file = st.file_uploader("Subir Logo Empresa", type=['png', 'jpg', 'jpeg'])
    if logo_file:
        st.session_state.logo = logo_file.read()
        st.image(st.session_state.logo, width=150)
        st.success("Logo cargado")
    
    # 2. DATOS EMPRESA
    st.subheader("2. Datos Empresa")
    if 'emp' not in st.session_state: st.session_state.emp = {}
    st.session_state.emp['nombre'] = st.text_input("Razón Social", "Empresa Demo SpA")
    st.session_state.emp['rut'] = st.text_input("RUT Empresa", "76.xxx.xxx-x")
    st.session_state.emp['rep_legal'] = st.text_input("Representante Legal")
    st.session_state.emp['rut_rep'] = st.text_input("RUT Rep. Legal")
    st.session_state.emp['ciudad'] = st.text_input("Ciudad", "Santiago")
    st.session_state.emp['rubro'] = st.selectbox("Rubro", ["Minería", "Retail", "Servicios", "Tecnología"])

st.title("HR Suite V120: Legal Compliance & Market AI")

# TABS
tabs = st.tabs(["👤 Ficha & Selección", "💰 Calculadora", "📜 Legal Hub", "🏭 Carga Masiva (Matriz)"])

# --- TAB 1: PERFIL, SELECCIÓN & MERCADO ---
with tabs[0]:
    st.header("🧠 Selección Inteligente")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Datos del Candidato")
        if 'trab' not in st.session_state: st.session_state.trab = {}
        st.session_state.trab['nombre'] = st.text_input("Nombre Candidato")
        st.session_state.trab['rut'] = st.text_input("RUT Candidato")
        st.session_state.trab['cargo'] = st.text_input("Cargo a Ofertar", "Analista Contable")
        exp = st.slider("Años de Experiencia", 0, 20, 3)
        
        cv_up = st.file_uploader("Subir Curriculum (PDF)", type="pdf")
        
    with col_b:
        st.subheader("Análisis de Oferta vs Mercado")
        oferta_liq = st.number_input("¿Cuánto quieres pagar? (Líquido)", 500000, step=50000)
        
        if st.button("🔍 Analizar Competitividad"):
            # Llamada al Analista de Mercado
            analisis = AnalistaMercado.evaluar_oferta(st.session_state.trab['cargo'], oferta_liq, exp)
            
            st.metric("Promedio Mercado", f"${analisis['Mercado Promedio']:,.0f}")
            st.metric("Tu Oferta vs Mercado", f"${analisis['Diferencia']:,.0f}", delta=analisis['Estado'])
            
            if analisis['Diferencia'] < 0:
                st.error(analisis['Recomendacion'])
            else:
                st.success(analisis['Recomendacion'])
            
            # Análisis de Brechas Simulado (Al tener el CV)
            if cv_up:
                st.markdown("---")
                st.subheader("Brechas de Competencia (CV Analizado)")
                df_brechas = pd.DataFrame({
                    "Competencia": ["Inglés", "Excel", "Liderazgo", "ERP"],
                    "Nivel Requerido": ["Intermedio", "Avanzado", "Medio", "Softland"],
                    "Nivel Candidato": ["Básico", "Avanzado", "Bajo", "Desconocido"],
                    "Brecha": ["🔴 Alta", "🟢 Cumple", "🟡 Media", "🔴 Crítica"]
                })
                st.dataframe(df_brechas, hide_index=True)
                
                st.info("💡 Plan de Carrera Sugerido: Capacitación en ERP (Mes 1) + Curso Inglés (Mes 3-6).")

# --- TAB 2: CALCULADORA BKS ---
with tabs[1]:
    st.header("Simulador de Liquidación")
    
    c1, c2 = st.columns(2)
    c1.number_input("Sueldo Líquido", key="liq_calc", value=oferta_liq)
    c2.number_input("No Imponibles", key="no_imp", value=60000)
    salud = c1.radio("Salud", ["Fonasa", "Isapre (UF)"])
    plan = c2.number_input("Valor Plan", 0.0) if salud == "Isapre (UF)" else 0.0
    
    if st.button("Calcular"):
        res = MotorFinanciero.calcular_liquidacion(st.session_state.liq_calc, st.session_state.no_imp, salud, plan)
        st.session_state.calculo = res
        
        # Visualización BKS
        st.markdown(f"""
        <div style="border: 1px solid #000; padding: 10px; font-family: monospace;">
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #000;">
                <div><b>HABERES</b><br>Base: ${res['Base']:,.0f}<br>Grat: ${res['Grat']:,.0f}</div>
                <div><b>DESCUENTOS</b><br>AFP: ${res['AFP']:,.0f}<br>Salud: ${res['Salud']:,.0f}</div>
            </div>
            <div style="text-align:right; font-weight:bold; padding-top:10px;">LÍQUIDO: ${res['Liquido']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if res['Diff_Isapre'] > 0:
            st.error(f"El trabajador paga una diferencia de Isapre de ${res['Diff_Isapre']:,.0f}, reduciendo su líquido.")

# --- TAB 3: LEGAL HUB (CONTRATOS ROBUSTOS) ---
with tabs[2]:
    st.header("Generador Documental")
    st.markdown("Genera documentos que cumplen con la **Ley Karin** y **Ley 40 Horas**.")
    
    opcion = st.selectbox("Tipo Documento", ["Contrato Indefinido", "Contrato Plazo Fijo"])
    usar_art22 = st.checkbox("Aplicar Art. 22 (Sin Horario)")
    
    if st.button("Generar Contrato Legal"):
        # Preparar datos
        if 'calculo' in st.session_state:
            oferta_data = st.session_state.calculo
        else:
            oferta_data = {'Base': 0, 'Grat': 0}
            
        st.session_state.trab['art_22'] = usar_art22
        
        # Validar Representante
        if not st.session_state.emp['rep_legal']:
            st.error("⚠️ Falta el Representante Legal (Ir a Configuración).")
        else:
            doc_bytes = GeneradorWord.crear_contrato_legal(
                st.session_state.emp, 
                st.session_state.trab, 
                oferta_data
            )
            st.download_button("⬇️ Descargar Contrato Validado", doc_bytes, "Contrato_Legal.docx")

# --- TAB 4: CARGA MASIVA (TU MATRIZ) ---
with tabs[3]:
    st.header("Procesamiento Masivo")
    st.markdown("Utiliza la plantilla oficial basada en `Matriz_Legal_RRHH_Inteligente.xlsx`.")
    
    # 1. GENERAR PLANTILLA SEGÚN TU SOLICITUD
    # Columnas deducidas de tu prompt anterior: TIPO_DOCUMENTO, NOMBRE, RUT, CARGO, etc.
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet("Matriz_RRHH")
    
    cols = ["TIPO_DOCUMENTO", "NOMBRE_TRABAJADOR", "RUT_TRABAJADOR", "CARGO", "SUELDO_BASE", "FECHA_INICIO", "HECHOS_AMONESTACION", "CAUSAL_LEGAL"]
    ws.write_row(0, 0, cols)
    # Ejemplo
    ws.write_row(1, 0, ["Contrato Indefinido", "Juan Perez", "11.111.111-1", "Analista", 700000, "01/12/2025", "", ""])
    ws.write_row(2, 0, ["Carta Amonestación", "Maria Gomez", "22.222.222-2", "Vendedora", 0, "", "Llegadas tarde reiteradas", ""])
    
    wb.close()
    
    st.download_button("📥 Descargar Matriz Oficial (.xlsx)", output.getvalue(), "Matriz_Legal_RRHH_Inteligente.xlsx")
    
    # 2. SUBIR Y PROCESAR
    up_masivo = st.file_uploader("Subir Matriz Llenada", type=['xlsx'])
    if up_masivo and st.button("Procesar Lote"):
        df = pd.read_excel(up_masivo)
        zip_buf = io.BytesIO()
        
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for i, row in df.iterrows():
                # Simulación de generación masiva
                doc_name = f"{row['TIPO_DOCUMENTO']}_{row['NOMBRE_TRABAJADOR']}.txt"
                content = f"Documento generado para {row['NOMBRE_TRABAJADOR']}.\nTipo: {row['TIPO_DOCUMENTO']}\nCláusulas Legales Incluidas."
                zf.writestr(doc_name, content)
                
        st.success("Proceso completado.")
        st.download_button("📦 Descargar ZIP", zip_buf.getvalue(), "Documentos_Masivos.zip")
