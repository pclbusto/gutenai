#!/bin/bash

# Cambiar al directorio del proyecto
cd "/home/pedro/PycharmProjects/gutenai"

# Configurar variables de entorno para reducir warnings de portales
export GDK_BACKEND=x11
export G_MESSAGES_DEBUG=""

# Silenciar warnings de Gdk sobre portales (opcional)
# Descomenta la siguiente línea si quieres silenciar todos los warnings de Gdk
# export GDK_DEBUG=""

# Ejecutar la aplicación
.venv/bin/python3 main.py "$@" 2>&1 | grep -v "Failed to read portal settings"
