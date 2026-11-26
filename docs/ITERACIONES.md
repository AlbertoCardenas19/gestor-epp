# Iteraciones de gestor-epp

## Estado actual

Iteraciones UI-01 y UI-02 publicadas. UI-03 implementada y verificada localmente: el control del sidebar se muestra desde el HTML y los scripts compartidos usan URL ligada a su contenido.

## Pendientes

- Decisiones funcionales abiertas de [docs/04-pendientes.md](04-pendientes.md), en particular el cálculo automático de IVA (P-07), aprobación de compras, devoluciones y reposiciones.
- Confirmar en la PC del usuario el recorrido visual y funcional con sus datos locales tras actualizar desde `origin/main`.

## Próximo paso

Actualizar la copia Ubuntu desde `origin/main` y comprobar las nuevas URL de `components.js` y `datatables.js`, el botón en ambos estados y el ancho de las tablas tras redimensionar.

## UI-03 · 26 de noviembre de 2026

**Objetivo.** Mantener visible el botón circular en ambos estados del sidebar y evitar tablas estrechas después de reducir y ampliar la ventana, cambiar el sidebar o abrir pestañas.

**Causa y cambios implementados.** El botón existía en el DOM, pero el HTML lo entregaba con `hidden` y dependía de que `components.js` quitase ese atributo. Al inspeccionarlo con el script actual, medía 44 × 44 px como área de clic, estaba centrado en el borde derecho y en la altura de la ventana, recibía el clic en su centro y quedaba fuera del `overflow` del sidebar, por encima de este. Se quitó `hidden` inicial para que el círculo de 30 px sea visible desde el primer render. La URL de `components.js` ahora incluye el hash de su contenido, igual que la hoja de estilos.

**Diagnóstico de la tabla.** Los contenedores y elementos generados por DataTables se midieron en Chromium antes y después de redimensionar y al abrir pestañas ocultas. Con el script actual, la tabla recuperó el ancho disponible. Al servir el `datatables.js` anterior junto al HTML y CSS actuales se reprodujo exactamente el fallo: después de pasar de 600 a 1440 px, el contenedor medía 1306 px y la cabecera y tabla seguían en 506 px por el ancho en línea `width: 506px !important` que fijaba el script anterior. La URL de ese script no cambiaba entre versiones. Se versionó por hash de contenido en la plantilla compartida; el ajuste actual mediante la API de DataTables se conserva. Esto explica el fallo de una copia con script en caché, aunque no se ha inspeccionado el caché de la PC del usuario.

**Verificación visual.** En Chromium se redujo y amplió la ventana, se cerró y abrió el sidebar y se cambiaron pestañas de detalle. La tabla volvió a ocupar el contenedor (1306 px tras ampliar); no hubo errores de consola ni solicitudes de datos adicionales por la secuencia. El botón quedó visible y pulsable expandido y contraído. Capturas: [botón expandido](capturas/ui03-boton-expandido.png), [botón contraído](capturas/ui03-boton-contraido.png) y [tabla tras redimensionar](capturas/ui03-tabla-tras-redimensionar.png).

**Comprobaciones.** Pasaron `manage.py check`, 187 pruebas Django, 13 pruebas Chromium, `makemigrations --check --dry-run`, `node --check` de los dos scripts y `git diff --check`. La prueba de navegador cubre anchos de 390, 700 y 1440 px, el botón en ambos estados, la tabla tras redimensionar y las pestañas de detalle.

**Entrega.** Verificada y autorizada para publicación en `origin/main`; el hash se informa en la respuesta final.

## UI-02 · 26 de noviembre de 2026

**Objetivo.** Hacer visible de forma fiable la dirección estética aprobada del sidebar en el navegador del usuario (RF-03), conservando la navegación de UI-01.

