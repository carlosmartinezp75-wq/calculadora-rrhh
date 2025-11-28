import streamlit as st
import pandas as pd
import io
import zipfile
import random
import time
from datetime import datetime, date

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================
st.set_page_config(page_title="HR AI Suite V100", layout="wide", page_icon="🧬")

def load_css():
    st.markdown("""
    <style>
        h1, h2, h3 {color: #002b55;}
        .stButton>button {background-color: #002b55; color: white; border-radius: 6px;}
        .metric-box {padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9; text-align: center;}
        .alert-box {padding: 10px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 4px;}
        .isapre-diff {color: #dc3545; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

load_css()

# Gestión de Librerías
try:
    from fpdf import FPDF
    from docx import Document
    import xlsxwriter
    LIBS_OK = True
except ImportError as e:
    st.error(f"Faltan librerías: {e}. Instala: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBS_OK = False

# =============================================================================
# 2. MOTOR DE IA GENERATIVA (SIMULADOR AVANZADO)
# =============================================================================
class GenerativeAI:
    """
    Este módulo simula ser GPT-4. En producción, aquí conectaríamos 
    openai.ChatCompletion.create()
    """
    @staticmethod
    def generar_funciones(cargo):
        # En una integración real, aquí va la llamada a la API
        prompts = [
            f"Diseñar estrategias de {cargo} alineadas a la visión corporativa.",
            f"Supervisar KPIs operativos del área de {cargo}.",
            "Liderar equipos multidisciplinarios fomentando el clima laboral.",
            "Optimizar procesos mediante metodologías ágiles y control de gastos.",
            "Reportar estados de avance a la Gerencia General."
        ]
        return prompts

    @staticmethod
    def generar_plan_carrera(cargo, brecha):
        return f"""
        PLAN DE TRABAJO DETALLADO PARA: {cargo.upper()}
        
        DIAGNÓSTICO: Se detecta una brecha principal en '{brecha}'.
        
        FASE 1: NIVELACIÓN (Mes 1-2)
        - Acción: Curso intensivo de especialización en {brecha}.
        - KPI: Aprobar certificación con nota superior a 6.0.
        - Mentor: Gerente de Área.
        
        FASE 2: CONSOLIDACIÓN (Mes 3-5)
        - Acción: Liderar un proyecto piloto aplicando los conocimientos de {brecha}.
        - KPI: Reducción de tiempos operativos en un 15%.
        
        FASE 3: EXPANSIÓN (Mes 6+)
        - Acción: Capacitar a pares (rol de relator interno).
        - Objetivo: Asumir rol de Senior/Jefatura.
        """

# =============================================================================
# 3. DATOS MAESTROS & INDICADORES (CON LINKS)
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "IMM": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 84.3, "TOPE_AFC": 126.6,
    "SIS": 1.49, "MUTUAL_BASE": 0.93
}

# =============================================================================
# 4. MOTOR FINANCIERO (LÓGICA ISAPRE & EMPRESARIAL)
# =============================================================================
class CalculadoraSueldos:
    @staticmethod
    def calcular(liquido_obj, col, mov, tipo_contrato, salud_sistema, plan_uf):
        # 1. Ajustes Iniciales
        no_imp = col + mov
        meta_tributable = liquido_obj - no_imp
        
        # Tasas según contrato (Tu regla de negocio)
        if tipo_contrato == "Sueldo Empresarial":
            tasa_afp = 0.0 # No cotiza AFP
            tasa_afc_trab = 0.0
            tasa_afc_emp = 0.0 # AFC Empresa
            tasa_sis = IND["SIS"] / 100
            tasa_mutual = IND["MUTUAL_BASE"] / 100
        else:
            tasa_afp = 0.11 # Promedio Habitat/Capital
            tasa_sis = IND["SIS"] / 100
            tasa_mutual = IND["MUTUAL_BASE"] / 100
            if tipo_contrato == "Indefinido":
                tasa_afc_trab = 0.006
                tasa_afc_emp = 0.024
            else: # Plazo Fijo
                tasa_afc_trab = 0.0
                tasa_afc_emp = 0.03
        
        # 2. Ingeniería Inversa (Buscando el Bruto Base)
        # Asumimos Salud Legal (7%) para encontrar el contrato base
        bruto_encontrado = 0
        min_b, max_b = meta_tributable, meta_tributable * 2.5
        
        for _ in range(100):
            test_bruto = (min_b + max_b) / 2
            
            # Estructura Base vs Gratificación
            if tipo_contrato == "Sueldo Empresarial":
                # Generalmente no lleva gratificación legal o es distinta, 
                # pero usaremos la estructura estándar si no se especifica
                grat = 0 
                base = test_bruto
            else:
                if test_bruto > (IND["TOPE_GRAT"] * 5):
                    grat = IND["TOPE_GRAT"]
                    base = test_bruto - grat
                else:
                    base = test_bruto / 1.25
                    grat = test_bruto - base
            
            imponible = base + grat
            
            # Descuentos para iteración (Escenario Ideal 7%)
            top_afp_p = IND["TOPE_AFP"] * IND["UF"]
            afp_monto = int(min(imponible, top_afp_p) * tasa_afp)
            
            salud_legal = int(min(imponible, top_afp_p) * 0.07)
            
            top_afc_p = IND["TOPE_AFC"] * IND["UF"]
            afc_monto = int(min(imponible, top_afc_p) * tasa_afc_trab)
            
            tributable = imponible - afp_monto - salud_legal - afc_monto
            
            # Impuesto (Tabla 2025 simplificada)
            imp = 0
            if tributable > (13.5*IND["UTM"]): imp = (tributable*0.04) - (0.54*IND["UTM"])
            if tributable > (30*IND["UTM"]): imp = (tributable*0.08) - (1.74*IND["UTM"])
            imp = max(0, int(imp))
            
            liq_calc = imponible - afp_monto - salud_legal - afc_monto - imp
            
            if abs(liq_calc - meta_tributable) < 500:
                bruto_encontrado = test_bruto
                break
            
            if liq_calc < meta_tributable: min_b = test_bruto
            else: max_b = test_bruto
            
        # 3. Cálculo FINAL REAL (Aplicando Delta Isapre)
        # Recalculamos con el bruto encontrado pero aplicando el plan UF real
        base_final = int(base)
        grat_final = int(grat)
        tot_imp = base_final + grat_final
        
        afp_real = int(min(tot_imp, IND["TOPE_AFP"]*IND["UF"]) * tasa_afp)
        salud_7pct = int(min(tot_imp, IND["TOPE_AFP"]*IND["UF"]) * 0.07)
        
        salud_real = salud_7pct
        diff_isapre = 0
        glosa_salud = "Fonasa / Isapre Legal (7%)"
        
        if salud_sistema == "Isapre (UF)":
            valor_plan = int(plan_uf * IND["UF"])
            if valor_plan > salud_7pct:
                salud_real = valor_plan
                diff_isapre = valor_plan - salud_7pct
                glosa_salud = f"Isapre Pactada ({plan_uf} UF)"
        
        afc_real = int(min(tot_imp, IND["TOPE_AFC"]*IND["UF"]) * tasa_afc_trab)
        
        # El impuesto se calcula sobre el tributable legal (descontando salud TOTAL con tope 5.x UF aprox, 
        # pero para simplificar usaremos el descuento legal salud total permitido tributariamente)
        tributable_real = tot_imp - afp_real - salud_real - afc_real
        
        imp_real = 0
        if tributable_real > (13.5*IND["UTM"]): imp_real = (tributable_real*0.04) - (0.54*IND["UTM"])
        imp_real = max(0, int(imp_real))
        
        liquido_final = tot_imp - afp_real - salud_real - afc_real - imp_real + no_imp
        
        # Costos Empresa
        sis = int(tot_imp * tasa_sis)
        afc_emp = int(min(tot_imp, IND["TOPE_AFC"]*IND["UF"]) * tasa_afc_emp)
        mutual = int(tot_imp * tasa_mutual)
        
        return {
            "Base": base_final, "Grat": grat_final, "Tot_Imp": tot_imp, "No_Imp": no_imp,
            "AFP": afp_real, "Salud": salud_real, "AFC_Trab": afc_real, "Impuesto": imp_real,
            "Liquido": liquido_final,
            "Diff_Isapre": diff_isapre,
            "Glosa_Salud": glosa_salud,
            "Costo_Empresa": tot_imp + no_imp + sis + afc_emp + mutual
        }

# =============================================================================
# 5. GENERADORES DE DOCUMENTOS (REPOSITORIO)
# =============================================================================
class GestorDocumental:
    @staticmethod
    def generar_pdf_perfil_detallado(datos, funciones_ia):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"PERFIL DE CARGO: {datos['cargo'].upper()}", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "1. IDENTIFICACIÓN", 0, 1)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Empresa: {datos['empresa']}", 0, 1)
        pdf.cell(0, 8, f"Área: Operaciones / Administración", 0, 1)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "2. OBJETIVO DEL CARGO", 0, 1)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, f"El {datos['cargo']} tiene como propósito fundamental asegurar la continuidad operativa y el cumplimiento normativo de la organización.")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "3. FUNCIONES PRINCIPALES (Sugeridas por IA)", 0, 1)
        pdf.set_font("Arial", "", 11)
        for func in funciones_ia:
            pdf.multi_cell(0, 7, f"- {func}")
        
        return pdf.output(dest='S').encode('latin-1')

    @staticmethod
    def generar_excel_masivo_con_combos():
        # Generar Excel con validación de datos (Combo Boxes)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Carga_Masiva')
        
        # Encabezados
        headers = ['RUT', 'NOMBRE', 'CARGO', 'TIPO_CONTRATO', 'SUELDO_BASE', 'AFP', 'SALUD']
        worksheet.write_row('A1', headers)
        
        # Validaciones (Combo Boxes)
        worksheet.data_validation('D2:D100', {'validate': 'list', 'source': ['Indefinido', 'Plazo Fijo', 'Sueldo Empresarial']})
        worksheet.data_validation('F2:F100', {'validate': 'list', 'source': ['Capital', 'Habitat', 'Modelo', 'Uno', 'PlanVital', 'Provida']})
        worksheet.data_validation('G2:G100', {'validate': 'list', 'source': ['Fonasa', 'Isapre']})
        
        # Datos Ejemplo
        worksheet.write_row('A2', ['11.111.111-1', 'Juan Perez', 'Analista', 'Indefinido', 600000, 'Modelo', 'Fonasa'])
        
        workbook.close()
        return output.getvalue()

# =============================================================================
# 6. INTERFAZ GRÁFICA (UI)
# =============================================================================

# --- SIDEBAR: DATOS MAESTROS ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    st.title("Configuración Global")
    
    # Datos Empresa (Persistentes)
    if 'empresa' not in st.session_state: st.session_state.empresa = {}
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", "76.xxx.xxx-x")
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", "Empresa Demo SpA")
    st.session_state.empresa['logo'] = st.file_uploader("Logo Corporativo", type=['png', 'jpg'])
    
    st.divider()
    
    # Datos Trabajador (Potencial)
    st.subheader("Ficha Trabajador")
    if 'trab' not in st.session_state: st.session_state.trab = {}
    st.session_state.trab['nombre'] = st.text_input("Nombre Trabajador", "María González")
    st.session_state.trab['cargo'] = st.text_input("Cargo", "Jefe de Proyectos")

# --- CUERPO PRINCIPAL ---
st.title("HR Suite V100: AI & Legal Tech")

tabs = st.tabs(["💰 Calculadora & Liquidación", "🧠 Perfil & IA Generativa", "📜 Repositorio Legal", "🏭 Carga Masiva", "📊 Indicadores"])

# TAB 1: CALCULADORA (CON LOGICA ISAPRE/EMPRESARIAL)
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Parámetros Financieros")
        liq = st.number_input("Sueldo Líquido Objetivo", 800000, step=10000)
        no_imp = st.number_input("Total No Imponibles", 60000)
        contrato = st.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        
    with c2:
        st.subheader("Previsión")
        salud = st.radio("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan_uf = st.number_input("Valor Plan (UF)", 0.0) if salud == "Isapre (UF)" else 0.0

    if st.button("CALCULAR LIQUIDACIÓN REAL"):
        # Llamada al motor
        res = CalculadoraSueldos.calcular(liq, no_imp/2, no_imp/2, contrato, salud, plan_uf)
        st.session_state.calculo = res
        
        # Renderizado Visual
        st.write("---")
        k1, k2, k3 = st.columns(3)
        k1.metric("Sueldo Base", f"${res['Base']:,.0f}")
        k2.metric("Líquido Final", f"${res['Liquido']:,.0f}")
        k3.metric("Costo Empresa", f"${res['Costo_Empresa']:,.0f}")
        
        if res['Diff_Isapre'] > 0:
            st.markdown(f"""
            <div class="alert-box">
                ⚠️ <b>ATENCIÓN ISAPRE:</b> El plan pactado ({plan_uf} UF) excede el 7% legal en <b>${res['Diff_Isapre']:,.0f}</b>.<br>
                Este monto se descuenta del líquido objetivo, por lo que el trabajador recibirá menos de lo solicitado.
            </div>
            """, unsafe_allow_html=True)

        if contrato == "Sueldo Empresarial":
            st.info("ℹ️ Cálculo bajo modalidad 'Sueldo Empresarial': Sin cotización AFP.")

# TAB 2: PERFIL IA GENERATIVA
with tabs[1]:
    st.header("Generador de Perfiles (IA)")
    st.markdown("Genera funciones y planes de carrera descriptivos automáticamente.")
    
    cargo_ia = st.text_input("Cargo a Analizar", value=st.session_state.trab['cargo'])
    
    if st.button("✨ Generar Perfil con IA"):
        funciones = GenerativeAI.generar_funciones(cargo_ia)
        
        c_res1, c_res2 = st.columns(2)
        with c_res1:
            st.subheader("Funciones Sugeridas")
            for f in funciones:
                st.write(f"✅ {f}")
                
        with c_res2:
            st.subheader("Plan de Trabajo")
            plan = GenerativeAI.generar_plan_carrera(cargo_ia, "Gestión de ERP")
            st.text_area("Plan Detallado", plan, height=200)
            
        # Descarga PDF
        pdf_bytes = GestorDocumental.generar_pdf_perfil_detallado(
            {'cargo': cargo_ia, 'empresa': st.session_state.empresa['nombre']},
            funciones
        )
        st.download_button("Descargar Informe Perfil (PDF)", pdf_bytes, f"Perfil_{cargo_ia}.pdf", "application/pdf")

# TAB 3: REPOSITORIO LEGAL (MODELOS)
with tabs[2]:
    st.header("Repositorio de Documentos")
    
    opcion = st.selectbox("Seleccionar Modelo", ["Contrato Trabajo", "Carta Amonestación", "Finiquito"])
    
    if st.button("Previsualizar Modelo"):
        st.markdown(f"### Clausulas Legales para {opcion}")
        if opcion == "Contrato Trabajo":
            st.code("""
            CLÁUSULA JORNADA 40 HORAS:
            "La jornada de trabajo se ajustará a la reducción gradual establecida en la Ley 21.561..."
            
            CLÁUSULA LEY KARIN:
            "La empresa declara contar con el Protocolo de Prevención de Acoso Sexual, Laboral y Violencia..."
            """)
        elif opcion == "Finiquito":
            st.warning("Recuerda: El tope de indemnización por años de servicio es de 90 UF.")

    st.markdown("---")
    if st.button("Generar Documento Final (Word)"):
        doc = Document()
        doc.add_heading(opcion.upper(), 0)
        doc.add_paragraph(f"Trabajador: {st.session_state.trab['nombre']}")
        doc.add_paragraph("TEXTO LEGAL ACTUALIZADO 2025...")
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        st.download_button("Descargar Word", bio, f"{opcion}.docx")

# TAB 4: MASIVO CON COMBO BOX
with tabs[3]:
    st.header("Carga Masiva Inteligente")
    st.markdown("Descarga la plantilla que incluye listas desplegables (Combo Boxes) para evitar errores.")
    
    excel_tpl = GestorDocumental.generar_excel_masivo_con_combos()
    st.download_button("📥 Descargar Plantilla con Validaciones (.xlsx)", excel_tpl, "Plantilla_RRHH_Validada.xlsx")
    
    st.markdown("---")
    up_file = st.file_uploader("Subir Excel Completo", type=['xlsx'])
    if up_file:
        st.success("Archivo recibido. Procesando lotes...")

# TAB 5: INDICADORES (LINKS)
with tabs[4]:
    st.header("Indicadores Oficiales")
    
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.markdown("### 🌐 Fuentes Oficiales")
        st.markdown("- [Previred: Indicadores Previsionales](https://www.previred.com/indicadores-previsionales/)")
        st.markdown("- [SII: Impuesto Segunda Categoría 2025](https://www.sii.cl/valores_y_fechas/impuesto_2da_categoria/impuesto2025.htm)")
        
    with col_i2:
        st.markdown("### 📊 Valores del Mes")
        st.table(pd.DataFrame({
            "Indicador": ["UF", "UTM", "Sueldo Mínimo", "Tope AFP"],
            "Valor": [IND["UF"], IND["UTM"], IND["IMM"], f"{IND['TOPE_AFP']} UF"]
        }))
