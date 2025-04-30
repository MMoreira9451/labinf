
# web.Dockerfile (Crear en el directorio raíz)
FROM nginx:alpine
# Copia el build de Expo Web a la carpeta pública de Nginx
COPY ./web-dist /usr/share/nginx/html
# Copia la configuración de nginx (debes crear este archivo)
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
