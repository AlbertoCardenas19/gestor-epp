# Gestor EPP

Aplicación web en español con Django, PostgreSQL y CoreUI basado en Bootstrap.

Actualmente puedes:

- Crear, listar y consultar proyectos.
- Crear y consultar un catálogo común de EPP y señaléticas.
- Registrar existencias iniciales y entradas por proyecto.
- Consultar saldos e historial y corregir registros conservando sus originales.
- Registrar entregas directas a trabajadores por nombre completo, descontando
  unidades del inventario del proyecto sin permitir superar el saldo disponible.

Las entregas directas se descuentan; intermediarios, devoluciones y reposiciones
siguen pendientes. Se pueden corregir aperturas, entradas y entregas mediante
reemplazos vinculados. En entregas se pueden rectificar los seis campos, incluido
proyecto o elemento, conservando el original y validando ambos saldos.
También se puede anular una entrega vigente registrada por error, con motivo e
historial conservados y restitución de existencias una sola vez. Esto no registra
una devolución física. Esta versión está
preparada para pruebas locales; cuentas, permisos y despliegue público siguen pendientes.

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

1. En Proyectos, crea un proyecto, por ejemplo «Obra Norte». Las tablas de Catálogo y Entregas tienen
   un botón «Acciones» por fila que abre un menú para consultar sus registros.
   Proyectos se muestra con tarjetas y enlaces «Ver proyecto».
2. En «Catálogo», crea «Casco de seguridad» de tipo EPP.
3. Desde Inicio, entra en Proyectos. Abre el proyecto y selecciona la pestaña «Inventario».
4. Registra una apertura de 10 cascos y después una entrada de 5: saldo 15.
5. Corrige la apertura a 8, indicando un motivo: saldo 13. El original queda anulado.
6. Crea otro proyecto y comprueba que el mismo casco comienza «Sin registro inicial».
7. En el historial del casco de Obra Norte, registra una entrega de 3 unidades
   a un trabajador, indicando su nombre completo y la fecha: saldo 10.
8. Intenta entregar 11 unidades: debe rechazarse y conservarse el saldo 10.
9. Vuelve al proyecto: «Entregas» muestra una fila por entrega vigente. Prueba
   buscar por trabajador, ordenar pulsando los encabezados y cambiar de página. El filtro de estado permite
   consultar también las entregas sustituidas y anuladas.
10. En Catálogo, prueba la tabla con búsqueda automática al escribir, ordenación
    y paginación. También se aplica a Proyectos y Entregas. Ya no hay selector
    «Ordenar por»: cada encabezado de datos alterna la dirección al pulsarlo. La flecha
    bajo las opciones del menú lateral permite reducirlo a una columna de iconos.

Los datos que registres se guardan en tu PostgreSQL local. No se incluyen bases
de datos ni registros de prueba de la nube en GitHub.

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

## Documentación

- [Requisitos, acuerdos y pendientes](docs/README.md).
- [Desarrollo en el entorno de nube y detalles de implementación](docs/06-desarrollo.md).
- [Prueba manual de corrección y anulación de entregas](docs/07-iteraciones-entregas.md#recorrido-manual-para-ambas-iteraciones).


El stock común de empresa y las solicitudes por proyecto con reserva están
acordándose para un próximo cambio; todavía no sustituyen el inventario por
proyecto de esta versión. Consulta [las decisiones y pendientes](docs/05-fuentes.md#s16--revisión-del-flujo-stock-común-y-solicitudes-por-proyecto).
