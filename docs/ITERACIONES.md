# Iteraciones de gestor-epp

## Estado actual

Iteración UI-01 publicada. UI-02 implementada y verificada: la hoja propia usa una URL ligada a su contenido para que el navegador cargue los estilos actuales tras actualizar el proyecto.

## Pendientes

- Decisiones funcionales abiertas de [docs/04-pendientes.md](04-pendientes.md), en particular el cálculo automático de IVA (P-07), aprobación de compras, devoluciones y reposiciones.
- Confirmar en la PC del usuario el recorrido visual y funcional con sus datos locales tras actualizar desde `origin/main`.

## Próximo paso

Actualizar la copia Ubuntu desde `origin/main` y comprobar que el navegador solicita la URL nueva de `app.css` y muestra el sidebar expandido y contraído como en las capturas.

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
