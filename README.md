# Team Balancer

Pequeña app en Streamlit para generar equipos balanceados a partir de una lista de jugadores.

## Requisitos
- Windows (PowerShell)
- Python 3.11 (se probó con 3.11.9)

## Instalación (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar la app
```powershell
# Con el entorno activado
python -m streamlit run app.py
# Luego abrir http://localhost:8501 en el navegador
```

## Tests
```powershell
# Con el entorno activado
python -m pytest -q
```

## Variables de entorno importantes

- `MAX_BACKUPS` (opcional): controla cuántas copias de seguridad antiguas se mantienen para el fichero de persistencia SQLite. Valor por defecto: `5`.
- `LOG_LEVEL` (opcional): nivel de logging para la app. Valores típicos: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Valor por defecto: `INFO`.
- `SENTRY_DSN` (opcional): si lo configuras, la app inicializará `sentry-sdk` para reportar errores (usa `SENTRY_TRACES_SAMPLE_RATE` para controlar sampling).

Ejemplo (PowerShell):
```powershell
$env:MAX_BACKUPS = "3"
$env:LOG_LEVEL = "DEBUG"
$env:SENTRY_DSN = "https://<key>@sentry.io/<project>"
python -m streamlit run app.py
```

## Publicación de la imagen Docker (CI)

El repositorio incluye un workflow (`.github/workflows/docker-build.yml`) que construye y publica la imagen en GitHub Container Registry (GHCR). Además, el workflow puede opcionalmente publicar en Docker Hub si configuras los secrets correspondientes.

Secrets necesarios para GHCR
- `GITHUB_TOKEN` (ya disponible automáticamente en Actions) — usado para autenticarse en `ghcr.io`.

Secrets necesarios para Docker Hub (opcional)
- `DOCKERHUB_USERNAME` — tu usuario en Docker Hub.
- `DOCKERHUB_TOKEN` — token/password para autenticación (mejor usar un Access Token de Docker Hub).

Cómo configurar los secrets (GitHub):
1. Ve a `Settings` → `Secrets and variables` → `Actions` en tu repositorio.
2. Pulsa `New repository secret` y crea `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` (si quieres publicar en Docker Hub).

Comportamiento del workflow
- Siempre: construye la imagen multi-arch y la publica en GHCR como `ghcr.io/<owner>/team-balancer:latest`.
- Opcional: si `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` están definidos en los secrets, hará login en Docker Hub y publicará `docker.io/<username>/team-balancer:latest`.

Nota de permisos
- Para publicar en GHCR con `GITHUB_TOKEN` no suele requerir más configuración; para Docker Hub necesitas crear un token en Docker Hub y guardarlo en `DOCKERHUB_TOKEN`.

Ejemplo rápido (configuración local antes de push):
```powershell
# Exportar variables localmente para pruebas (no confundir con secrets de GitHub)
$env:LOG_LEVEL = "INFO"
$env:MAX_BACKUPS = "5"
python -m streamlit run app.py
```

## Notas
- `requirements.txt` contiene versiones pineadas para reproducibilidad.

## Persistencia y migraciones
La aplicación usa SQLite (`jugadores.db`) como backend de persistencia. El módulo `core_db.py` inicializa la base de datos, ejecuta lecturas/escrituras transaccionales y gestiona backups rotativos según `MAX_BACKUPS`.

Si necesitas ayuda con migraciones de esquema, exportaciones o copias de seguridad remotas, puedo añadir utilidades o scripts específicos para tu flujo.
