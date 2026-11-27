# Iteraciones de gestor-epp

## Estado actual

UI-01 a UI-06 publicadas. UI-06 verificada en Chromium; falta comprobarla en Firefox en la PC del usuario.

## Pendientes

- Decisiones funcionales abiertas de [docs/04-pendientes.md](04-pendientes.md), en particular el cálculo automático de IVA (P-07), aprobación de compras, devoluciones y reposiciones.
- Confirmar en la PC del usuario el recorrido visual y funcional con sus datos locales tras actualizar desde `origin/main`.

## Próximo paso

Actualizar la copia Ubuntu desde `origin/main` y comprobar el recorrido visual de UI-06 en Firefox con los datos locales. El plan restante de `diseno-gestor-epp.md` requiere iteraciones posteriores.

## UI-06 · 27 de noviembre de 2026

**Objetivo y alcance.** Incorporar [diseno-gestor-epp.md](diseno-gestor-epp.md) como guía permanente y aplicar únicamente las decisiones nuevas sobre tablas e Inicio (RF-03, RF-04 y RF-05). La solicitud prevalece sobre el diseño anterior del buscador y del encabezado. No se cambiaron modelos ni cálculos de stock, entregas, compras o IVA.

**Cambios.** El buscador oficial de DataTables queda dentro de la tarjeta, junto a «Mostrar X filas», con etiqueta visible «Buscar» y placeholder según los campos reales de cada endpoint. Se retiró su traslado externo y se conserva la búsqueda automática única. El bloque de la tabla tiene 1rem de separación arriba y abajo en escritorio y .75rem en móvil; se retira la clase `mt-2` que añade el adaptador BS5 para evitar un margen superior en conflicto. El encabezado compartido usa `--app-table-heading: #EAF4FB` y texto oscuro, incluidos estados de ordenación; las filas blancas y el hover gris permanecen. Inicio usa un componente de tarjeta con área de acciones separada por borde y alineada abajo, y añade Facturas enlazada al listado existente.

**Filtros retirados de la interfaz.** Categoría de Inventario, Proyecto del historial de movimientos y Estado de Entregas. El código compartido deja de enviar esos valores desde controles ocultos. El listado de Entregas presenta Vigentes, Anuladas y Sustituidas con su estado visible; conserva el alcance del proyecto. El historial conserva el alcance del elemento. Los endpoints siguen aceptando filtros explícitos para compatibilidad de consultas directas, pero la página no los aplica ni retiene parámetros antiguos. Proyectos y los selectores de elementos mantienen sus búsquedas. No quedó un caso que requiera decisión funcional para retirar estos tres controles temporalmente.

**Documentación.** AGENTS.md enlaza la guía y declara las nuevas reglas permanentes. [09-componentes-y-datatables.md](09-componentes-y-datatables.md) distingue los resultados históricos de las convenciones vigentes. El resto del plan visual adjunto no se implementó en esta iteración.

**Verificación.** Pasaron 185 pruebas Django y 15 pruebas Chromium: tabla vacía, una fila, más de una página, búsqueda y ordenación en servidor, tamaño de página, pestañas, sidebar y navegación; se comprobaron ausencia de controles duplicados, el enlace Facturas y la alineación de áreas de acciones con descripciones de longitud distinta. En Chromium se midió Inventario a 1440 → 390 → 320 → 1440 px sin recarga: tabla y contenedor midieron 1290, 296, 226 y 1290 px, respectivamente; los huecos alrededor de la tabla midieron 16 px en escritorio y 12 px en móvil. El encabezado calculado fue `rgb(234, 244, 251)`. No hubo desbordamiento horizontal ni errores de consola en ese recorrido. Capturas: [Inicio](capturas/ui06-inicio.png), [tabla escritorio](capturas/ui06-tabla-escritorio.png), [tabla 390 px](capturas/ui06-tabla-390.png), [tabla 320 px](capturas/ui06-tabla-320.png) y [tabla tras volver a escritorio](capturas/ui06-tabla-1440.png). Firefox no está disponible en este entorno.

## UI-05 · 26 de noviembre de 2026

**Objetivo y alcance.** Alinear los elementos del sidebar y acercar su presentación a la imagen de Punto Aparte (RF-03), sin cambiar destinos, interacciones ni reglas de negocio.

