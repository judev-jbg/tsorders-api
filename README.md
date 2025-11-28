# TS Orders API

**Toolstock Orders API** - Backend moderno en FastAPI para gestión de pedidos y envíos.

🔐 **Autenticación JWT con httpOnly cookies** - Reemplazo seguro del sistema de API Key

✅ **20 endpoints ** FastAPI

## Requisitos

- Python 3.11 o superior
- MySQL
- Variables de entorno configuradas en `.env`

## Instalación

### 1. Crear entorno virtual

```bash
cd \tsorders-api
python -m venv venv
```

### 2. Activar entorno virtual

```bash
# Windows CMD
venv\Scripts\activate

# Windows PowerShell
venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

`.env` configurar con tus credenciales:

Editar `.env` con tus valores reales.

## Uso Diario

### Comando manual

```bash
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en: **http://127.0.0.1:8000**

## Documentación API

Una vez iniciado el servidor, acceder a:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Estructura del Proyecto

```
tsorders-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # Aplicación principal FastAPI
│   ├── database.py      # Configuración de base de datos
│   ├── models.py        # Modelos SQLAlchemy
│   ├── schemas.py       # Esquemas Pydantic (validación)
│   ├── routes.py        # Endpoints de la API
│   └── services.py      # Lógica de negocio y servicios
├── venv/                # Entorno virtual (no subir a git)
├── .env                 # Variables de entorno (no subir a git)
├── .env.example         # Ejemplo de variables
├── requirements.txt     # Dependencias Python
├── start.bat            # Script para iniciar en Windows
└── README.md
```

## Endpoints Disponibles (20 total)

### 🔐 Autenticación JWT (5 endpoints)

- `POST /auth/login` - Iniciar sesión (establece cookies httpOnly)
- `POST /auth/logout` - Cerrar sesión
- `POST /auth/refresh` - Renovar access token
- `GET /auth/me` - Información del usuario
- `GET /auth/check` - Verificar estado de autenticación

### 📦 Pedidos (4 endpoints)

- `GET /order/{id}` - Obtener pedido por ID
- `GET /orderspending` - Pedidos pendientes
- `GET /orderspending/untiltoday` - Pendientes hasta hoy
- `GET /orderspending/delayed` - Pendientes retrasados
- `PATCH /orderspending` - Actualizar flag de stock

### 📋 Fuera de Stock (4 endpoints)

- `GET /ordersoutofstock` - Pedidos sin stock
- `GET /ordersoutofstock/untiltoday` - Sin stock hasta hoy
- `GET /ordersoutofstock/delayed` - Sin stock retrasados
- `PATCH /ordersoutofstock` - Actualizar flag fake

### 🚚 Envíos (7 endpoints)

- `GET /ordersshipfake` - Pedidos con envío fake
- `GET /ordersreadytoship` - Pedidos listos para envío
- `POST /ordersreadytoship` - Añadir pedido a envío ✨ NUEVO
- `PATCH /ordersreadytoship` - Actualizar datos de envío ✨ NUEVO
- `DELETE /ordersreadytoship` - Eliminar pedido de envío ✨ NUEVO
- `PATCH /registershipment` - Registrar envío File ✨ NUEVO
- `PATCH /registershipment` - Registrar envío GLS WS ✨ NUEVO

### 📊 Historial (2 endpoints)

- `GET /ordershistory` - Historial de envíos
- `GET /ordershistory/{filename}` - Envíos por archivo

## Troubleshooting

### Error: "Address already in use"

- El puerto 8000 está ocupado
- Cambia el puerto en `start.bat`: `--port 8001`

## Desarrollo

### Agregar nuevos endpoints

1. Definir schema en `app/schemas.py`
2. Agregar ruta en `app/routes.py`
3. Implementar lógica en `app/services.py`

## Licencia

Uso interno - Toolstock
