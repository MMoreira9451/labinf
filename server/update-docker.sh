#!/bin/bash

# 🔧 CONFIGURACIÓN - AJUSTAR ESTAS RUTAS
DOCKER_USER="ashby4469"
COMPOSE_FILE="/srv/docker/acceso.informaticauaint.com/docker-compose.yml"  # ← CAMBIAR POR RUTA DEL COMPOSE
LOG_FILE="/var/log/docker-update.log"

# Función de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "🚀 Iniciando actualización de imágenes Docker..."

# Verificar si docker-compose existe
if [ ! -f "$COMPOSE_FILE" ]; then
    log "❌ ERROR: docker-compose.yml no encontrado en $COMPOSE_FILE"
    exit 1
fi

# Cambiar al directorio del compose
cd "$(dirname "$COMPOSE_FILE")" || exit 1

# Pull de las nuevas imágenes
log "📥 Descargando nuevas imágenes..."

# Definir imágenes específicas de ashby4469
IMAGES=(
    "ashby4469/front-end-web:latest"
    "ashby4469/back-end-estudiantes:latest"
    "ashby4469/back-end-ayudantes:latest"
    "ashby4469/back-end-lector:latest"
    "ashby4469/front-end-lector:latest"
)

UPDATED=false

# Verificar cada imagen
for image in "${IMAGES[@]}"; do
    log "🔍 Verificando $image..."
    
    # Obtener ID actual de la imagen
    CURRENT_ID=$(docker images --no-trunc --quiet "$image" 2>/dev/null)
    
    # Pull de la nueva imagen
    docker pull "$image"
    
    # Obtener nuevo ID
    NEW_ID=$(docker images --no-trunc --quiet "$image" 2>/dev/null)
    
    # Comparar IDs
    if [ "$CURRENT_ID" != "$NEW_ID" ] && [ -n "$NEW_ID" ]; then
        log "📦 Nueva versión detectada para $image"
        UPDATED=true
    else
        log "ℹ️  No hay actualizaciones para $image"
    fi
done

# Si hay actualizaciones, recrear contenedores
if [ "$UPDATED" = true ]; then
    log "🔄 Nuevas imágenes detectadas, recreando contenedores..."
    
    # Recrear contenedores con nuevas imágenes
    docker compose up -d --force-recreate
    
    # Verificar que los contenedores estén corriendo
    sleep 10
    
    # Mostrar estado
    log "📊 Estado de los servicios:"
    docker compose ps | tee -a "$LOG_FILE"
    
    # Limpiar imágenes no utilizadas
    log "🧹 Limpiando imágenes no utilizadas..."
    docker image prune -f
    
    log "✅ Actualización completada exitosamente"
    
else
    log "ℹ️  No hay nuevas imágenes disponibles"
fi

log "🏁 Proceso de actualización finalizado"
