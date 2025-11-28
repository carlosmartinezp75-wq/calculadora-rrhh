#!/bin/bash

# Script para ejecutar HR Suite Pro
# Uso: bash run.sh

echo "🚀 Iniciando HR Suite Pro..."

# Verificar si existe el entorno virtual
if [ -d "hr_suite_env" ]; then
    echo "🔄 Activando entorno virtual..."
    source hr_suite_env/bin/activate
else
    echo "⚠️ Entorno virtual no encontrado. Ejecutando instalación..."
    chmod +x install.sh
    ./install.sh
    source hr_suite_env/bin/activate
fi

echo "🌐 Abriendo aplicación en el navegador..."
echo "📱 URL: http://localhost:8501"

# Ejecutar Streamlit
streamlit run hr_suite_complete.py --server.port 8501 --server.address 0.0.0.0
