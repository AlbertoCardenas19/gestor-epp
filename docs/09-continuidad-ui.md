# Continuidad de la integración UI

Estado final: integración completada y verificada sobre `work`. El usuario autorizó
posteriormente crear el commit y publicarlo en `main`, conservando el remoto y sin
force push. El hash publicado se confirma en Git al cerrar esa operación. No reiniciar desde
cero ni descartar cambios. Alcance y convenciones: AGENTS.md y
[09-componentes-y-datatables.md](09-componentes-y-datatables.md).

## Conservado y completado

- Dependencias locales verificadas: CoreUI 5.4.3 (CSS + bundle con Popper), jQuery
  3.7.1, DataTables 2.3.5 y adaptador Bootstrap 5 2.3.5. Manifest y licencias locales.
- Adaptador `projects/datatables.py`, endpoints JSON y configuración compartida
  `projects/static/projects/datatables.js`. Consulta completa en PostgreSQL antes
  de paginar; acciones no ordenables ni buscables.
- CoreUI Sidebar/Dropdown y opciones de integración en `components.js`.
- Proyectos conserva tarjetas, `cards.py`, `cards.js` y controles propios de tarjetas.
- Se retiraron los seis archivos sustituidos; no quedan referencias operativas a ellos.
- AGENTS.md y guía técnica actualizados con convenciones actuales del usuario.
- No se modificaron modelos, servicios, migraciones ni reglas de inventario.

## Verificación final

- 125 pruebas Django/PostgreSQL aprobadas.
- 3 pruebas Playwright/Chromium aprobadas sobre una base PostgreSQL temporal:
  vacío/una fila/varias páginas, búsqueda fuera de primera página, orden de fechas
  y cantidades, estados, acciones, corrección/anulación y saldos, tarjetas y móvil.
- Prueba móvil repetida con teclado, preferencia del sidebar, movimiento reducido
  y hit-test de menús sin recorte, a 320/390/1440 píxeles.

## Hallazgo resuelto y cierre

La revisión de capturas detectó encabezados blancos sobre transparente y franjas
con color distinto del acordado. Causa comprobada: el adaptador Bootstrap 5 usa
variables `--bs-table-*`, mientras CoreUI define `--cui-table-*`. Se añadió un puente
limitado a tablas y reglas explícitas de encabezado/franjas en `app.css`. La nueva
pasada de las tres pruebas de navegador pasó, incluyendo las comprobaciones de
contraste y la revisión de capturas correspondientes.

Guía 09 y docs/06-desarrollo.md actualizados. Integridad y referencias comprobadas;
Django check y consistencia de migraciones pasan. No hay pendientes de esta
integración; la limitación actual es Firefox no instalado. El próximo desarrollo
de stock común sigue siendo una tarea separada. No hacer commit ni push sin la
instrucción correspondiente del usuario.

## Comandos en este entorno

```bash
cd /workspace/gestor-epp
export PYTHONDONTWRITEBYTECODE=1
export PGHOST=/workspace/gestor-epp/.local/pgsocket PGPORT=55432 PGUSER=gestor_epp PGDATABASE=gestor_epp
PG_BIN=/workspace/.cloud/postgresql/usr/lib/postgresql/17/bin bash scripts/dev-db.sh start
/workspace/.venvs/gestor-epp/bin/python manage.py test --noinput
PYTHONPATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages BROWSER_EXECUTABLE=/usr/bin/chromium UI_ARTIFACT_DIR=/workspace/.cloud/gestor-epp/datatables-screenshots /workspace/.venvs/gestor-epp/bin/python manage.py test projects.browser_checks --noinput
/workspace/.venvs/gestor-epp/bin/python manage.py check
/workspace/.venvs/gestor-epp/bin/python manage.py makemigrations --check --dry-run
python3 scripts/frontend-vendor.py
git diff --check
```

Los logs/capturas anteriores están en `/workspace/.cloud/gestor-epp/`. No confundir
capturas de otros avances con las de `datatables-screenshots/`. Las pruebas de
navegador crean y retiran su base temporal; no usan los datos de la app.

Logs finales: `dt-backend-final.log` y `dt-browser-final.log` dentro de
`/workspace/.cloud/gestor-epp/`. Última pasada: 125 pruebas backend y 3 pruebas de
navegador aprobadas. El usuario puede retomar desde estos cambios conservados.
