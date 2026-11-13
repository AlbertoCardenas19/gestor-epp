# Convenciones actuales: DataTables y componentes CoreUI

Decisión actual del usuario, registrada el 12 de noviembre de 2026 (S20).
Aplica a RF-03, RF-05, RF-08 y RF-09. No es una reinterpretación de acuerdos
históricos. Las instrucciones permanentes están en [AGENTS.md](../AGENTS.md).

## Decisiones y estado implementado

- DataTables gestiona búsqueda, ordenación, filas por página y paginación de las
  tablas que lo necesiten. Configuración y textos en español compartidos.
- Catálogo y Entregas usan DataTables con `serverSide: true`. La consulta SQL ya
  estaba paginada y no hay un límite de crecimiento acordado: se mantiene la
  paginación en PostgreSQL y solo se envía la página solicitada. Nunca se ordena
  ni filtra únicamente el fragmento de HTML inicial de Django.
- Proyectos conserva sus tarjetas, búsqueda y páginas. Su mejora específica usa
  `cards.py`/`cards.js`; no es una tabla y no recibe una inicialización DataTables.
- CoreUI gestiona Sidebar y Dropdown: toggle, Escape, flechas de teclado, cierre,
  atributos de estado y posicionamiento mediante Popper. No se reconstruyen esas
  interacciones en código propio. Modales o colapsables futuros deben usar también
  CoreUI cuando cubra la necesidad; no se añaden componentes sin uso ahora.
- Antes de introducir una alternativa técnica se debe justificar la excepción.
  Mantener diseños elegidos y no convertir indiscriminadamente listados en tablas.

No cambia el modelo de datos ni ninguna regla de inventario, entrega, corrección
o anulación. Stock común y solicitudes (S16/S19) siguen fuera de esta entrega.

## Dependencias y carga única

| Paquete | Versión | Uso |
|---|---|---|
| `@coreui/coreui` | 5.4.3 | CSS existente y `coreui.bundle.min.js`, que incluye Popper |
| `jquery` | 3.7.1 | Dependencia de DataTables y su transporte Ajax; versión completa |
| `datatables.net` | 2.3.5 | Biblioteca DataTables |
| `datatables.net-bs5` | 2.3.5 | Adaptador JS y estilos de DataTables para Bootstrap 5 |

CoreUI ya proporciona la base Bootstrap 5. **No cargar Bootstrap CSS ni Bootstrap
JS además de CoreUI.** Los estilos `dataTables.bootstrap5.min.css` son la adaptación
de DataTables, no otra copia de Bootstrap. No usar otra versión de DataTables para
el adaptador. jQuery completo es necesario para Ajax; no usar la versión slim.

Los archivos, licencias, URLs, SHA-512 del archivo npm y SHA-256 de cada recurso
están versionados en `projects/static/vendor/manifest.json`. Se verificaron los
archivos npm oficiales al incorporarlos. El navegador no depende de CDN ni de npm.

`base.html` carga una vez CoreUI CSS, CoreUI bundle y `components.js`.
Las páginas con tablas incluyen una vez `datatables_styles.html` y
`datatables_scripts.html`: jQuery → DataTables → adaptador Bootstrap 5 →
`datatables.js`. `app.css` se carga después de los CSS de bibliotecas para adaptar
paleta y espaciado. Proyectos carga solo `cards.js`, sin DataTables ni jQuery.

Comprobar archivos locales, sin red ni instalaciones:

```bash
python scripts/frontend-vendor.py
```

Restaurar exactamente las versiones fijadas desde npm, únicamente si es necesario:

```bash
python scripts/frontend-vendor.py --restore
```

Para actualizar versiones se deben revisar compatibilidad, licencias, manifest e
integridad y volver a ejecutar las comprobaciones; no editar un archivo minificado.

## Reutilizar una tabla

1. Incluir los estilos y scripts compartidos desde los bloques `extra_styles` y
   `extra_scripts`, como hacen Catálogo y Entregas. No copiar una inicialización.
2. Encerrar filtros, mensaje de error y tabla en un contenedor
   `data-datatable-panel` para que cada instancia tenga su propio contexto.
3. Marcar la tabla con `data-datatable`, `data-source` y el orden inicial JSON:

```html
<table data-datatable data-source="/ruta/datos/" data-order='[[0,"asc"]]'>
  <thead><tr>
    <th data-column="name">Nombre</th>
    <th data-column="actions" data-actions>Acciones</th>
  </tr></thead>
  <tbody></tbody>
</table>
```

