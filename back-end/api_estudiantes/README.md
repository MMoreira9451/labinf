# Estudiantes API

This module implements the REST API for student access using Flask. It exposes endpoints to register student presence, manage student data and validate QR codes.

## Dependencies

```
Flask==3.0.0
Flask-CORS==4.0.0
mysql-connector-python==8.2.0
python-dotenv==1.0.0
gunicorn==21.2.0
python-dateutil==2.8.2
pytest==7.4.3
pytest-flask==1.3.0
black==23.11.0
flake8==6.1.0
```

## Environment variables

- `SECRET_KEY` – Flask secret.
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` – MySQL settings.
- `HOST`, `PORT` – bind address for the server.
- `FLASK_ENV` – set to `development` for debug mode.

Variables are loaded via `python-dotenv`.

## Running

The service can be started directly with:

```bash
python run.py
```

In production you may run `gunicorn`:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

## API endpoints

`routes/` defines several groups:

- `/estudiantes_presentes/estudiantes` – list all students and mark presence.
- `/estudiantes` – CRUD operations for students.
- `/registros` and related endpoints – retrieve register logs.
- `/qr/*` – validate QR codes and check status/history.
- `/api/health` – basic health check.

See the route files for further details.
back-end/lector/README.md
New
+50
-0

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
back-end/web/README.md
New
+64
-0

# Web API

This service exposes the main Flask application used by the system to manage helpers and records.

## Dependencies

Contents of `requirements.txt`:

```
Flask==2.3.3
flask-cors==4.0.0
PyMySQL==1.1.0
PyJWT==2.8.0
cryptography==41.0.3
pytz==2023.3
APScheduler==3.10.4
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
Werkzeug==2.3.7
```

## Environment variables

- `JWT_SECRET` – secret key for JWT tokens.
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `MYSQL_PORT` – MySQL connection settings.
- `DB_CHARSET` – charset for the database (default `utf8mb4`).

Variables are normally loaded from a `.env` file or the environment.

## Running

For development the application can be started with:

```bash
python app.py
```

For production the included Dockerfile runs gunicorn:

```bash
docker build -t horarios-web .
docker run -p 5000:5000 horarios-web
```

## Scheduled tasks

`tasks/scheduled_tasks.py` defines two APScheduler jobs:

- **Daily closing** – POSTs to `/api/procesar_salidas_pendientes` every day at `23:59`.
- **Weekly reset** – POSTs to `/reiniciar_cumplimiento` every Sunday at `23:55`.

## API endpoints

Endpoints are grouped in blueprints. Some notable routes are:

- `POST /api/ayudantes/register` – register an administrator.
- `GET /registros`, `GET /registros_hoy` – obtain records.
- `GET /usuarios` – list allowed users.
- `GET /cumplimiento` – fetch compliance status.
- `GET /horas_acumuladas` – total hours worked.
- `GET /estado_usuarios` – status of all users.

Refer to the code inside `routes/` for the full list.
