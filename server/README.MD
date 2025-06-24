# 🚀 Guía de Implementación - Sistema Webhook Auto-Deploy

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Prerrequisitos](#prerrequisitos)
3. [Instalación del Sistema](#instalación-del-sistema)
4. [Configuración de GitHub](#configuración-de-github)
5. [Configuración del Proxy](#configuración-del-proxy)
6. [Verificación y Testing](#verificación-y-testing)
7. [Mantenimiento](#mantenimiento)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

Este sistema permite la actualización automática de los contenedores Docker cuando se hace push a la rama `main`. El flujo es:

```
GitHub Push → Actions Build → Docker Hub → Webhook → Servidor → Update Containers
```

**Componentes:**
- **Webhook Server**: Recibe notificaciones de GitHub Actions
- **Update Script**: Actualiza las imágenes Docker y recrea contenedores
- **SystemD Service**: Mantiene el webhook corriendo
- **GitHub Actions**: Workflow automatizado

---

## ✅ Prerrequisitos

### En el Servidor:
- ✅ Ubuntu/Debian con Docker y Docker Compose
- ✅ Python 3.8+ instalado
- ✅ Acceso root/sudo
- ✅ Puerto 9000 disponible
- ✅ Conexión a internet

### En GitHub:
- ✅ Repositorio con permisos de administrador
- ✅ Secrets configurados
- ✅ GitHub Actions habilitado

---

## 🛠️ Instalación del Sistema

### Paso 1: Preparar Directorios

```bash
# Conectar al servidor
ssh usuario@tu-servidor.com

# Crear directorios necesarios
sudo mkdir -p /opt/scripts
sudo mkdir -p /var/log
sudo chown $USER:$USER /opt/scripts
```

### Paso 2: Instalar Scripts

**Descargar y ubicar scripts del repositorio:**

1. **Script de actualización**: Colocar `docker-update.sh` en `/opt/scripts/docker-update.sh`
2. **Servidor webhook**: Colocar `webhook-server.py` en `/opt/scripts/webhook-server.py`

```bash
# Dar permisos de ejecución
chmod +x /opt/scripts/docker-update.sh
chmod +x /opt/scripts/webhook-server.py
```

**⚠️ IMPORTANTE**: Editar `/opt/scripts/docker-update.sh` y configurar:
- `COMPOSE_FILE="/ruta/real/a/tu/docker-compose.yml"`

**⚠️ IMPORTANTE**: Editar `/opt/scripts/webhook-server.py` y configurar:
- `WEBHOOK_SECRET = "tu_secreto_super_seguro"`

### Paso 3: Crear Servicio SystemD

**Crear archivo de servicio:**
```bash
sudo nano /etc/systemd/system/docker-webhook.service
```

**Colocar el contenido del archivo `docker-webhook.service` del repositorio.**

### Paso 4: Activar el Servicio

```bash
# Recargar systemd para reconocer el nuevo servicio
sudo systemctl daemon-reload

# Habilitar servicio para inicio automático
sudo systemctl enable docker-webhook

# Iniciar el servicio
sudo systemctl start docker-webhook

# Verificar estado
sudo systemctl status docker-webhook
```

### Paso 5: Verificar Funcionamiento

```bash
# Ver logs en tiempo real
sudo journalctl -u docker-webhook -f

# Probar health check local
curl http://localhost:9000/webhook/health

# Verificar puerto abierto
sudo netstat -tlnp | grep :9000
```

---

## 🔧 Configuración de GitHub

### Paso 1: Configurar Secrets

En tu repositorio GitHub:

1. Ve a `Settings` → `Secrets and variables` → `Actions`
2. Crear **Environment** llamado `Prod`
3. En el environment `Prod`, agregar estos secrets:

```
DOCKERHUB_USERNAME=tu_usuario_dockerhub
DOCKERHUB_TOKEN=tu_token_dockerhub
WEBHOOK_SECRET=el_mismo_secreto_del_servidor
```

### Paso 2: Configurar Workflow

**Colocar el archivo `ci-cd.yml` en `.github/workflows/ci-cd.yml` de tu repositorio.**

### Paso 3: Configurar docker-compose.yml

**Colocar el archivo `docker-compose.yml` optimizado en la raíz de tu proyecto en el servidor.**

---

## 🌐 Configuración del Proxy

### Nginx Proxy Manager

**Crear Proxy Host:**

1. **General Tab:**
   - Domain Names: `acceso.informaticauaint.com`
   - Scheme: `http`
   - Forward Hostname/IP: `172.17.0.1` (o IP de tu servidor)
   - Forward Port: `9000`
   - Block Common Exploits: ✅

2. **SSL Tab:**
   - SSL Certificate: Request new SSL Certificate
   - Force SSL: ✅
   - HTTP/2 Support: ✅

3. **Advanced Tab:**
   - Colocar la configuración nginx del repositorio

### Firewall (si es necesario)

```bash
# Ubuntu/Debian con ufw
sudo ufw allow 9000/tcp

# CentOS/RHEL con firewalld
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

---

## ✅ Verificación y Testing

### Paso 1: Test Local del Webhook

```bash
# Probar endpoint de salud
curl https://acceso.informaticauaint.com/webhook/health

# Probar webhook sin firma (debe funcionar si verificación está deshabilitada)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": "manual"}' \
  https://acceso.informaticauaint.com/webhook/docker-update
```

### Paso 2: Test del Script de Actualización

```bash
# Ejecutar manualmente
sudo /opt/scripts/docker-update.sh

# Ver logs
tail -f /var/log/docker-update.log
```

### Paso 3: Test Completo

1. **Hacer push a rama `main`**
2. **Verificar GitHub Actions**: Ve a la pestaña Actions del repositorio
3. **Verificar logs del servidor**:
   ```bash
   sudo journalctl -u docker-webhook -f
   tail -f /var/log/docker-update.log
   ```

---

## 🔧 Mantenimiento

### Comandos Útiles

```bash
# Ver estado del servicio
sudo systemctl status docker-webhook

# Reiniciar servicio
sudo systemctl restart docker-webhook

# Ver logs del webhook
sudo journalctl -u docker-webhook -n 50

# Ver logs de actualización
tail -f /var/log/docker-update.log

# Ver contenedores actuales
docker-compose ps

# Actualización manual
sudo /opt/scripts/docker-update.sh
```

### Rotación de Logs

```bash
# Crear configuración para logrotate
sudo nano /etc/logrotate.d/docker-webhook

# Contenido:
/var/log/docker-update.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
```

---

## 🚨 Troubleshooting

### Problema: Servicio no inicia

```bash
# Ver errores detallados
sudo journalctl -u docker-webhook -n 50

# Verificar archivo de servicio
sudo systemctl cat docker-webhook

# Verificar permisos
ls -la /opt/scripts/
```

### Problema: Webhook no responde

```bash
# Verificar puerto
sudo netstat -tlnp | grep :9000

# Verificar logs
sudo journalctl -u docker-webhook -f

# Probar conectividad local
curl http://localhost:9000/webhook/health
```

### Problema: GitHub Actions falla

1. **Verificar secrets** en GitHub repository settings
2. **Ver logs del workflow** en la pestaña Actions
3. **Verificar conectividad**:
   ```bash
   # Desde otra máquina
   curl https://acceso.informaticauaint.com/webhook/health
   ```

### Problema: Contenedores no se actualizan

```bash
# Verificar imágenes
docker images | grep ashby4469

# Forzar actualización manual
docker-compose pull
docker-compose up -d --force-recreate

# Ver logs del script
tail -f /var/log/docker-update.log
```

### Logs de Debug

```bash
# Ver todo el proceso en tiempo real
sudo journalctl -u docker-webhook -f &
tail -f /var/log/docker-update.log &

# Hacer push y observar logs
```

---

## 📞 Soporte

### Archivos de Configuración Clave

- `/opt/scripts/docker-update.sh` - Script de actualización
- `/opt/scripts/webhook-server.py` - Servidor webhook
- `/etc/systemd/system/docker-webhook.service` - Servicio systemd
- `/var/log/docker-update.log` - Logs de actualización
- `docker-compose.yml` - Configuración de contenedores

### Comandos de Diagnóstico

```bash
# Estado completo del sistema
sudo systemctl status docker-webhook
docker-compose ps
curl -I https://acceso.informaticauaint.com/webhook/health
sudo netstat -tlnp | grep :9000

# Test completo manual
echo "Testing webhook system..."
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": "diagnostico"}' \
  https://acceso.informaticauaint.com/webhook/docker-update
```

---

## 🎯 Resumen de Archivos

| Archivo | Ubicación | Propósito |
|---------|-----------|-----------|
| `docker-update.sh` | `/opt/scripts/` | Script actualización containers |
| `webhook-server.py` | `/opt/scripts/` | Servidor recepción webhooks |
| `docker-webhook.service` | `/etc/systemd/system/` | Servicio systemd |
| `ci-cd.yml` | `.github/workflows/` | GitHub Actions workflow |
| `docker-compose.yml` | `/path/to/project/` | Configuración containers |

¡Sistema listo para producción! 🚀
