# Configuración de Indicadores Económicos - Chile 2025
# Actualizar estos valores según los boletines oficiales del SII

# Indicadores base actualizados a Noviembre 2025
INDICADORES_ECONOMICOS = {
    # UF (Unidad de Fomento) - BCI
    "UF": 39643.59,
    
    # UTM (Unidad Tributaria Mensual) - SII
    "UTM": 69542.0,
    
    # IMM (Ingreso Mínimo Mensual) - Banco Central
    "IMM": 530000,
    
    # Tope Gratificación
    "TOPE_GRAT": (4.75 * 530000) / 12,  # 4.75 veces IMM anualizado
    
    # Topes previsionales (UF)
    "TOPE_AFP": 84.3,    # 84.3 UF (Aportes al Seguro de Cesantía)
    "TOPE_AFC": 126.6,   # 126.6 UF (Afiliación Caja Compensación)
    
    # Tope indemnización por años de servicio
    "TOPE_INDEM_ANOS": 90,  # 90 UF máximo por año
    
    # Jornada laboral
    "HORAS_SEMANALES_LEGALES": 45,  # Hasta implementación completa 40 horas
    
    # Valor hora ordinaria (IMM / horas mensuales)
    "VALOR_HORA_ORDINARIA": 530000 / 180,  # 180 horas mensuales promedio
    
    # Porcentajes legales
    "PORCENTAJE_AFP": 0.11,     # 11% trabajador
    "PORCENTAJE_SALUD_MIN": 0.07,  # 7% mínimo
    "PORCENTAJE_AFC": 0.006,    # 0.6% AFC
    
    # Bonificación fiscal Isapre
    "MAX_ISAPRE_BONIF_UF": 4.0,  # Máximo 4 UF bonificación fiscal
    
    # Factor vacaciones
    "DIAS_VACACIONES_ANUAL": 15,   # Días hábiles por año
    "FACTOR_PROPORCIONAL_VAC": 1.25,  # Factor días trabajados
    
    # Tope horas extras
    "HORAS_EXTRAS_DIARIAS_MAX": 2,  # Máximo 2 horas extras diarias
    "RECARGO_HORAS_EXTRAS_1": 0.25,  # 25% recargo primeras 2 horas
    "RECARGO_HORAS_EXTRAS_2": 0.50,  # 50% recargo horas adicionales
}

