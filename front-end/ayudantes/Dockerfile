# Dockerfile para Ayudantes
FROM nginx:alpine

# Copiar los archivos estáticos construidos
COPY dist/ /usr/share/nginx/html/

# Copiar configuración personalizada de nginx (opcional)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

# Comando por defecto
CMD ["nginx", "-g", "daemon off;"]
