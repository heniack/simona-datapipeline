# Documentación Técnica - Simona DataPipeline

**Versión:** 1.1  
**Fecha:** Mayo 2026  
**Desarrollador:** Juan Vilanova

---

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Modelos de Datos](#modelos-de-datos)
6. [Funcionalidades Principales](#funcionalidades-principales)
7. [Sistema de Cifrado](#sistema-de-cifrado)
8. [Scheduler y Automatización](#scheduler-y-automatización)
9. [Guía de Instalación](#guía-de-instalación)
10. [Configuración](#configuración)
11. [API y Endpoints](#api-y-endpoints)
12. [Flujos de Trabajo](#flujos-de-trabajo)
13. [Seguridad](#seguridad)

---

## Descripción General

Simona DataPipeline es una aplicación web de sincronización automática de datos PostgreSQL hacia servicios de almacenamiento en la nube (Google Drive y Amazon S3). Incluye un sistema de limpieza automática de datos antiguos basado en políticas de retención configurables.

### Características Principales

- ✅ Sincronización incremental de tablas PostgreSQL
- ✅ Múltiples destinos: Google Drive y Amazon S3
- ✅ Detección automática de cambios de esquema
- ✅ Limpieza automática de datos obsoletos
- ✅ Scheduler para ejecución programada
- ✅ OAuth 2.0 para Google Drive
- ✅ Cifrado AES de credenciales sensibles
- ✅ Historial de ejecuciones
- ✅ Interfaz web responsive

---

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMONA DATAPIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Frontend   │◄────►│   Backend    │                    │
│  │   Bootstrap  │      │    Django    │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                               │                              │
│                    ┌──────────┴──────────┐                  │
│                    │                     │                  │
│            ┌───────▼────────┐   ┌───────▼────────┐         │
│            │   Scheduler    │   │   Encryption   │         │
│            │  APScheduler   │   │   Fernet/AES   │         │
│            └───────┬────────┘   └────────────────┘         │
│                    │                                         │
│       ┌────────────┼────────────┐                           │
│       │            │            │                           │
│  ┌────▼─────┐ ┌───▼────┐ ┌────▼──────┐                    │
│  │PostgreSQL│ │ Google │ │ Amazon S3 │                    │
│  │  Sync    │ │ Drive  │ │  Upload   │                    │
│  └────┬─────┘ └───┬────┘ └────┬──────┘                    │
│       │           │            │                            │
└───────┼───────────┼────────────┼────────────────────────────┘
        │           │            │
        ▼           ▼            ▼
   PostgreSQL  Google Drive  Amazon S3
   (Cliente)    API v3        Bucket
```

### Capas de la Aplicación

1. **Capa de Presentación**: Templates HTML + Bootstrap 5.3 + Bootstrap Icons
2. **Capa de Aplicación**: Django Views + Forms
3. **Capa de Lógica de Negocio**: Services (PostgreSQLSync, GoogleDriveUploader, S3Uploader, CleanupOrchestrator)
4. **Capa de Datos**: Django ORM + PostgreSQL
5. **Capa de Integración**: APIs externas (Google Drive, AWS S3, PostgreSQL)
6. **Capa de Automatización**: APScheduler con BackgroundScheduler

---

## Stack Tecnológico

### Backend
- **Python**: 3.13
- **Django**: 4.2.3
- **Base de Datos**: PostgreSQL (metadata de la app y fuente de datos)

### Librerías de Integración
- **psycopg2-binary**: 2.9.11 - Conexión PostgreSQL
- **google-auth-oauthlib**: 1.3.0 - OAuth 2.0 para Google
- **google-auth-httplib2**: 0.3.0 - Cliente HTTP para Google APIs
- **google-api-python-client**: 2.192.0 - Google Drive API v3
- **boto3**: 1.24.39 - AWS SDK para S3

### Automatización y Seguridad
- **APScheduler**: 3.11.2 - Scheduler de tareas en segundo plano
- **cryptography**: 46.0.5 - Cifrado Fernet (AES)

### Frontend
- **Bootstrap**: 5.3.0
- **Bootstrap Icons**: 1.11.0
- **Tipografía**: Inter (Google Fonts)
- **CSS**: Centralizado con custom properties (variables)
- **JavaScript**: Vanilla JS (interacciones dinámicas)

---

## Estructura del Proyecto

```
simona_datapipeline/
├── manage.py                    # CLI de Django
├── client_secret.json           # Credenciales OAuth Google (no versionado)
├── simona_datapipeline/         # Configuración del proyecto
│   ├── settings.py              # Settings de Django
│   ├── urls.py                  # URLs raíz
│   └── wsgi.py                  # WSGI entry point
└── core/                        # App principal
    ├── models.py                # Modelos: Connector, SyncTask, CleanupTask, etc.
    ├── views.py                 # Vistas: 24 endpoints
    ├── urls.py                  # URLs de la app
    ├── forms.py                 # Formularios: ConnectorForm, ConnectorEditForm, SyncTaskForm, CleanupTaskForm
    ├── services.py              # Lógica de negocio: PostgreSQLSync, GoogleDriveUploader, S3Uploader, CleanupOrchestrator
    ├── scheduler.py             # Configuración APScheduler
    ├── encryption.py            # Sistema de cifrado Fernet
    ├── apps.py                  # AppConfig (inicio del scheduler)
    ├── admin.py                 # Django Admin
    ├── migrations/              # Migraciones de base de datos (10 archivos)
    ├── static/core/
    │   ├── css/styles.css       # Estilos centralizados (CSS variables, ~400 líneas)
    │   └── images/logo_simona.jpg
    └── templates/core/          # Templates HTML (15 archivos)
        ├── base.html            # Template base (navbar, sidebar, footer, toasts)
        ├── home.html            # Landing page / Dashboard autenticado
        ├── login.html           # Autenticación (standalone)
        ├── signup.html          # Registro (standalone)
        ├── settings.html        # Configuración de cuenta
        ├── help.html            # Documentación
        ├── connector_list.html  # Lista de conectores (Google Drive / S3)
        ├── create_connector.html
        ├── edit_connector.html  # Edición: nombre, frecuencia, tablas (read-only para conexión)
        ├── select_tables.html   # Selección de tablas post-creación
        ├── sync_task_list.html  # Historial de sincronizaciones
        ├── create_sync_task.html
        ├── cleanup_task_list.html
        ├── create_cleanup_task.html
        └── cleanup_task_detail.html
```

---

## Modelos de Datos

### UserProfile
Extiende el modelo User de Django con información adicional.

```python
UserProfile
├── user: OneToOneField(User) - Relación con usuario Django
├── role: CharField - 'admin' | 'user'
└── created_at: DateTimeField
```

### Connector
Representa una conexión PostgreSQL con destino de sincronización.

```python
Connector
├── user: ForeignKey(User) - Propietario del conector
├── name: CharField(100) - Nombre descriptivo
├── is_active: BooleanField - Estado activo/inactivo
├── sync_frequency: IntegerField - Frecuencia en minutos (5, 15, 30, 60, 360, 1440)
│
├── # Credenciales PostgreSQL (cifradas)
├── pg_host: CharField(255)
├── pg_port: IntegerField
├── pg_database: CharField(100)
├── pg_user: CharField(100) - Default: 'simona_user'
├── pg_password: CharField(500) - Cifrada con Fernet
│
├── # Destino
├── destination_type: CharField - 'google_drive' | 's3'
│
├── # Google Drive (OAuth)
├── drive_folder_url: URLField - URL de carpeta destino
├── google_refresh_token: CharField - Token OAuth refresh
├── oauth_state: CharField - Estado OAuth temporal
│
├── # Amazon S3 (IAM)
├── s3_bucket_name: CharField
├── s3_region: CharField
├── s3_access_key: CharField
├── s3_secret_key: CharField(500) - Cifrada con Fernet
│
└── Timestamps: created_at, updated_at

Métodos:
- get_pg_password() -> str: Descifra y retorna la contraseña
- get_s3_secret_key() -> str: Descifra y retorna el secret key
```

### SyncTask
Representa una tabla específica a sincronizar dentro de un conector.

```python
SyncTask
├── connector: ForeignKey(Connector) - Conector padre
├── table_name: CharField(100) - Nombre de la tabla PostgreSQL
├── timestamp_column: CharField(100) - Columna para sincronización incremental (default: 'updated_at')
├── last_sync_time: DateTimeField - Último timestamp sincronizado
├── last_schema: TextField - Schema JSON de la última sincronización
├── status: CharField - 'pending' | 'running' | 'success' | 'failed'
├── last_execution_at: DateTimeField
├── records_synced: IntegerField - Total de registros sincronizados
└── Timestamps: created_at, updated_at
```

### SyncExecution
Historial de ejecuciones completas de sincronización.

```python
SyncExecution
├── connector: ForeignKey(Connector)
├── status: CharField - 'running' | 'success' | 'partial' | 'failed'
├── trigger: CharField - 'manual' | 'automatic'
├── tables_synced: IntegerField - Tablas sincronizadas exitosamente
├── tables_failed: IntegerField - Tablas con error
├── total_records: IntegerField - Total de registros procesados
├── error_message: TextField
├── started_at: DateTimeField
└── finished_at: DateTimeField

Propiedades:
- duration: Calcula duración en formato "Xm Ys"
```

### CleanupTask
Tarea de limpieza automática de datos antiguos.

```python
CleanupTask
├── user: ForeignKey(User)
├── name: CharField(100) - Nombre descriptivo
│
├── # Conexión PostgreSQL (cifrada)
├── pg_host: CharField(255)
├── pg_port: IntegerField
├── pg_database: CharField(100)
├── pg_user: CharField(100)
├── pg_password: CharField(500) - Cifrada con Fernet
│
├── # Configuración de limpieza
├── table_name: CharField(100)
├── timestamp_column: CharField(100)
│
├── # Política de retención
├── retention_months: IntegerField(0-12)
├── retention_days: IntegerField(0-365)
├── retention_hours: IntegerField(0-24)
│
├── # Frecuencia
├── cleanup_frequency: IntegerField - 60, 360, 720, 1440 minutos
│
├── # Estado
├── is_active: BooleanField
├── last_cleanup_at: DateTimeField
└── Timestamps: created_at, updated_at

Métodos:
- get_pg_password() -> str: Descifra y retorna la contraseña
- retention_display: Formatea retención en texto legible
```

### CleanupExecution
Historial de ejecuciones de limpieza.

```python
CleanupExecution
├── cleanup_task: ForeignKey(CleanupTask)
├── status: CharField - 'running' | 'success' | 'failed'
├── rows_deleted: IntegerField
├── error_message: TextField
├── started_at: DateTimeField
└── finished_at: DateTimeField

Propiedades:
- duration: Calcula duración en formato "Xm Ys"
```

### GoogleDriveToken
Tokens OAuth para acceso a Google Drive.

```python
GoogleDriveToken
├── user: ForeignKey(User)
├── google_refresh_token: CharField(500)
├── google_access_token: CharField(500)
├── token_expiry: DateTimeField
├── client_id: CharField(500)
├── client_secret: CharField(500)
├── scopes: TextField
└── Timestamps: created_at, updated_at
```

---

## Funcionalidades Principales

### 1. Gestión de Conectores

#### Google Drive
- **Autenticación OAuth 2.0**: Flujo completo con refresh tokens
- **Estructura de carpetas**: `carpeta_drive/nombre_db/nombre_tabla/archivo.csv`
- **Archivos CSV**: Exportación con codificación UTF-8
- **Versionado**: Archivos antiguos se reemplazan por nuevas versiones

#### Amazon S3
- **Autenticación IAM**: Access Key + Secret Key
- **Estructura de carpetas**: `bucket/nombre_db/nombre_tabla/archivo.csv`
- **Regiones**: Soporte multi-región
- **Permisos requeridos**: `s3:PutObject`, `s3:GetObject`

### 2. Sincronización Incremental

**Algoritmo:**
1. Consultar PostgreSQL con filtro `WHERE timestamp_column > last_sync_time`
2. Comparar esquema actual con `last_schema` guardado
3. Si el esquema cambió:
   - Eliminar archivo anterior en destino
   - Sincronizar todos los registros (full sync)
4. Si el esquema no cambió:
   - Agregar solo registros nuevos/modificados
5. Actualizar `last_sync_time` con el timestamp más reciente
6. Guardar esquema actual en `last_schema`

**Ventajas:**
- Minimiza transferencia de datos
- Detecta cambios de estructura (ADD/DROP COLUMN)
- Mantiene consistencia de datos

### 3. Limpieza Automática

**Política de Retención:**
```python
threshold = now - (months * 30 days + days + hours)
DELETE FROM tabla WHERE timestamp_column < threshold
```

**Proceso:**
1. Calcular fecha límite según retención configurada
2. Ejecutar `DELETE FROM tabla WHERE campo < fecha_limite`
3. Contar filas eliminadas
4. Guardar ejecución en `CleanupExecution`

**Frecuencias disponibles:** 1, 6, 12, 24 horas

### 4. Sistema de Autenticación

- **Registro**: Formulario personalizado en español con email
- **Login**: Autenticación Django estándar
- **Logout**: Redirección a home page
- **Configuración**: Cambio de username, email, contraseña
- **Contraseñas hasheadas**: Django PBKDF2 (usuarios)

---

## Sistema de Cifrado

### Implementación: Fernet (AES-128)

**Archivo:** `core/encryption.py`

```python
# Derivación de clave desde SECRET_KEY
key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
fernet_key = base64.urlsafe_b64encode(key)
cipher = Fernet(fernet_key)

# Cifrado
encrypted = cipher.encrypt(password.encode())

# Descifrado
decrypted = cipher.decrypt(encrypted_password.encode())
```

### Campos Cifrados

- `Connector.pg_password` → `get_pg_password()`
- `Connector.s3_secret_key` → `get_s3_secret_key()`
- `CleanupTask.pg_password` → `get_pg_password()`

### Características

- **Cifrado simétrico**: Misma clave para cifrar/descifrar
- **Autenticación**: Previene manipulación de datos cifrados
- **Prefijo identificable**: Comienza con `gAAAAA`
- **Backward compatible**: Detecta texto plano durante migración

---

## Scheduler y Automatización

### APScheduler Configuration

**Archivo:** `core/scheduler.py`

```python
scheduler = BackgroundScheduler(
    timezone='America/Argentina/Buenos_Aires',
    job_defaults={
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 300
    }
)
```

### Tipos de Jobs

#### 1. Sincronización de Conectores
```python
job_id = f"sync_connector_{connector.id}"
scheduler.add_job(
    func=sync_connector_now,
    trigger='interval',
    minutes=connector.sync_frequency,
    id=job_id,
    args=[connector.id],
    replace_existing=True
)
```

#### 2. Limpieza Automática
```python
job_id = f"cleanup_task_{cleanup_task.id}"
scheduler.add_job(
    func=execute_cleanup,
    trigger='interval',
    minutes=cleanup_task.cleanup_frequency,
    id=job_id,
    args=[cleanup_task.id],
    replace_existing=True
)
```

### Inicio del Scheduler

El scheduler se inicia automáticamente al levantar Django:

**Archivo:** `core/apps.py`
```python
def ready(self):
    from .scheduler import start_scheduler
    start_scheduler()
```

### Gestión de Jobs

- **Agregar job**: `schedule_connector(connector)` / `schedule_cleanup_task(task)`
- **Remover job**: `remove_connector_job(connector_id)` / `remove_cleanup_job(task_id)`
- **Listar jobs**: `scheduler.get_jobs()`
- **Próxima ejecución**: `job.next_run_time`

---

## Guía de Instalación

### Requisitos Previos

- Python 3.10+
- pip
- PostgreSQL 12+ (para conectarse como cliente)
- Cuenta Google Cloud (para Google Drive)
- Cuenta AWS (para S3)

### Pasos de Instalación

```bash
# 1. Clonar repositorio
cd "/Users/juan.vilanova/Desktop/Simona version final"

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install django psycopg2-binary APScheduler \
    google-auth-oauthlib google-auth-httplib2 \
    google-api-python-client boto3 cryptography

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear superusuario (opcional)
python manage.py createsuperuser

# 6. Iniciar servidor
python manage.py runserver
```

### Acceso
- URL: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Configuración

### SECRET_KEY de Django

**Ubicación:** `simona_datapipeline/settings.py`

⚠️ **Crítico:** El `SECRET_KEY` se usa para:
- Cifrado de cookies y sesiones
- Derivación de clave Fernet para cifrado de contraseñas
- Tokens CSRF

**NO compartir en repositorios públicos.**

### Google Drive OAuth

1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com/)
2. Activar Google Drive API
3. Crear credenciales OAuth 2.0
4. Descargar `client_secret.json` → raíz del proyecto
5. Agregar URI de redirección: `http://127.0.0.1:8000/google/oauth2callback/`

**Scopes requeridos:**
```python
SCOPES = ['https://www.googleapis.com/auth/drive.file']
```

### Amazon S3

**Permisos IAM mínimos:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::tu-bucket/*"
    }
  ]
}
```

### PostgreSQL (Cliente)

**Usuario requerido para sincronización:**
```sql
CREATE USER simona_user WITH PASSWORD 'tu_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO simona_user;
```

**Usuario requerido para limpieza:**
```sql
GRANT SELECT, DELETE ON TABLE nombre_tabla TO simona_user;
```

---

## API y Endpoints

### Autenticación

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Home page (público) |
| `/signup/` | GET/POST | Registro de usuario |
| `/login/` | GET/POST | Inicio de sesión |
| `/logout/` | GET | Cierre de sesión |
| `/settings/` | GET/POST | Configuración de cuenta |
| `/help/` | GET | Documentación |

### Conectores

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/connectors/google-drive/` | GET | Lista conectores Google Drive |
| `/connectors/amazon-s3/` | GET | Lista conectores Amazon S3 |
| `/connectors/create/` | GET/POST | Crear conector |
| `/connectors/<id>/edit/` | GET/POST | Editar conector |
| `/connectors/<id>/delete/` | POST | Eliminar conector |
| `/connectors/<id>/select-tables/` | GET/POST | Seleccionar tablas |
| `/connectors/<id>/sync-now/` | GET | Sincronizar manualmente |

### OAuth Google Drive

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/google/authorize/` | GET | Iniciar flujo OAuth |
| `/oauth2callback` | GET | Callback OAuth con código |

### Tareas de Sincronización

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/sync-tasks/<connector_id>/` | GET | Historial de sincronizaciones |
| `/sync-tasks/<connector_id>/create/` | GET/POST | Crear tarea manual |
| `/connectors/<id>/sync-tables-now/` | GET | Sincronizar desde listado |

### Tareas de Limpieza

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/cleanup-tasks/` | GET | Lista tareas de limpieza |
| `/cleanup-tasks/create/` | GET/POST | Crear tarea limpieza |
| `/cleanup-tasks/<id>/` | GET | Detalle tarea |
| `/cleanup-tasks/<id>/execute/` | GET | Ejecutar limpieza manual |
| `/cleanup-tasks/<id>/toggle/` | POST | Activar/desactivar |
| `/cleanup-tasks/<id>/delete/` | POST | Eliminar tarea |

### AJAX Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/cleanup-tasks/create/` | POST (AJAX) | Obtener columnas timestamp de tabla |

**Request:**
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "db_name",
  "user": "simona_user",
  "password": "password",
  "table_name": "users"
}
```

**Response:**
```json
{
  "success": true,
  "columns": ["created_at", "updated_at", "last_login"]
}
```

---

## Flujos de Trabajo

### Flujo: Crear Conector Google Drive

```
1. Usuario: Click "Configurar Google Drive"
   ↓
2. Sistema: Genera oauth_state único
   ↓
3. Sistema: Redirige a Google OAuth consent screen
   ↓
4. Usuario: Autoriza permisos en Google
   ↓
5. Google: Redirige a /google/oauth2callback/?code=xxx&state=xxx
   ↓
6. Sistema: Valida state, intercambia code por tokens
   ↓
7. Sistema: Guarda refresh_token cifrado
   ↓
8. Usuario: Completa formulario (nombre, host, DB, frecuencia, carpeta)
   ↓
9. Sistema: Cifra pg_password y guarda Connector
   ↓
10. Redirect: /connectors/<id>/select-tables/
   ↓
11. Sistema: Detecta tablas con columna updated_at
   ↓
12. Usuario: Selecciona tablas a sincronizar
   ↓
13. Sistema: Crea SyncTask por cada tabla
   ↓
14. Sistema: Programa job en APScheduler
   ↓
15. Sistema: Ejecuta primera sincronización (full)
   ↓
16. Redirect: Lista de conectores Google Drive
```

### Flujo: Sincronización Automática

```
Scheduler trigger (cada X minutos)
   ↓
sync_connector_now(connector_id)
   ↓
Crea SyncExecution(status='running')
   ↓
Para cada SyncTask del connector:
   ├─ Conecta a PostgreSQL (contraseña descifrada)
   ├─ Compara esquema actual vs last_schema
   ├─ Si cambió esquema:
   │  ├─ Elimina archivo anterior en destino
   │  └─ Sincroniza todos los registros
   ├─ Si esquema igual:
   │  └─ Sincroniza registros WHERE timestamp > last_sync_time
   ├─ Genera CSV en memoria
   ├─ Sube a Google Drive o S3
   ├─ Actualiza last_sync_time y last_schema
   └─ Marca SyncTask como 'success' o 'failed'
   ↓
Actualiza SyncExecution con totales
   ↓
Marca como 'success', 'partial' o 'failed'
```

### Flujo: Limpieza Automática

```
Scheduler trigger (cada X horas)
   ↓
execute_cleanup(cleanup_task_id)
   ↓
Crea CleanupExecution(status='running')
   ↓
Calcula threshold:
   threshold = now - (months*30 + days + hours/24)
   ↓
Conecta a PostgreSQL (contraseña descifrada)
   ↓
Ejecuta:
   DELETE FROM tabla 
   WHERE timestamp_column < threshold
   ↓
Cuenta filas eliminadas (cursor.rowcount)
   ↓
Actualiza CleanupExecution:
   ├─ rows_deleted
   ├─ finished_at
   └─ status='success' o 'failed'
   ↓
Actualiza CleanupTask.last_cleanup_at
```

---

## Seguridad

### Cifrado de Contraseñas

**Método:** Fernet (AES-128 en modo CBC con HMAC para autenticación)

**Proceso de cifrado:**
1. Derivar clave desde `SECRET_KEY` con SHA-256
2. Codificar clave en base64 URL-safe
3. Crear instancia Fernet
4. Cifrar contraseña
5. Guardar en DB como string base64

**Detección automática:**
- Contraseñas cifradas empiezan con `gAAAAA`
- Si no empieza con ese prefijo, se cifra al guardar
- Soporte para migración de contraseñas en texto plano

### Contraseñas de Usuario

**Hasheadas con PBKDF2:** Django gestiona automáticamente con `set_password()` y `check_password()`.

**Algoritmo:** `pbkdf2_sha256$600000$<salt>$<hash>`

### Validaciones

- **Username único**: Verificación antes de actualizar
- **Email requerido**: En signup form
- **Contraseña mínima**: 8 caracteres
- **CSRF tokens**: Protección en todos los formularios
- **Login requerido**: Decorador `@login_required` en vistas sensibles

### Gestión de Secretos

⚠️ **NO versionar:**
- `client_secret.json` (OAuth Google)
- `.env` files (si se usan)
- Credenciales de base de datos PostgreSQL

✅ **Versionado:**
- `settings.py` (con SECRET_KEY generado único por instalación)

---

## Servicios (core/services.py)

### PostgreSQLSync

**Métodos principales:**

```python
get_connection() -> psycopg2.connection
    # Conecta usando credenciales cifradas descifradas

get_tables_from_database(host, port, db, user, password) -> List[str]
    # Detecta tablas con columna 'updated_at'

get_table_data(table_name, timestamp_column, last_sync_time) -> tuple
    # Retorna (columns, rows, max_timestamp)
    # Sincronización incremental con WHERE clause

detect_schema_change(sync_task) -> bool
    # Compara esquema actual con last_schema JSON
```

### GoogleDriveUploader

**Métodos principales:**

```python
get_drive_service(connector) -> googleapiclient.discovery.Resource
    # Crea cliente Google Drive con refresh token

upload_or_update_csv(csv_content, db_name, table_name, schema_changed) -> str
    # Estructura: drive_folder/db_name/table_name/archivo.csv
    # Si schema_changed: elimina archivo anterior
    # Retorna file_id

extract_folder_id(url) -> str
    # Parsea Google Drive folder URL
```

### S3Uploader

**Métodos principales:**

```python
get_s3_client() -> boto3.client
    # Crea cliente S3 con credenciales descifradas

upload_csv(csv_content, db_name, table_name, schema_changed) -> str
    # Estructura: bucket/db_name/table_name/archivo.csv
    # Si schema_changed: elimina archivo anterior
    # Retorna object_key
```

### CleanupOrchestrator

**Métodos principales:**

```python
get_connection() -> psycopg2.connection
    # Conecta usando contraseña cifrada descifrada

get_timestamp_columns(host, port, db, user, password, table) -> List[str]
    # Retorna columnas de tipo timestamp/timestamptz/datetime

execute_cleanup() -> int
    # Calcula threshold y ejecuta DELETE
    # Retorna filas eliminadas
```

---

## Formularios (core/forms.py)

### ConnectorForm

**Campos:**
- name, destination_type, sync_frequency
- pg_host, pg_port, pg_database, pg_user, pg_password
- drive_folder_url (Google Drive)
- s3_bucket_name, s3_region, s3_access_key, s3_secret_key (S3)

**Widgets especiales:**
- `pg_password`: PasswordInput con `render_value=False`, `autocomplete='new-password'`
- `s3_secret_key`: PasswordInput con `render_value=False`, `autocomplete='new-password'`
- `pg_user`: TextInput con `readonly=True` (forzado a 'simona_user')

### ConnectorEditForm

**Formulario simplificado para editar un conector existente.**

**Campos:** `name`, `sync_frequency`

Solo permite cambiar el nombre y la frecuencia de sincronización. La gestión de tablas se hace por separado con checkboxes en el template `edit_connector.html`. La configuración de conexión (host, port, database, user, password) y destino (Google Drive URL, S3 bucket) se muestra como read-only.

### CleanupTaskForm

**Campos:**
- name, pg_host, pg_port, pg_database, pg_user, pg_password
- table_name, timestamp_column
- retention_months, retention_days, retention_hours
- cleanup_frequency

**Widgets especiales:**
- `timestamp_column`: Select dinámico (cargado via AJAX)
- `pg_password`: PasswordInput con `autocomplete='new-password'`

---

## Migraciones de Base de Datos

### Historial de Migraciones

1. **0001_initial.py**: UserProfile
2. **0002_connector.py**: Modelo Connector
3. **0003_synctask.py**: Modelo SyncTask
4. **0004_googledrivetoken.py**: Modelo GoogleDriveToken
5. **0005_remove_connector_google_api_key.py**: Migración a OAuth
6. **0006_synctask_last_schema.py**: Campo para detección de cambios
7. **0007_syncexecution.py**: Historial de sincronizaciones
8. **0008_synctask_last_schema.py**: Ajuste schema
9. **0009_cleanuptask_cleanupexecution.py**: Sistema de limpieza
10. **0010_encrypt_passwords.py**: Cifrado de contraseñas existentes

### Migración de Cifrado (0010)

**Proceso:**
1. Aumenta tamaño de campos: `CharField(255)` → `CharField(500)`
2. Ejecuta función `encrypt_existing_passwords()`:
   - Itera todos los Connectors
   - Detecta contraseñas en texto plano (sin prefijo `gAAAAA`)
   - Cifra `pg_password` y `s3_secret_key`
   - Itera todos los CleanupTasks
   - Cifra `pg_password`
3. Guarda cambios en DB

**Aplicación:**
```bash
python manage.py migrate
```

---

## Interfaz de Usuario

### Diseño

- **Framework:** Bootstrap 5.3.0
- **Tema:** Azul profesional (#2563eb, #3b82f6)
- **Iconos:** Bootstrap Icons 1.11.0
- **Tipografía:** Inter (Google Fonts) - pesos 300 a 800
- **CSS:** Centralizado en `core/static/core/css/styles.css` con custom properties
- **Layout:** Responsive (mobile-first)
- **Herencia:** `base.html` como template padre para todas las páginas autenticadas

### Componentes Principales

#### Navbar
- Logo con imagen (logo_simona.jpg)
- Hamburger button para sidebar
- Badge de usuario (username)
- Botón "Cerrar Sesión" / "Iniciar Sesión"

#### Sidebar Offcanvas
- Mis Conectores Google Drive (verde #10b981)
- Mis Conectores Amazon S3 (naranja #f59e0b)
- Mis Limpiezas Automáticas (rojo #ef4444)
- Configuración (morado #8b5cf6)
- Ayuda (cyan #06b6d4)

#### Cards de Conectores
- Hover effect con elevación
- Icono de tipo (Google/Amazon)
- Información de conexión
- Estado de sincronización
- Botones: Editar, Eliminar, Sincronizar Ahora

#### Mensajes Toast
- Auto-dismiss después de 5 segundos via JavaScript
- Soporta success, error, warning, info
- Integrado con `django.contrib.messages`

#### Formularios
- Validación cliente con HTML5
- Validación servidor con Django Forms
- Mensajes de error inline en login/signup
- Campos dinámicos (destination_type toggle en crear conector)

### Páginas Clave

#### Home Page
- **No autenticado:** Landing page con sección "¿Qué es Simona?", 3 feature cards, 4 pasos "Cómo funciona", 3 características técnicas, CTA con botones Login/Signup
- **Autenticado:** Dashboard con 4 feature cards (Conectores, Google Drive, S3, Limpieza) + 3 stat cards

#### Help Page
- Introducción a Simona
- Guía Google Drive (paso a paso)
- Guía Amazon S3 (paso a paso)
- Guía Sync Tasks con alerta de `updated_at = NOW()`
- Guía Limpiezas con comando `GRANT SELECT, DELETE`
- Configuración de cuenta
- FAQ

---

## Logs y Debugging

### Print Statements

**Sincronización:**
```python
print(f"DEBUG: Sincronización incremental. Last sync: {last_sync_time}")
print(f"DEBUG: Se extrajeron {len(rows)} registros")
```

**Limpieza:**
```python
print(f"🧹 Ejecutando limpieza: {cleanup_task.name}")
print(f"   Tabla: {cleanup_task.table_name}")
print(f"   Campo: {cleanup_task.timestamp_column}")
print(f"   Retención: {retention_display}")
print(f"✅ Limpieza exitosa: {rows_deleted} filas eliminadas")
```

**Scheduler:**
```python
print("============================================================")
print("🚀 INICIANDO SCHEDULER DE SINCRONIZACIÓN AUTOMÁTICA")
print("============================================================")
print(f"✓ Programado '{connector.name}' cada {connector.sync_frequency} minutos")
```

### Warnings

```python
logger.warning(f"Error al actualizar scheduler: {str(e)}")
```

---

## Mejoras Futuras

### Recomendaciones de Producción

1. **Testing**
   - Tests unitarios (models, forms, services)
   - Tests de integración (APIs externas)
   - Tests E2E (Selenium/Playwright)

2. **Logging Estructurado**
   - Reemplazar prints con `logging` module
   - Configurar handlers (file, syslog, CloudWatch)
   - Niveles apropiados (DEBUG, INFO, WARNING, ERROR)

3. **Validación Previa**
   - Test de conectividad PostgreSQL antes de guardar
   - Validación de permisos en bucket S3
   - Verificación de folder_id en Google Drive

4. **Manejo de Errores Robusto**
   - Reintentos con backoff exponencial
   - Dead letter queue para jobs fallidos
   - Alertas por email/Slack en fallos

5. **Rate Limiting**
   - Throttling de peticiones a Google Drive API (10 req/sec)
   - Throttling de peticiones a S3 (5500 req/sec write)
   - Manejo de cuotas y límites

6. **Containerización**
   - Dockerfile para deployment
   - docker-compose.yml con PostgreSQL
   - Volúmenes para persistencia de datos

7. **Variables de Entorno**
   - `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

8. **Escalabilidad**
   - Usar Celery + Redis para jobs async
   - Queue system para sincronizaciones grandes
   - Connection pooling para PostgreSQL (pgBouncer)

9. **Monitoreo**
   - Metrics de APScheduler (jobs ejecutados, fallos)
   - Dashboard de sincronizaciones (Grafana/Prometheus)
   - Health checks endpoints

10. **Backup y Recuperación**
    - Backup automático de PostgreSQL (pg_dump)
    - Export/import de configuraciones
    - Disaster recovery plan

---

## Resolución de Problemas

### Problemas Comunes

#### 1. Scheduler no inicia
**Síntoma:** Jobs no se ejecutan automáticamente

**Solución:**
```python
# Verificar en core/apps.py que ready() llama a start_scheduler()
def ready(self):
    from .scheduler import start_scheduler
    start_scheduler()
```

#### 2. Google OAuth falla
**Síntoma:** Error "redirect_uri_mismatch"

**Solución:**
- Verificar `client_secret.json` tiene URI correcto
- Agregar `http://127.0.0.1:8000/google/oauth2callback/` en Google Cloud Console

#### 3. S3 Access Denied
**Síntoma:** `botocore.exceptions.ClientError: AccessDenied`

**Solución:**
- Verificar permisos IAM: `s3:PutObject` en bucket
- Verificar region correcta
- Verificar bucket existe

#### 4. PostgreSQL Connection Failed
**Síntoma:** `psycopg2.OperationalError: could not connect`

**Solución:**
- Verificar PostgreSQL está corriendo
- Verificar host/port/database/user correctos
- Verificar contraseña (ahora cifrada, debe descifrarse)
- Verificar permisos: `GRANT SELECT ON TABLE`

#### 5. Contraseña no se descifra
**Síntoma:** `cryptography.fernet.InvalidToken`

**Solución:**
- Verificar `SECRET_KEY` no ha cambiado
- Si cambió, las contraseñas cifradas son irrecuperables
- Solución: Recrear conectores con nuevas contraseñas

---

## Glosario

- **Connector**: Conexión PostgreSQL configurada con destino (Drive/S3)
- **SyncTask**: Tabla específica dentro de un conector a sincronizar
- **SyncExecution**: Registro histórico de una ejecución completa de sincronización
- **CleanupTask**: Configuración de limpieza automática para una tabla
- **CleanupExecution**: Registro histórico de una ejecución de limpieza
- **Incremental Sync**: Sincronización solo de registros nuevos/modificados
- **Full Sync**: Sincronización de todos los registros (cuando cambia esquema)
- **Schema Change**: Detección de ADD/DROP/ALTER COLUMN en tabla
- **Retention Policy**: Política de retención de datos (meses/días/horas)
- **Job**: Tarea programada en APScheduler
- **OAuth State**: Token temporal para validar callback de Google
- **Refresh Token**: Token de larga duración para obtener access tokens

---

## Contacto y Soporte

**Desarrollador:** Juan Vilanova  
**Proyecto:** Simona DataPipeline  
**Fecha de Finalización:** 10 de marzo de 2026

---

## Licencia

Proyecto académico/personal. Todos los derechos reservados.

---

## Changelog

### v1.1 (03/05/2026) - Refactoring de Frontend

#### Templates
- ✅ Creado `base.html` como template base con navbar, sidebar offcanvas, footer y mensajes toast
- ✅ Todos los templates (excepto login/signup) ahora extienden `base.html`, eliminando ~1500 líneas de código duplicado
- ✅ Login y signup rediseñados como páginas standalone con layout `auth-wrapper`
- ✅ Home page rediseñada: landing informativa para no autenticados, dashboard con stats para autenticados
- ✅ Mensajes de error de login ahora se muestran correctamente (non_field_errors + field errors)

#### CSS
- ✅ Creado `core/static/core/css/styles.css` centralizado (~400 líneas)
- ✅ CSS custom properties (variables) para colores, sombras, radios, transiciones
- ✅ Tipografía Inter (Google Fonts) en lugar de fuente del sistema
- ✅ Paleta: `--primary: #2563eb`, `--success: #10b981`, `--warning: #f59e0b`, `--danger: #ef4444`, `--purple: #8b5cf6`, `--cyan: #06b6d4`
- ✅ Componentes: navbar, sidebar, cards, botones, formularios, tablas, badges, alertas, modales, estados vacíos, auth pages, footer, toasts
- ✅ Responsive con breakpoints para mobile

#### Edición de Conectores
- ✅ Creado `ConnectorEditForm` (solo nombre y frecuencia)
- ✅ Vista `edit_connector` reescrita: conexión y destino como read-only, gestión de tablas con checkboxes
- ✅ Tablas existentes aparecen marcadas (checked) al editar
- ✅ Re-programación automática del scheduler al cambiar frecuencia

#### Internacionalización
- ✅ `LANGUAGE_CODE` cambiado a `'es'` para mensajes de error en español

### v1.0 (10/03/2026) - Release Inicial
- ✅ Sistema de conectores Google Drive y Amazon S3
- ✅ Sincronización incremental con detección de cambios de esquema
- ✅ Sistema de limpieza automática con políticas de retención
- ✅ Scheduler APScheduler para automatización
- ✅ Cifrado Fernet para contraseñas sensibles
- ✅ Interfaz web responsive en español
- ✅ Páginas de Settings y Help
- ✅ Sistema de autenticación completo
- ✅ Historial de ejecuciones (sync y cleanup)

---

## Notas para Deploy en Producción

1. Cambiar `SECRET_KEY` a un valor seguro (genera uno con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
2. Configurar `ALLOWED_HOSTS` con el dominio de producción
3. Poner `DEBUG = False`
4. Configurar `STATIC_ROOT` y ejecutar `python manage.py collectstatic`
5. Usar gunicorn + nginx (o similar) en lugar de runserver
6. Actualizar la redirect URI de OAuth en Google Cloud Console al dominio de producción
7. Mover credenciales sensibles a variables de entorno
8. Considerar whitenoise para servir archivos estáticos

---

**Fin de la documentación técnica**