**Cambios.** Los enlaces Inicio y Proyectos quedan bajo General; se mantienen Elementos y Compras con sus enlaces previos. Se retira la marca superior del sidebar para que el primer título comience junto al borde superior, como en la referencia. Títulos y texto de enlaces comparten la coordenada horizontal de 28 px. Los separadores quedan entre grupos, de 28 a 221 px. El ancho expandido es 255 px; el estado activo usa azul más claro, texto blanco y una barra clara a la izquierda. La franja contraída de 28 px y el botón circular centrado en su borde se conservan.

**Verificación.** En Chromium a 1440 × 850 px, títulos y enlaces midieron x = 28 px; el sidebar midió 255 px expandido y 28 px contraído. El control midió 44 × 44 px como área de clic con círculo visible de 30 px, centrado en x = 255 o 28 px y a media altura. Se inspeccionaron las capturas [expandido](capturas/ui05-sidebar-expandido.png) y [contraído](capturas/ui05-sidebar-contraido.png). Pasaron 185 pruebas Django, 14 pruebas Chromium, la prueba ampliada de alineación, `manage.py check`, `makemigrations --check --dry-run` y `git diff --check`. Firefox sigue pendiente de comprobación en la PC del usuario.

## UI-04 · 26 de noviembre de 2026

**Objetivo y alcance.** Aplicar la nueva dirección de búsquedas, formularios, títulos, tarjetas, tablas, inventario, sidebar y tipografía (RF-03, RF-04 y RF-05). Añadir fecha y estado informativo a proyectos. No cambiar cálculos de stock, compras, IVA ni entregas.

**Cambios.** Los buscadores automáticos carecen de rótulo visible y botón Aplicar, mantienen etiqueta accesible y anuncian solo campos buscados por el backend. El buscador DataTables se mueve fuera de la tarjeta sin duplicar su motor. Los botones Agregar comparten componente visual y se sitúan junto al título principal. Los formularios comparten campos, errores, espacios y acciones; las etiquetas indican `(opcional)` donde corresponde y omiten ese marcador en fechas condicionadas por el estado de pago. Las tablas cargan DataTables Responsive 3.0.8 y su adaptador BS5 local: un botón nativo por fila revela las columnas ocultas y no activa la navegación. Inventario muestra un extracto de Descripción y el nombre enlazado sin subrayado; Entregados sitúa Pendiente antes de la cantidad. El sidebar conserva fondo, grupos y franja; títulos más pequeños en mayúsculas y opciones más separadas. Calibri es primera opción con respaldo sans-serif, sin distribuir archivos de la fuente. Inicio usa tarjetas sin iconos y con separador.

**Proyectos y rutas.** Se añade `created_on` automático según la fecha local de Chile, no editable, y estado En curso/Terminado. Los antiguos sin fecha fiable conservan `NULL` y muestran «Sin fecha registrada»; la migración asigna En curso como estado inicial sin bloquear operaciones. La edición permite cambiar el estado. Inventario reemplaza el listado del catálogo: `/catalogo/` redirige allí y se elimina la vista, plantilla y endpoint exclusivos del listado, manteniendo fichas, formularios y categorías.

**Verificación visual y automatizada.** En Chromium se comprobó 1440 → 390 → 320 → 1440 px sin recarga: la tabla volvió a medir lo mismo que su contenedor; a 320 px ocultó columnas y el control por fila mostró los datos restantes sin navegar. También se abrió una pestaña de tabla inicialmente oculta, cuyo contenedor y tabla midieron ambos 280 px en móvil. Capturas: [inicio](capturas/ui04-inicio.png), [proyectos](capturas/ui04-proyectos.png), [inventario escritorio](capturas/ui04-inventario-escritorio.png), [inventario móvil expandido](capturas/ui04-inventario-movil-expandido.png), [inventario tras volver a escritorio](capturas/ui04-inventario-vuelta-escritorio.png), [pestaña de proyectos móvil](capturas/ui04-pestana-proyectos-movil.png) y [edición de proyecto móvil](capturas/ui04-editar-proyecto-movil.png). No hubo errores de consola en ese recorrido. Pasaron 185 pruebas Django y 14 pruebas Chromium, además de `manage.py check`, `makemigrations --check --dry-run`, `node --check`, integridad de seis paquetes locales y `git diff --check`.

**Limitaciones.** Firefox no está instalado aquí; la descarga del motor de Playwright devolvió HTTP 403. Calibri no está incorporada y solo se verá donde esté instalada. Falta confirmación visual en Firefox de la PC del usuario.

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