4. Cada `data-column` corresponde a una clave del JSON. Marcar fechas ISO con
   `data-format="date"` para presentación DD/MM/YYYY sin conversiones de zona horaria.
   `data-actions` desactiva búsqueda y ordenación en el cliente; también debe
   tener columna `None` y no figurar en `search_fields` del servidor.
5. El texto del usuario usa `DataTable.render.text()` para evitar interpretar HTML.
   Solo `actions` recibe HTML de una plantilla Django con escape automático.
6. `window.EppTables.init(contenedor)` permite inicializar tablas nuevas, por ejemplo
   tras insertar contenido. Comprueba `DataTable.isDataTable` antes de inicializar;
   invocarlo dos veces no duplica controles ni consultas.

No añadir otro buscador, paginador Django visible ni enlaces propios de ordenación
alrededor de una tabla DataTables. El HTML inicial sirve para consulta básica sin
JavaScript, con páginas Django dentro de `noscript`; DataTables lo sustituye por
la consulta Ajax completa cuando está disponible JavaScript.

## Adaptador del servidor

`projects/datatables.py::DataTableView` es un adaptador de lectura del protocolo
DataTables. Cada subclase declara:

- `get_queryset()`: alcance de negocio, antes de contar, buscar o paginar.
- `order_columns`: lista permitida de campos ORM; `None` para Acciones.
- `search_fields`: únicamente campos buscables, nunca HTML de acciones.
- `default_order`: orden estable; se añade PK como desempate al ordenar por columnas.
- `serialize_record()`: diccionario de datos por fila.
- `normalize_search()`, si es necesario para formatos de presentación como fechas.

La respuesta incluye `draw`, `recordsTotal`, `recordsFiltered` y `data`. No se
aceptan nombres de campos ORM enviados por el navegador. `draw`, inicio y tamaño
se validan; se permiten 10, 25 o 50 filas por página. Las búsquedas son literales,
sin ejecutar expresiones regulares del cliente. Se permiten órdenes de varias
columnas, siempre dentro de la lista permitida. Todo es GET, sin escrituras.

Endpoints actuales:

- `/catalogo/datos/` — `catalog:data`.
- `/proyectos/<pk>/entregas/datos/` — `projects:delivery-data`.

Entregas restringe primero al proyecto y al estado elegido. `recordsTotal` refleja
ese alcance de negocio; `recordsFiltered`, el mismo alcance más la búsqueda.
Mantiene Vigentes, Todos, Anuladas y Sustituidas. El filtro conserva el buscador,
el orden y el tamaño de página; al cambiar vuelve a la primera página. Fecha y
cantidad se ordenan en PostgreSQL con sus tipos reales. Las cantidades viajan
como cadenas exactas para no perder precisión con enteros superiores a 2^53.

## CoreUI y ajustes específicos

`components.js` inicializa los componentes oficiales de forma idempotente.
DataTables llama a `dispose()` antes de redibujar y a `init()` después: las acciones
siguen operativas tras buscar, ordenar y cambiar de página, sin instancias antiguas.
El menú utiliza `data-coreui-toggle="dropdown"`; sus enlaces abren las mismas vistas
y confirmaciones. Elegir Corregir o Anular no ejecuta directamente la escritura.

Los dropdowns reciben `popperConfig.strategy = 'fixed'` y límite de viewport/body,
para superar el recorte del contenedor desplazable de la tabla. CoreUI/Popper
conservan el posicionamiento y teclado; no hay un menú propio paralelo.

El sidebar usa `coreui.Sidebar` y `data-coreui-toggle="narrow"`. La app únicamente
sincroniza su nombre accesible y guarda la preferencia en `localStorage`. El CSS
mantiene el rail de iconos en móvil: anula el modo off-canvas automático mediante
`--cui-is-mobile: initial` y adapta la clase oficial `sidebar-narrow` a 76 píxeles.
Se conserva expansión, transición suave, altura fija del botón, paleta y respeto
por `prefers-reduced-motion`. No se oculta completamente el menú móvil elegido.

## Sustituciones y código conservado

| Anterior | Actual |
|---|---|
| `projects/tables.py` | `datatables.py` para tablas; `cards.py` para tarjetas |
| `table.js` | `datatables.js`; la mejora de tarjetas se conserva como `cards.js` |
| `table_controls.html` | Controles oficiales DataTables; `cards_controls.html` solo para tarjetas |
| `table_headers.html` | Encabezados estáticos declarativos y ordenación oficial DataTables |
| `sidebar.js` | Sidebar CoreUI, más persistencia de aplicación en `components.js` |
| `actions.js` y Popover | Dropdown CoreUI y sus opciones de Popper en `components.js` |

