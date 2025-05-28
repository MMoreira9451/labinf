# back-end/lector/Dockerfile
FROM python:3.11-slim

# Metadatos
LABEL maintainer="acceso.informaticauaint.com"
LABEL description="API Lector QR temporal para sistema de acceso"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=api_qr_temporal.py \
    FLASK_ENV=production

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivo principal
COPY api_qr_temporal.py .

# Crear requirements.txt para la API QR
RUN echo "Flask==2.3.3" > requirements.txt && \
    echo "flask-cors==4.0.0" >> requirements.txt && \
    echo "PyMySQL==1.1.0" >> requirements.txt && \
    echo "gunicorn==21.2.0" >> requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Cambiar propietario de archivos
RUN chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 5000

# Comando de salud
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Comando por defecto
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "api_qr_temporal:app"]