**Causa y cambios implementados.** El HTML de navegación se actualizaba, pero la URL `/static/projects/app.css` no variaba entre commits. Al servir a Chromium esa hoja anterior junto con el HTML nuevo se reprodujeron el fondo gris azulado `rgb(51, 65, 85)`, el encabezado de 12 px, los iconos y la franja de 76 px. CoreUI se carga primero; la hoja del proyecto tiene la última regla efectiva para el sidebar y no impide los estilos nuevos. `versioned_static` añade a la URL un hash del contenido CSS, de modo que cada versión solicita una URL distinta. Se reforzó discretamente el contraste de los separadores, el círculo conserva el azul del sidebar también al pasar el cursor, y se consolidaron las reglas del sidebar para evitar declaraciones repetidas de altura, padding y transición.

**Diagnóstico de cascada.** La página carga `coreui.min.css` y luego `app.css?v=<hash>`. CoreUI define `.sidebar` con ancho de 16 rem, fondo `--cui-sidebar-bg` y transición propia; `.app-sidebar` aparece después y define ancho, fondo `--app-sidebar` (`#142c4b`) y transición de 0,24 s. `.sidebar.app-sidebar.sidebar-narrow` fija la franja en 28 px. Los enlaces usan `.app-sidebar .nav-link`, sin `::before` visible, y no reciben iconos de CoreUI. El botón está fuera del `<aside>`, con posición fija y `z-index: 11` frente al `10` del sidebar; su centro recibe los clics en ambos estados. El `overflow: hidden` del estado contraído afecta solo al contenido del sidebar y no recorta ese botón.

**Verificaciones realizadas y resultados.** Chromium confirmó el orden de las hojas, la URL versionada, los estilos calculados, el elemento que recibe el clic y la ausencia de recorte del botón en escritorio y móvil. La simulación con el CSS anterior reprodujo los estilos incorrectos. Pasaron `manage.py check`, 187 pruebas Django, 12 pruebas Chromium, `makemigrations --check --dry-run`, `compileall` y `git diff --check`. Capturas: [escritorio expandido](capturas/sidebar-escritorio-expandido.png), [escritorio contraído](capturas/sidebar-escritorio-contraido.png), [móvil expandido](capturas/sidebar-movil-expandido.png) y [móvil contraído](capturas/sidebar-movil-contraido.png).

**Limitaciones y pendientes.** La causa en la PC se infiere de la reproducción con la hoja anterior; no se ha inspeccionado el caché de ese equipo. Las decisiones funcionales abiertas, incluido el IVA automático, no cambian.

**Entrega.** Verificada y autorizada para publicación en `origin/main`; el hash se informa en la respuesta final.

## UI-01 · 26 de noviembre de 2026

**Objetivo.** Unificar la navegación y presentación de inventario y listados sin alterar las reglas de stock, solicitudes, entregas o compras (RF-03, RF-04 y RF-05).

**Cambios implementados.** Sidebar agrupado sin iconos en los enlaces, franja contraída y control circular; acceso «Inventario» único en el menú; creación junto a filtros y búsqueda; enlaces generales redundantes retirados; tablas blancas con hover gris; filas de inventario navegables con enlace real; acciones de inventario accesibles desde la ficha; indicador «Pendiente» junto a entregados; ajuste de ancho mediante la API compartida de DataTables.

**Verificaciones realizadas y resultados.** `manage.py check`, `compileall`, `node --check` y `makemigrations --check --dry-run` pasaron; no se detectaron cambios de modelos. Pasaron 186 pruebas Django y 12 pruebas Chromium sobre bases temporales PostgreSQL 17. Chromium comprobó anchos 320, 390 y 1440 px, sidebar, controles, tablas, navegación por fila, indicador pendiente, cambios de tamaño y errores de consola.

**Limitaciones y pendientes.** Las decisiones funcionales de `docs/04-pendientes.md`, incluido el IVA automático, siguen abiertas. No se añadieron migraciones ni dependencias de producción.

**Entrega.** Publicada en `origin/main` mediante `b47fef873ed574d5d19533546b8dc0e3f660db51`.