# Configuración de áreas y competencias
COMPETENCIAS_POR_AREA = {
    "Administración": {
        "Conocimientos Técnicos": {
            "Contabilidad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Administración": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Excel": ["Básico", "Intermedio", "Avanzado", "Avanzado+"],
            "Gestión Documental": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Normativa Laboral": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Comunicación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Liderazgo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Análisis": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Organización": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Atención al Cliente": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    
    "Tecnología": {
        "Conocimientos Técnicos": {
            "Programación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Bases de Datos": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Redes": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "DevOps": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Ciberseguridad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Cloud Computing": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Resolución Problemas": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Innovación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Trabajo Equipo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Aprendizaje Continuo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Comunicación Técnica": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    
    "Operaciones": {
        "Conocimientos Técnicos": {
            "Gestión Operaciones": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Procesos": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Logística": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Control Calidad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Lean Manufacturing": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Supply Chain": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Planificación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Organización": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Orientación Resultados": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Toma Decisiones": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Liderazgo Operacional": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    
    "Recursos Humanos": {
        "Conocimientos Técnicos": {
            "Legislación Laboral": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Reclutamiento": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Evaluación Desempeño": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Compensaciones": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Desarrollo Organizacional": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Relaciones Laborales": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Empatía": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Confidencialidad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Mediación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Comunicación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Liderazgo RRHH": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    
    "Finanzas": {
        "Conocimientos Técnicos": {
            "Contabilidad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Análisis Financiero": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Presupuestos": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Auditoría": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Finanzas Corporativas": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Tributación": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Análisis Numérico": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Atención al Detalle": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Integridad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Toma Decisiones": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Comunicación Financiera": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    },
    
    "Marketing": {
        "Conocimientos Técnicos": {
            "Marketing Digital": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Análisis de Mercado": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Branding": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "SEO/SEM": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Analítica Web": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Redes Sociales": ["Básico", "Intermedio", "Avanzado", "Experto"]
        },
        "Habilidades Blandas": {
            "Creatividad": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Orientación Cliente": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Comunicación": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Liderazgo": ["Básico", "Intermedio", "Avanzado", "Experto"],
            "Innovación": ["Básico", "Intermedio", "Avanzado", "Experto"]
        }
    }
}

# Configuración de causales de terminación
CAUSALES_TERMINACION = {
    "Art. 159 N°1": {
        "nombre": "Renuncia Voluntaria",
        "descripcion": "Por voluntad unilateral del trabajador",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Días Trabajados", "Otros Haberes"],
        "preaviso": "Opcional",
        "indemnizacion": False
    },
    
    "Art. 159 N°2": {
        "nombre": "Vencimiento del Plazo",
        "descripcion": "Terminación natural del contrato a plazo fijo",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Días Trabajados", "Otros Haberes"],
        "preaviso": "No requerido",
        "indemnizacion": False
    },
    
    "Art. 159 N°3": {
        "nombre": "Muerte del Trabajador",
        "descripcion": "Fallecimiento del trabajador",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Días Trabajados", "Indemnización por Muerte"],
        "preaviso": "No aplicable",
        "indemnizacion": "Hasta 11 meses"
    },
    
    "Art. 159 N°4": {
        "nombre": "Vencimiento del Contrato",
        "descripcion": "Finalización del contrato por obra determinada",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Días Trabajados", "Otros Haberes"],
        "preaviso": "No requerido",
        "indemnizacion": False
    },
    
    "Art. 159 N°5": {
        "nombre": "Mutuo Acuerdo",
        "descripcion": "Terminación por acuerdo entre las partes",
        "finiquito_incluye": ["A convenir entre las partes"],
        "preaviso": "Por acuerdo",
        "indemnizacion": "Por acuerdo"
    },
    
    "Art. 161": {
        "nombre": "Necesidades de la Empresa",
        "descripcion": "Terminación por razones de funcionamiento",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Indemnización por Años", "Mes de Aviso"],
        "preaviso": "30 días mínimo",
        "indemnizacion": "1 mes por año (máximo 11 meses)"
    },
    
    "Art. 168": {
        "nombre": "Término Injustificado",
        "descripcion": "Terminación sin causa legal que lo justifique",
        "finiquito_incluye": ["Vacaciones Proporcionales", "Indemnización", "Días Trabajados"],
        "preaviso": "No aplicable",
        "indemnizacion": "Hasta 11 meses + pago íntegro"
    }
}

# Templates de documentos legales
TEMPLATES_DOCUMENTOS = {
    "contrato_indefinido": {
        "estructura": [
            "encabezado_empresa",
            "datos_empresa", 
            "datos_trabajador",
            "clausulas_principales",
            "cumplimiento_legal",
            "firmas"
        ],
        " clausulas_obligatorias": [
            "Jornada de trabajo",
            "Sueldo y forma de pago",
            "Duración del contrato",
            "Vacaciones",
            "Descansos",
            "Locación de los servicios",
            "Representación del trabajador"
        ]
    },
    
    "carta_amonestacion": {
        "estructura": [
            "encabezado_empresa",
            "fecha",
            "destinatario", 
            "descripcion_falta",
            "conducta_observada",
            "consecuencias",
            "medidas_correctivas",
            "advertencia",
            "firma"
        ]
    }
}

# Configuración de reportes
REPORTES_DISPONIBLES = {
    "liquidaciones_mensuales": {
        "nombre": "Liquidaciones Mensuales",
        "descripcion": "Reporte completo de todas las liquidaciones del mes",
        "campos": ["RUT", "Nombre", "Cargo", "Sueldo Base", "Grat", "Líquido", "Fecha"],
        "formato": "Excel"
    },
    
    "finiquitos_pendientes": {
        "nombre": "Finiquitos Pendientes", 
        "descripcion": "Lista de finiquitos por pagar",
        "campos": ["RUT", "Nombre", "Fecha Término", "Causal", "Monto", "Estado"],
        "formato": "Excel"
    },
    
    "analisis_brechas": {
        "nombre": "Análisis de Brechas",
        "descripcion": "Reporte de brechas de competencia por área",
        "campos": ["Empleado", "Cargo", "Área", "Competencia", "Brecha", "Score"],
        "formato": "Excel"
    },
    
    "rotacion_personal": {
        "nombre": "Rotación de Personal",
        "descripcion": "Análisis de rotación y causas",
        "campos": ["RUT", "Nombre", "Cargo", "Fecha Ingreso", "Fecha Salida", "Causal"],
        "formato": "Excel"
    },
    
    "cumplimiento_legal": {
        "nombre": "Cumplimiento Legal",
        "descripcion": "Estado de cumplimiento de normativas",
        "campos": ["Aspecto", "Estado", "Última Revisión", "Próxima Revisión"],
        "formato": "PDF"
    },
    
    "presupuesto_salarial": {
        "nombre": "Presupuesto Salarial",
        "descripcion": "Análisis de gasto en personal",
        "campos": ["Área", "Cantidad Empleados", "Sueldo Total", "Cargas", "Total"],
        "formato": "Excel"
