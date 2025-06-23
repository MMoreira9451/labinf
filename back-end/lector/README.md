# QR Temporal API

A lightweight Flask service that validates temporary QR codes for students and helpers. It records entries/exits and provides helper endpoints.

## Dependencies

(Installed via the Dockerfile)

```
Flask==2.3.3
flask-cors==4.0.0
PyMySQL==1.1.0
gunicorn==21.2.0
python-dotenv==1.1.0
```

## Environment variables

- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `MYSQL_PORT` – database connection.
- `SECRET_KEY` – Flask secret.
- `HOST`, `PORT` – address for the service when run directly.
- `FLASK_ENV` – controls debug mode.
- `LOG_LEVEL` – logging level.
- `CORS_ORIGINS` – allowed origins.

## Running

Typical development start:

```bash
python api_qr_temporal.py
```

Docker usage builds and runs the service under gunicorn:

```bash
docker build -t qr-temporal .
docker run -p 5000:5000 qr-temporal
```

## API endpoints

The service exposes the following routes:

- `POST /validate-qr` – validate a QR code and register entry/exit.
- `POST /verify-student` – check if a student exists.
- `POST /verify-helper` – check if a helper exists.
- `GET /get-last-records` – return recent records.
- `GET /stats` – statistics for the current day.
- `GET /health` – health check.
