# api.Dockerfile (Crear en el directorio raíz)
FROM python:3.11
WORKDIR /app
# Copia todo el contenido del directorio back-end
COPY ./back-end /app
# Instalar dependencias + Gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn
# Exponer HTTPS
EXPOSE 443
# Arrancar Gunicorn con SSL
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:443", "--certfile=/app/certificate.pem", "--keyfile=/app/privatekey.pem", "api:app"]
