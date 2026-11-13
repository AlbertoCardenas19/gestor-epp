# Gestor EPP

Aplicación web en español con Django, PostgreSQL y CoreUI basado en Bootstrap.

Actualmente puedes crear/consultar proyectos en tarjetas y elementos en un único
Inventario; registrar entradas, solicitar elementos por proyecto, reservar lo
disponible y guardar lo faltante como necesidad de compra. Las reservas y entregas
reales se reúnen en «Entregados», manteniendo su distinción y trazabilidad interna.

Se confirman entregas parciales a trabajadores por nombre completo, con fecha y
observación opcional. Se pueden corregir/anular con motivo e historial y reducir
pendientes, priorizando lo que falta comprar. No hay compras, aprobación,
intermediarios, devoluciones físicas ni finanzas implementadas. Cuentas, permisos
y despliegue público siguen pendientes. [Reglas actuales y pruebas](docs/11-inventario-y-solicitudes.md).

## Probar en tu PC

Necesitas **Git, Python 3.12 y PostgreSQL 17** instalado y en ejecución.
Los estilos y gráficos están incluidos en el repositorio: no necesitas Node ni npm.

### 1. Obtener el código

```bash
git clone https://github.com/AlbertoCardenas19/gestor-epp.git
cd gestor-epp
```

Si ya tienes una copia con trabajo propio, consérvala y clona en otra carpeta
para esta primera prueba. El antiguo `.venv` versionado fue retirado de Git;
crea un entorno nuevo para esta versión.

### 2. Crear un entorno e instalar dependencias

**Windows — PowerShell**, sin necesidad de activar scripts:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux o macOS:**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Copia el ejemplo solo la primera vez; conserva tu `.env` al actualizar el código.

### 3. Preparar PostgreSQL

Desde pgAdmin, con una cuenta administradora, crea una cuenta local para la app.
Sustituye la clave de ejemplo por una elegida por ti:

```sql
CREATE ROLE gestor_epp WITH LOGIN CREATEDB PASSWORD 'elige_una_clave_local';
```

Después ejecuta **por separado**, con autocommit habilitado:

```sql
CREATE DATABASE gestor_epp OWNER gestor_epp;
```

`CREATEDB` permite ejecutar las pruebas, que crean una base temporal separada.
Si ya tienes un usuario y una base local, puedes usarlos sin recrearlos.

Abre `.env` en tu editor y configura `PGPASSWORD` con la clave de esa cuenta.
Comprueba también `PGHOST`, `PGPORT`, `PGUSER` y `PGDATABASE`; los ejemplos usan
PostgreSQL local en `127.0.0.1:5432` y el nombre `gestor_epp`.
`.env` se carga automáticamente y está excluido de Git. No compartas su contenido.
Si tienes variables `PG*` configuradas en la terminal, prevalecen sobre `.env`.

### 4. Crear las tablas e iniciar la aplicación

**Windows — PowerShell:**

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

**Linux o macOS:**

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

En tu PC, abre el navegador en `http://127.0.0.1:8000/`. Para detener el servidor,
presiona `Ctrl+C`. Las próximas veces solo necesitas iniciar PostgreSQL y ejecutar
`manage.py runserver` con el Python de tu entorno.

### 5. Recorrido de prueba

1. En Inventario, crea un casco de tipo EPP con cantidad inicial 2 (vacía = 0).
2. En Proyectos, crea/abre una tarjeta y entra en su pestaña Inventario.
3. Solicita 5 cascos: se reservan 2 y quedan 3 como necesidad de compra.
   Inventario general muestra Existencias 0 / Entregados 2.
4. Confirma entrega de 1 a un trabajador. Las columnas siguen 0/2; el historial
   del proyecto muestra la entrega real. No puedes entregar más de lo reservado.
5. Registra una entrada en Inventario; después usa «Reservar disponibles» en
   la solicitud. No hay asignación automática entre proyectos.
6. Prueba reducción/cancelación pendiente con motivo y corrección/anulación de
   entregas. El [recorrido detallado](docs/11-inventario-y-solicitudes.md#probar-en-ubuntu)
   explica las cantidades esperadas y las diferencias entre estas operaciones.
7. Prueba búsqueda con ×, ordenación, páginas y menús Acciones. Proyectos conserva
   tarjetas. Entregas conserva su filtro de estado.

Los datos se guardan en tu PostgreSQL local. GitHub no incluye la base de la nube.

## Comprobaciones

Con PostgreSQL en ejecución y `.env` configurado:

```bash
# Usa .\.venv\Scripts\python.exe en Windows.
.venv/bin/python manage.py check
.venv/bin/python manage.py test projects catalog inventory
```

Si aparece «connection refused», revisa que PostgreSQL esté iniciado y que el
puerto coincida. Si aparece «password authentication failed», verifica que
`PGUSER` y `PGPASSWORD` correspondan a la cuenta creada, no a otra cuenta de pgAdmin.

Para actualizar una copia limpia más adelante: `git pull`, instalar nuevamente
`requirements.txt` y ejecutar `manage.py migrate` antes de iniciar el servidor.

Las tablas usan los controles de DataTables en español y procesamiento en PostgreSQL.
Proyectos conserva sus tarjetas. CoreUI gestiona el menú lateral y los desplegables;
no se necesita npm ni conexión a un CDN para ejecutar la app.

## Documentación

- [DataTables, componentes CoreUI y pruebas](docs/09-componentes-y-datatables.md).
- [Inventario único, solicitudes y migración 0004](docs/11-inventario-y-solicitudes.md).
- [Primer incremento común y migración 0003](docs/10-inventario-comun.md).
- [Requisitos, acuerdos y pendientes](docs/README.md).
- [Desarrollo en el entorno de nube y detalles de implementación](docs/06-desarrollo.md).
- [Prueba manual de corrección y anulación de entregas](docs/07-iteraciones-entregas.md#recorrido-manual-para-ambas-iteraciones).


Las migraciones 0003/0004 conservan los datos anteriores; ejecuta `migrate` antes
de usar el flujo nuevo. No se fabrican solicitudes para entregas históricas.

Para tu copia Ubuntu existente (cuando estos cambios estén publicados):

```bash
cd ~/Proyectos/gestor-epp
git status
git pull --ff-only origin main
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver
```

Conserva tu `.env` y cualquier trabajo local antes de actualizar.
