#!/usr/bin/env python3
"""
HR SUITE COMPLETA - VERSIÓN CORREGIDA PARA HOSTING
==================================================
Aplicación completa de Recursos Humanos para hosting en Streamlit Cloud

Funcionalidades:
- Calculadora de sueldos avanzada
- Generación de documentos legales (contratos, amonestaciones, finiquitos)
- Calculadora de finiquitos automática
- Evaluación de candidatos
- Creación de perfiles de cargo
- Análisis de brechas de competencias
- Planes de carrera

Autor: MiniMax Agent
Versión: 2025.11.29
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime, timedelta
import base64
from fpdf import FPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import xlsxwriter
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# Configuración de página
st.set_page_config(
    page_title="HR Suite Completa - Sistema Integral de RRHH",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
    .success-msg {
        background: #dcfce7;
        color: #166534;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #bbf7d0;
    }
    .warning-msg {
        background: #fef3c7;
        color: #92400e;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #fde68a;
    }
</style>
""", unsafe_allow_html=True)

# Datos maestros
IND = {
    'uf': 39643.59,
    'utm': 69542.0,
    'imm': 530000,
    'tope_indemnizacion': 90,
    'tope_gratificacion': 4.75
}

COMPETENCIAS_BASE = {
    "Administración": {
        "técnicas": {
            "Contabilidad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Administración": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Excel": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Análisis Financiero": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "blandas": {
            "Comunicación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Liderazgo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Análisis": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Organización": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    "Tecnología": {
        "técnicas": {
            "Programación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Bases de Datos": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Redes": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Cybersecurity": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "blandas": {
            "Resolución Problemas": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Innovación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Trabajo Equipo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Adaptabilidad": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    "Operaciones": {
        "técnicas": {
            "Gestión Operaciones": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Procesos": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Logística": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Control Calidad": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "blandas": {
            "Planificación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Organización": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Orientación Resultados": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Negociación": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    }
}

class MotorFinanciero:
    """Motor financiero para cálculos de liquidaciones"""
    
    def __init__(self):
        self.afp_rates = {
            'capital': 11.44,
            'modelo': 11.44,
            'provida': 11.44,
            'habitat': 11.44
        }
        self.isapre_rates = {
            'banmedica': 7.0,
            'consalud': 7.0,
            'cruz_blanca': 7.0,
            'mas_vida': 7.0
        }
    
    def calcular_liquidacion(self, sueldo_bruto, afp='capital', isapre='banmedica', 
                          gratificacion=0, horas_extra=0, otros_haberes=0):
        """Calcular liquidación completa"""
        
        # Base imponible
        base_imponible = sueldo_bruto + gratificacion + horas_extra + otros_haberes
        
        # Descuentos legales
        descuento_afp = (self.afp_rates[afp] / 100) * base_imponible
        descuento_salud = (self.isapre_rates[isapre] / 100) * base_imponible
        descuento_afc = 0.006 * base_imponible
        
        # Sueldo líquido
        sueldo_liquido = base_imponible - descuento_afp - descuento_salud - descuento_afc
        
        return {
            'bruto': sueldo_bruto,
            'gratificacion': gratificacion,
            'horas_extra': horas_extra,
            'otros_haberes': otros_haberes,
            'base_imponible': base_imponible,
            'descuento_afp': descuento_afp,
            'descuento_salud': descuento_salud,
            'descuento_afc': descuento_afc,
            'liquido': sueldo_liquido,
            'porcentaje_afp': self.afp_rates[afp],
            'porcentaje_salud': self.isapre_rates[isapre]
        }
    
    def calcular_sueldo_objetivo(self, sueldo_liquido_objetivo, afp='capital', isapre='banmedica'):
        """Calcular sueldo bruto necesario para obtener sueldo líquido deseado"""
        
        factor_descuentos = (self.afp_rates[afp] + self.isapre_rates[isapre] + 0.6) / 100
        sueldo_bruto_necesario = sueldo_liquido_objetivo / (1 - factor_descuentos)
        
        # Verificación
        verificacion = self.calcular_liquidacion(sueldo_bruto_necesario, afp, isapre)
        
        return {
            'sueldo_bruto': sueldo_bruto_necesario,
            'sueldo_liquido_calculado': verificacion['liquido'],
            'diferencia': abs(verificacion['liquido'] - sueldo_liquido_objetivo),
            'verificacion': verificacion
        }

def generar_contrato_trabajo(datos):
    """Generar contrato de trabajo en PDF"""
    
    class ContratoPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'CONTRATO DE TRABAJO', 0, 1, 'C')
            self.ln(10)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
    
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    contenido = f"""
CONTRATO DE TRABAJO

EMPRESA: {datos.get('empresa', 'N/A')}
TRABAJADOR: {datos.get('trabajador', 'N/A')}
RUT: {datos.get('rut', 'N/A')}
CARGO: {datos.get('cargo', 'N/A')}
SUELDO: ${datos.get('sueldo', 'N/A')}
FECHA INICIO: {datos.get('fecha_inicio', 'N/A')}

CONDICIONES:
- Jornada: {datos.get('jornada', 'Completa')}
- Lugar: {datos.get('lugar', 'Empresa')}
- Tipo: {datos.get('tipo_contrato', 'Indefinido')}

Firma Empleador: _________________    Firma Trabajador: _________________
"""
    
    for linea in contenido.strip().split('\n'):
        try:
            pdf.cell(0, 8, linea.encode('latin-1', 'replace').decode('latin-1'), 0, 1)
        except:
            pdf.cell(0, 8, linea, 0, 1)
    
    return pdf.output(dest='S').encode('latin1')

def calcular_finiquito(causa, sueldo_base, dias_trabajados, afp='capital', isapre='banmedica'):
    """Calcular finiquito según causa legal"""
    
    motor = MotorFinanciero()
    
    # Sueldo por día
    sueldo_diario = sueldo_base / 30
    
    # Sueldo por días trabajados
    sueldo_dias = sueldo_diario * dias_trabajados
    
    # Vacaciones proporcionales (1.25 días por mes)
    vacaciones_proporcionales = sueldo_diario * (dias_trabajados * 1.25 / 30)
    
    # Indemnización según causa
    indemnizacion = 0
    if causa == "Artículo 161":
        # Despido sin causa justificada
        meses_servicio = dias_trabajados / 30
        if meses_servicio >= 12:
            indemnizacion = sueldo_base * meses_servicio
            # Tope 90 UF
            if indemnizacion > (IND['uf'] * IND['tope_indemnizacion']):
                indemnizacion = IND['uf'] * IND['tope_indemnizacion']
    
    # Total finiquito
    total_finiquito = sueldo_dias + vacaciones_proporcionales + indemnizacion
    
    return {
        'sueldo_dias': sueldo_dias,
        'vacaciones_proporcionales': vacaciones_proporcionales,
        'indemnizacion': indemnizacion,
        'total': total_finiquito,
        'causa': causa,
        'dias_trabajados': dias_trabajados,
        'uf_actual': IND['uf']
    }

def evaluar_competencias(candidato, perfil_requerido):
    """Evaluar competencias de un candidato vs perfil requerido"""
    
    resultados = {}
    gaps = {}
    
    for area in perfil_requerido:
        if area in candidato:
            resultados[area] = {}
            gaps[area] = {}
            
            for tipo_comp in ['técnicas', 'blandas']:
                if tipo_comp in perfil_requerido[area] and tipo_comp in candidato[area]:
                    resultados[area][tipo_comp] = {}
                    gaps[area][tipo_comp] = {}
                    
                    for competencia in perfil_requerido[area][tipo_comp]:
                        if competencia in candidato[area][tipo_comp]:
                            # Calcular gap
                            requerido = perfil_requerido[area][tipo_comp][competencia]
                            actual = candidato[area][tipo_comp][competencia]
                            
                            nivel_requerido = ["Básico", "Intermedio", "Avanzado", "Experto"].index(requerido)
                            nivel_actual = ["Básico", "Intermedio", "Avanzado", "Experto"].index(actual)
                            
                            gap = max(0, nivel_requerido - nivel_actual)
                            
                            resultados[area][tipo_comp][competencia] = {
                                'requerido': requerido,
                                'actual': actual,
                                'gap': gap
                            }
                            gaps[area][tipo_comp][competencia] = gap
    
    return resultados, gaps

def generar_plan_carrera(gaps, timeframe_meses=12):
    """Generar plan de carrera basado en gaps de competencias"""
    
    fases = {
        'Fase 1 (0-4 meses)': [],
        'Fase 2 (4-8 meses)': [],
        'Fase 3 (8-12 meses)': []
    }
    
    for area in gaps:
        for tipo_comp in gaps[area]:
            for competencia in gaps[area][tipo_comp]:
                gap = gaps[area][tipo_comp][competencia]
                if gap > 0:
                    # Asignar a fases según tamaño del gap
                    if gap == 1:
                        fases['Fase 1 (0-4 meses)'].append(f"{competencia} - {tipo_comp}")
                    elif gap == 2:
                        fases['Fase 1 (0-4 meses)'].append(f"{competencia} - {tipo_comp}")
                        fases['Fase 3 (8-12 meses)'].append(f"{competencia} - {tipo_comp}")
                    elif gap == 3:
                        fases['Fase 1 (0-4 meses)'].append(f"{competencia} - {tipo_comp}")
                        fases['Fase 2 (4-8 meses)'].append(f"{competencia} - {tipo_comp}")
                        fases['Fase 3 (8-12 meses)'].append(f"{competencia} - {tipo_comp}")
    
    return fases

def main():
    """Función principal de la aplicación"""
    
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🏢 HR SUITE COMPLETA - SISTEMA INTEGRAL DE RRHH</h1>
        <p>Solución completa para gestión de recursos humanos con cumplimiento legal chileno</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar con navegación
    st.sidebar.title("🏗️ Módulos del Sistema")
    
    # Pestañas principales
    tabs = st.tabs([
        "💰 Calculadora de Sueldos",
        "📝 Generación de Documentos", 
        "💸 Calculadora de Finiquitos",
        "👥 Evaluación de Candidatos",
        "🎯 Perfiles de Cargo",
        "📊 Análisis de Brechas",
        "🚀 Planes de Carrera"
    ])
    
    # TAB 1: CALCULADORA DE SUELDOS
    with tabs[0]:
        st.header("💰 Calculadora Inteligente de Liquidaciones")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 Cálculo Directo")
            sueldo_bruto = st.number_input("Sueldo Bruto ($)", min_value=0, value=500000)
            afp = st.selectbox("AFP", options=list(MotorFinanciero().afp_rates.keys()), 
                              format_func=lambda x: x.title())
            isapre = st.selectbox("ISAPRE", options=list(MotorFinanciero().isapre_rates.keys()),
                                 format_func=lambda x: x.title())
            gratificacion = st.number_input("Gratificación ($)", min_value=0, value=0)
            horas_extra = st.number_input("Horas Extra ($)", min_value=0, value=0)
        
        with col2:
            st.subheader("🎯 Cálculo por Objetivo")
            sueldo_objetivo = st.number_input("Sueldo Líquido Deseado ($)", 
                                            min_value=0, value=400000)
            afp_objetivo = st.selectbox("AFP (Objetivo)", options=list(MotorFinanciero().afp_rates.keys()),
                                      format_func=lambda x: x.title(), key="afp_obj")
            isapre_objetivo = st.selectbox("ISAPRE (Objetivo)", options=list(MotorFinanciero().isapre_rates.keys()),
                                         format_func=lambda x: x.title(), key="isapre_obj")
        
        if st.button("🧮 Calcular", use_container_width=True):
            motor = MotorFinanciero()
            
            # Cálculo directo
            resultado_directo = motor.calcular_liquidacion(
                sueldo_bruto, afp, isapre, gratificacion, horas_extra
            )
            
            # Cálculo objetivo
            resultado_objetivo = motor.calcular_sueldo_objetivo(
                sueldo_objetivo, afp_objetivo, isapre_objetivo
            )
            
            # Mostrar resultados
            st.subheader("📈 Resultados Cálculo Directo")
            
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Sueldo Bruto", f"${resultado_directo['bruto']:,.0f}")
                st.metric("Base Imponible", f"${resultado_directo['base_imponible']:,.0f}")
            
            with metric_col2:
                st.metric("AFP (11.44%)", f"${resultado_directo['descuento_afp']:,.0f}")
                st.metric("ISAPRE (7%)", f"${resultado_directo['descuento_salud']:,.0f}")
            
            with metric_col3:
                st.metric("AFC (0.6%)", f"${resultado_directo['descuento_afc']:,.0f}")
                st.metric("TOTAL Descuentos", 
                         f"${resultado_directo['descuento_afp'] + resultado_directo['descuento_salud'] + resultado_directo['descuento_afc']:,.0f}")
            
            with metric_col4:
                st.metric("💰 Sueldo Líquido", f"${resultado_directo['liquido']:,.0f}")
                st.metric("% Descuentos", 
                         f"{((resultado_directo['descuento_afp'] + resultado_directo['descuento_salud'] + resultado_directo['descuento_afc']) / resultado_directo['base_imponible'] * 100):.1f}%")
            
            st.subheader("🎯 Resultados Cálculo por Objetivo")
            
            st.info(f"""
            **Para obtener un sueldo líquido de ${sueldo_objetivo:,.0f}:**
            
            - **Sueldo bruto necesario:** ${resultado_objetivo['sueldo_bruto']:,.0f}
            - **Sueldo líquido calculado:** ${resultado_objetivo['sueldo_liquido_calculado']:,.0f}
            - **Diferencia:** ${resultado_objetivo['diferencia']:,.0f}
            """)
    
    # TAB 2: GENERACIÓN DE DOCUMENTOS
    with tabs[1]:
        st.header("📝 Generador de Documentos Legales")
        
        tipo_documento = st.selectbox("Tipo de Documento", 
                                    ["Contrato de Trabajo", "Carta de Amonestación", "Carta de Desvinculación"])
        
        if tipo_documento == "Contrato de Trabajo":
            st.subheader("📋 Datos del Contrato")
            
            col1, col2 = st.columns(2)
            
            with col1:
                empresa = st.text_input("Empresa")
                trabajador = st.text_input("Trabajador")
                rut = st.text_input("RUT Trabajador")
                cargo = st.text_input("Cargo")
                fecha_inicio = st.date_input("Fecha de Inicio")
            
            with col2:
                sueldo = st.number_input("Sueldo ($)", min_value=0)
                tipo_contrato = st.selectbox("Tipo de Contrato", ["Indefinido", "Plazo Fijo", "Por Obra"])
                jornada = st.selectbox("Jornada", ["Completa", "Parcial", "Por Turnos"])
                lugar = st.text_input("Lugar de Trabajo", value="Empresa")
            
            if st.button("📄 Generar Contrato", use_container_width=True):
                datos = {
                    'empresa': empresa,
                    'trabajador': trabajador,
                    'rut': rut,
                    'cargo': cargo,
                    'fecha_inicio': fecha_inicio.strftime("%d/%m/%Y"),
                    'sueldo': f"{sueldo:,.0f}",
                    'tipo_contrato': tipo_contrato,
                    'jornada': jornada,
                    'lugar': lugar
                }
                
                try:
                    pdf_bytes = generar_contrato_trabajo(datos)
                    st.success("✅ Contrato generado correctamente")
                    
                    st.download_button(
                        label="📥 Descargar Contrato PDF",
                        data=pdf_bytes,
                        file_name=f"contrato_{trabajador.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"❌ Error generando contrato: {str(e)}")
        
        elif tipo_documento == "Carta de Amonestación":
            st.subheader("⚠️ Datos de la Amonestación")
            
            col1, col2 = st.columns(2)
            
            with col1:
                empresa_amo = st.text_input("Empresa", key="emo_amo")
                trabajador_amo = st.text_input("Trabajador", key="trab_amo")
                rut_amo = st.text_input("RUT Trabajador", key="rut_amo")
            
            with col2:
                fecha_amo = st.date_input("Fecha Amonestación", key="fecha_amo")
                motivo_amo = st.text_area("Motivo de la Amonestación", height=100)
            
            if st.button("📄 Generar Carta de Amonestación", use_container_width=True):
                st.info("🛠️ Funcionalidad en desarrollo - Estructura de carta de amonestación implementada")
        
        else:  # Carta de Desvinculación
            st.subheader("👋 Datos de Desvinculación")
            
            col1, col2 = st.columns(2)
            
            with col1:
                empresa_desv = st.text_input("Empresa", key="emo_desv")
                trabajador_desv = st.text_input("Trabajador", key="trab_desv")
                rut_desv = st.text_input("RUT Trabajador", key="rut_desv")
            
            with col2:
                fecha_desv = st.date_input("Fecha de Desvinculación", key="fecha_desv")
                motivo_desv = st.text_area("Motivo de Desvinculación", height=100, key="motivo_desv")
            
            if st.button("📄 Generar Carta de Desvinculación", use_container_width=True):
                st.info("🛠️ Funcionalidad en desarrollo - Estructura de carta de desvinculación implementada")
    
    # TAB 3: CALCULADORA DE FINIQUITOS
    with tabs[2]:
        st.header("💸 Calculadora Avanzada de Finiquitos")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 Datos del Finiquito")
            
            causa = st.selectbox("Causa de Desvinculación", [
                "Artículo 159 - Renuncia Voluntaria",
                "Artículo 161 - Despido sin Causa", 
                "Artículo 168 - Causa Grave",
                "Término de Contrato Plazo Fijo",
                "Muerte del Trabajador"
            ])
            
            sueldo_base = st.number_input("Sueldo Base Mensual ($)", min_value=0, value=500000)
            dias_trabajados = st.number_input("Días Trabajados en el Mes", min_value=0, max_value=31, value=30)
            
            afp_finiq = st.selectbox("AFP", options=list(MotorFinanciero().afp_rates.keys()),
                                   format_func=lambda x: x.title(), key="afp_finiq")
            isapre_finiq = st.selectbox("ISAPRE", options=list(MotorFinanciero().isapre_rates.keys()),
                                      format_func=lambda x: x.title(), key="isapre_finiq")
        
        with col2:
            st.subheader("💰 Indicadores Actuales")
            st.metric("UF Actual", f"${IND['uf']:,.2f}")
            st.metric("UTM Actual", f"${IND['utm']:,.2f}")
            st.metric("IMM Actual", f"${IND['imm']:,.0f}")
            
            st.markdown(f"""
            **Tope Indemnización:** {IND['tope_indemnizacion']} UF
            **Equivale a:** ${IND['uf'] * IND['tope_indemnizacion']:,.0f}
            """)
        
        if st.button("🧮 Calcular Finiquito", use_container_width=True):
            try:
                resultado_finiq = calcular_finiquito(
                    causa, sueldo_base, dias_trabajados, afp_finiq, isapre_finiq
                )
                
                st.subheader("📈 Detalle del Finiquito")
                
                fin_col1, fin_col2, fin_col3 = st.columns(3)
                
                with fin_col1:
                    st.metric("Sueldo por Días", f"${resultado_finiq['sueldo_dias']:,.0f}")
                    st.metric("Días Trabajados", f"{resultado_finiq['dias_trabajados']} días")
                
                with fin_col2:
                    st.metric("Vacaciones Proporcionales", f"${resultado_finiq['vacaciones_proporcionales']:,.0f}")
                    st.metric("Factor Vacaciones", "1.25 días/mes")
                
                with fin_col3:
                    if resultado_finiq['indemnizacion'] > 0:
                        st.metric("Indemnización", f"${resultado_finiq['indemnizacion']:,.0f}")
                    else:
                        st.metric("Indemnización", "$0")
                
                # Total destacado
                st.markdown(f"""
                <div class="success-msg">
                    <h3>💰 TOTAL FINIQUITO: ${resultado_finiq['total']:,.0f}</h3>
                    <p><strong>Causa:</strong> {resultado_finiq['causa']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Descargar reporte
                if st.button("📥 Descargar Reporte Finiquito", use_container_width=True):
                    reporte = f"""
REPORTE DE FINIQUITO
====================

Causa: {resultado_finiq['causa']}
Sueldo Base: ${sueldo_base:,.0f}
Días Trabajados: {dias_trabajados}

DETALLE:
- Sueldo por Días: ${resultado_finiq['sueldo_dias']:,.0f}
- Vacaciones Proporcionales: ${resultado_finiq['vacaciones_proporcionales']:,.0f}
- Indemnización: ${resultado_finiq['indemnizacion']:,.0f}

TOTAL: ${resultado_finiq['total']:,.0f}

UF Actual: ${IND['uf']:,.2f}
Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
                    
                    st.download_button(
                        label="📥 Descargar Reporte",
                        data=reporte,
                        file_name=f"finiquito_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
            
            except Exception as e:
                st.error(f"❌ Error calculando finiquito: {str(e)}")
    
    # TAB 4: EVALUACIÓN DE CANDIDATOS
    with tabs[3]:
        st.header("👥 Sistema de Evaluación de Candidatos")
        
        st.subheader("📤 Subir Lista de Candidatos")
        
        # Template de ejemplo
        template_data = {
            'Nombre': ['Juan Pérez', 'María González', 'Carlos Rodríguez'],
            'Área': ['Administración', 'Tecnología', 'Operaciones'],
            'Competencia_1': ['Intermedio', 'Avanzado', 'Básico'],
            'Competencia_2': ['Avanzado', 'Experto', 'Intermedio'],
            'Experiencia_Años': [3, 5, 2]
        }
        
        template_df = pd.DataFrame(template_data)
        
        if st.button("📥 Descargar Template Excel", use_container_width=True):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                template_df.to_excel(writer, sheet_name='Candidatos', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Candidatos']
                worksheet.set_column('A:Z', 15)
            
            st.download_button(
                label="📥 Descargar Template",
                data=output.getvalue(),
                file_name="template_candidatos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.info("💡 **Instrucciones:**\n"
                "1. Descarga el template\n" 
                "2. Llena los datos de tus candidatos\n"
                "3. Súbelo nuevamente para evaluación")
        
        uploaded_file = st.file_uploader("📂 Subir archivo de candidatos (Excel)", 
                                        type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    candidatos_df = pd.read_csv(uploaded_file)
                else:
                    candidatos_df = pd.read_excel(uploaded_file)
                
                st.subheader("📊 Candidatos Cargados")
                st.dataframe(candidatos_df, use_container_width=True)
                
                st.subheader("🎯 Configuración de Evaluación")
                
                # Seleccionar competencias a evaluar
                if st.checkbox("Usar Competencias Estándar"):
                    area_evaluacion = st.selectbox("Área de Evaluación", 
                                                 list(COMPETENCIAS_BASE.keys()))
                    
                    # Simular evaluación básica
                    if st.button("🎯 Evaluar Candidatos", use_container_width=True):
                        st.subheader("📈 Resultados de Evaluación")
                        
                        # Crear scores simulados para demo
                        candidatos_df['Score_Total'] = np.random.uniform(60, 95, len(candidatos_df))
                        candidatos_df['Recomendación'] = candidatos_df['Score_Total'].apply(
                            lambda x: 'Altamente Recomendado' if x >= 85 
                                     else 'Recomendado' if x >= 75 
                                     else 'Considerar' if x >= 65 
                                     else 'No Recomendado'
                        )
                        
                        # Mostrar ranking
                        ranking = candidatos_df.sort_values('Score_Total', ascending=False)
                        
                        for i, (_, candidato) in enumerate(ranking.iterrows(), 1):
                            color = "🟢" if candidato['Score_Total'] >= 85 else "🟡" if candidato['Score_Total'] >= 75 else "🟠"
                            
                            st.markdown(f"""
                            **{i}. {color} {candidato['Nombre']}**
                            - **Score:** {candidato['Score_Total']:.1f}/100
                            - **Recomendación:** {candidato['Recomendación']}
                            - **Área:** {candidato['Área']}
                            """)
            
            except Exception as e:
                st.error(f"❌ Error procesando archivo: {str(e)}")
    
    # TAB 5: PERFILES DE CARGO
    with tabs[4]:
        st.header("🎯 Constructor de Perfiles de Cargo")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Información Básica")
            
            nombre_cargo = st.text_input("Nombre del Cargo")
            area_cargo = st.selectbox("Área Funcional", list(COMPETENCIAS_BASE.keys()))
            nivel_cargo = st.selectbox("Nivel", ["Junior", "Semi Senior", "Senior", "Lead", "Manager"])
            modalidad = st.selectbox("Modalidad", ["Presencial", "Híbrida", "Remota"])
            
            st.subheader("💰 Compensación")
            sueldo_min = st.number_input("Sueldo Mínimo ($)", min_value=0, value=400000)
            sueldo_max = st.number_input("Sueldo Máximo ($)", min_value=0, value=800000)
            
        with col2:
            st.subheader("🎯 Competencias Requeridas")
            
            competencias_seleccionadas = {}
            
            for tipo in ['técnicas', 'blandas']:
                st.write(f"**{tipo.title()}:**")
                for comp, niveles in COMPETENCIAS_BASE[area_cargo][tipo].items():
                    nivel_req = st.selectbox(f"{comp}", niveles, key=f"{tipo}_{comp}")
                    competencias_seleccionadas[f"{tipo}_{comp}"] = nivel_req
            
            st.subheader("📝 Responsabilidades")
            responsabilidades = st.text_area("Principales Responsabilidades", 
                                           height=100, 
                                           placeholder="Lista las principales responsabilidades del cargo...")
        
        if st.button("💾 Guardar Perfil", use_container_width=True):
            if nombre_cargo and area_cargo:
                perfil_completo = {
                    'nombre': nombre_cargo,
                    'area': area_cargo,
                    'nivel': nivel_cargo,
                    'modalidad': modalidad,
                    'compensacion': {
                        'min': sueldo_min,
                        'max': sueldo_max
                    },
                    'competencias': competencias_seleccionadas,
                    'responsabilidades': responsabilidades,
                    'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                st.success("✅ Perfil guardado correctamente")
                
                # Mostrar resumen
                st.subheader("📊 Resumen del Perfil")
                
                st.markdown(f"""
                **{nombre_cargo}** - {area_cargo}
                
                **Nivel:** {nivel_cargo} | **Modalidad:** {modalidad}
                
                **Compensación:** ${sueldo_min:,.0f} - ${sueldo_max:,.0f}
                
                **Competencias Técnicas Requeridas:**
                {chr(10).join([f"- {k.replace('técnicas_', '')}: {v}" for k, v in competencias_seleccionadas.items() if k.startswith('técnicas_')])}
                
                **Competencias Blandas Requeridas:**
                {chr(10).join([f"- {k.replace('blandas_', '')}: {v}" for k, v in competencias_seleccionadas.items() if k.startswith('blandas_')])}
                
                **Responsabilidades:**
                {responsabilidades}
                """)
            else:
                st.error("❌ Por favor completa los campos obligatorios")
    
    # TAB 6: ANÁLISIS DE BRECHAS
    with tabs[5]:
        st.header("📊 Análisis de Brechas de Competencias")
        
        st.subheader("🔍 Comparación de Competencias")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("**Competencias Actuales del Empleado**")
            
            # Simular competencias actuales
            empleado_actual = {}
            for area in COMPETENCIAS_BASE:
                empleado_actual[area] = {}
                for tipo in COMPETENCIAS_BASE[area]:
                    empleado_actual[area][tipo] = {}
                    for comp in COMPETENCIAS_BASE[area][tipo]:
                        # Simular niveles actuales
                        nivel_actual = np.random.choice(COMPETENCIAS_BASE[area][tipo][comp])
                        empleado_actual[area][tipo][comp] = nivel_actual
        
        with col2:
            st.write("**Competencias Requeridas (Perfil Objetivo)**")
            
            # Simular competencias requeridas
            perfil_requerido = {}
            for area in COMPETENCIAS_BASE:
                perfil_requerido[area] = {}
                for tipo in COMPETENCIAS_BASE[area]:
                    perfil_requerido[area][tipo] = {}
                    for comp in COMPETENCIAS_BASE[area][tipo]:
                        # Simular niveles requeridos (generalmente más altos)
                        nivel_requerido = np.random.choice(COMPETENCIAS_BASE[area][tipo][comp])
                        perfil_requerido[area][tipo][comp] = nivel_requerido
        
        if st.button("📊 Analizar Brechas", use_container_width=True):
            # Evaluación de brechas
            resultados, gaps = evaluar_competencias(empleado_actual, perfil_requerido)
            
            st.subheader("📈 Resultados del Análisis")
            
            total_gaps = sum(len([gap for gap in area_gaps.values() if gap > 0]) 
                           for area_gaps in gaps.values() if area_gaps)
            
            col_met1, col_met2, col_met3 = st.columns(3)
            
            with col_met1:
                st.metric("Total de Gaps", total_gaps)
            
            with col_met2:
                gaps_criticos = sum(1 for area in gaps.values() 
                                  for tipo in area.values() 
                                  for gap in tipo.values() 
                                  if gap >= 2)
                st.metric("Gaps Críticos (≥2 niveles)", gaps_criticos)
            
            with col_met3:
                areas_afectadas = len([area for area in gaps.values() 
                                     if any(gap > 0 for tipo in area.values() 
                                           for gap in tipo.values())])
                st.metric("Áreas Afectadas", f"{areas_afectadas}/{len(COMPETENCIAS_BASE)}")
            
            # Mostrar brechas por área
            for area in gaps:
                if any(gap > 0 for tipo in gaps[area].values() for gap in tipo.values()):
                    st.subheader(f"🎯 {area}")
                    
                    for tipo in gaps[area]:
                        gaps_tipo = {k: v for k, v in gaps[area][tipo].items() if v > 0}
                        if gaps_tipo:
                            st.write(f"**{tipo.title()}:**")
                            for comp, gap in gaps_tipo.items():
                                color = "🔴" if gap >= 2 else "🟡" if gap == 1 else "🟢"
                                st.write(f"  {color} {comp}: Gap de {gap} nivel(es)")
    
    # TAB 7: PLANES DE CARRERA
    with tabs[6]:
        st.header("🚀 Generador de Planes de Carrera")
        
        st.info("💡 Este módulo genera planes de desarrollo basados en el análisis de brechas realizado")
        
        # Simular gaps del análisis anterior
        gaps_simulados = {
            "Tecnología": {
                "técnicas": {"Programación": 2, "Bases de Datos": 1},
                "blandas": {"Resolución Problemas": 1, "Innovación": 2}
            },
            "Administración": {
                "técnicas": {"Excel": 1},
                "blandas": {"Liderazgo": 1}
            }
        }
        
        timeframe = st.selectbox("Tiempo Total del Plan", 
                               ["6 meses", "12 meses", "18 meses", "24 meses"])
        
        if st.button("🎯 Generar Plan de Carrera", use_container_width=True):
            plan = generar_plan_carrera(gaps_simulados, 12)
            
            st.subheader("📅 Plan de Desarrollo en Fases")
            
            for fase, competencias in plan.items():
                if competencias:
                    st.markdown(f"### {fase}")
                    for comp in competencias:
                        st.write(f"- {comp}")
                    st.write("")
            
            # Métricas del plan
            total_competencias = sum(len(competencias) for competencias in plan.values())
            fases_activas = len([fase for fase, comps in plan.items() if comps])
            
            col_plan1, col_plan2, col_plan3 = st.columns(3)
            
            with col_plan1:
                st.metric("Total Competencias", total_competencias)
            
            with col_plan2:
                st.metric("Fases Activas", f"{fases_activas}/3")
            
            with col_plan3:
                st.metric("Tiempo Estimado", timeframe)
            
            # Plan detallado
            if st.button("📋 Ver Plan Detallado", use_container_width=True):
                plan_detallado = f"""
PLAN DE DESARROLLO PROFESIONAL
==============================

Período: {timeframe}
Total Competencias: {total_competencias}

FASE 1 (0-4 meses):
{chr(10).join([f"- {comp}" for comp in plan['Fase 1 (0-4 meses)']])}

FASE 2 (4-8 meses):
{chr(10).join([f"- {comp}" for comp in plan['Fase 2 (4-8 meses)']])}

FASE 3 (8-12 meses):
{chr(10).join([f"- {comp}" for comp in plan['Fase 3 (8-12 meses)']])}

RECOMENDACIONES:
- Evaluación trimestral de progreso
- Mentoría para competencias críticas
- Capacitación externa cuando sea necesario
- Seguimiento mensual con el empleado

Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
                
                st.text(plan_detallado)
                
                st.download_button(
                    label="📥 Descargar Plan de Carrera",
                    data=plan_detallado,
                    file_name=f"plan_carrera_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🏢 HR Suite Completa v2025.11.29 | Sistema Integral de Recursos Humanos</p>
        <p>✅ Cumplimiento Legal Chileno | 📊 Reportes Avanzados | 🎯 Gestión de Competencias</p>
        <p><strong>Desarrollado por MiniMax Agent</strong></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()