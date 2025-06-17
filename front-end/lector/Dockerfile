# Dockerfile para Lector QR
FROM node:18-alpine AS build

# Instalar dependencias del sistema
RUN apk add --no-cache git

# Crear directorio de trabajo
WORKDIR /app

# Copiar package.json y package-lock.json
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar código fuente
COPY . .

# Build para web
RUN npm run build:web

# Etapa de producción con nginx
FROM nginx:alpine

# Copiar los archivos construidos
COPY --from=build /app/dist /usr/share/nginx/html/

# Copiar configuración personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

# Comando por defecto
CMD ["nginx", "-g", "daemon off;"]