Se conservan formularios, enlaces de historial, correcciones, anulaciones, modelos,
servicios, migraciones anteriores, paleta y tarjetas. No hay migraciones nuevas.

## Verificar y probar en PC

Para ejecutar la app, usar el entorno y `.env` ya configurados. No se requieren
nuevas dependencias Python de aplicación ni Node/npm. Reiniciar el servidor y
recargar el navegador con Ctrl+Shift+R para renovar CSS/JS locales.

1. Catálogo: probar vacío, un elemento y más de 10. Buscar un nombre fuera de la
   primera página; ordenar cada columna, cambiar filas y página. Abrir Acciones.
2. Proyecto: comprobar las tarjetas y su búsqueda/páginas; abrir Entregas.
3. Entregas: ordenar fechas y cantidades, buscar un trabajador y cambiar estado.
   Comprobar que anuladas/sustituidas solo ofrecen historial y que vigentes ofrecen
   las confirmaciones de corregir/anular.
4. En escritorio y móvil, comprobar desplazamiento horizontal dentro de la tabla,
   menús sin recorte, teclado, sidebar, transición y preferencia al recargar.
5. Con datos de prueba, recorrer corrección y anulación y comprobar los saldos.

Pruebas de backend, con PostgreSQL y `.env` configurados:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python scripts/frontend-vendor.py
```

Suite opcional de navegador, separada de las dependencias de producción:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python manage.py test projects.browser_checks
```

En Windows usar `.\.venv\Scripts\python.exe`; en Linux/macOS, `.venv/bin/python`.
`BROWSER_EXECUTABLE` permite usar un Chromium ya instalado. `UI_ARTIFACT_DIR` guarda
capturas fuera del repositorio si se define. La suite levanta un servidor de prueba
y usa una base PostgreSQL temporal, sin modificar registros de la aplicación.


## Resultado verificado de esta integración

- 125 pruebas Django aprobadas sobre PostgreSQL, incluyendo inventario, reenvíos,
  concurrencia, correcciones y anulaciones anteriores, y el adaptador DataTables.
- 3 pruebas de navegador aprobadas en Chromium, con servidor y base PostgreSQL
  temporales: vacío, una fila, 41 registros, búsqueda fuera de la primera página,
  ordenación de fechas/cantidades, filtros, páginas y filas, acciones tras redibujar,
  repetición de inicializaciones sin duplicados y escape de texto del usuario.
- La suite realiza una corrección y una anulación desde las acciones DataTables;
  comprueba sus saldos y conserva el historial esperado. No escribe en la base de
  la aplicación.
- Escritorio y móvil emulado a 320, 390 y 1440 píxeles: menú sin recorte comprobado
  con hit-test, teclado y Escape, navegación de tarjetas, preferencia al recargar,
  transición y movimiento reducido, sin desborde de página ni errores de consola.
- La revisión visual detectó y corrigió un conflicto entre `--bs-table-*` y
  `--cui-table-*`. Hay un puente de variables limitado a las tablas en `app.css` y
  comprobaciones automáticas del encabezado grafito, texto blanco y franjas.
- Integridad de los cuatro paquetes verificada con el manifest. `check`,
  `makemigrations --check --dry-run`, `migrate --check` y `git diff --check` pasan.
  No hay referencias operativas a los seis archivos retirados.

Limitaciones comprobadas: Firefox se intentó iniciar, pero falta su ejecutable
`/home/agent/.cache/ms-playwright/firefox-1538/firefox/firefox`. La revisión móvil
usa emulación de viewport en Chromium; no se ejecutó en un dispositivo físico.
Las instrucciones Windows/macOS no se han ejecutado en esos sistemas.

## Uso en Inventario y solicitudes — S22

La tabla única de Inventario y las solicitudes por proyecto reutilizan el mismo
adaptador y `data-datatable`, con endpoints propios para SQL y `data-actions` en
Acciones. El historial común incluye el proyecto de la solicitud para entregas
nuevas y el proyecto de origen para las históricas. Proyectos sigue en tarjetas.

La configuración compartida agrega una × accesible al control de búsqueda nativo,
para limpiar/enfocar sin duplicar su inicialización. Las tarjetas incluyen el
mismo complemento en `cards_controls.html` y `cards.js`; no usan DataTables.
No cambian versiones ni dependencias. Flujo y comprobaciones actuales en
[11-inventario-y-solicitudes.md](11-inventario-y-solicitudes.md).
