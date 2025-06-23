# front-end/web/Dockerfile
# Etapa 1: Build de la aplicación Expo
FROM node:18-alpine AS build

# Metadatos
LABEL maintainer="acceso.informaticauaint.com"
LABEL description="Frontend Web para sistema de acceso QR"

# Variables de entorno para el build
ENV NODE_ENV=production \
    NPM_CONFIG_PREFIX=/home/node/.npm-global \
    PATH=/home/node/.npm-global/bin:$PATH

# Instalar dependencias del sistema necesarias para Expo
RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++

# Instalar Expo CLI globalmente
RUN npm install -g @expo/cli@latest

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias primero (para aprovechar cache)
COPY package.json package-lock.json* ./

# Instalar dependencias con npm ci para builds determinísticos
RUN npm ci --only=production

# Copiar el resto del código fuente
COPY . .

# Instalar dependencias específicas de Expo si es necesario
RUN npx expo install --fix

# Exportar la aplicación para web (genera archivos estáticos)
RUN npx expo export -p web --output-dir dist

# Etapa 2: Servidor de producción con Nginx
FROM nginx:alpine AS production

# Metadatos para la imagen final
LABEL maintainer="acceso.informaticauaint.com"
LABEL description="Frontend Web estático para sistema de acceso QR"
LABEL stage="production"

# Copiar configuración personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar archivos estáticos desde la etapa de build
COPY --from=build /app/dist /usr/share/nginx/html

# Crear usuario nginx si no existe y ajustar permisos
RUN addgroup -g 101 -S nginx || true && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Cambiar a usuario no-root
USER nginx

# Exponer puerto 8080 (puerto no privilegiado)
EXPOSE 8080

# Health check para verificar que Nginx está funcionando
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Comando para ejecutar Nginx
CMD ["nginx", "-g", "daemon off;"]