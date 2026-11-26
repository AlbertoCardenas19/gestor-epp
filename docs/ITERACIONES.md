# Iteraciones de gestor-epp

## Estado actual

Iteración UI-01 implementada y verificada. Navegación, listados y estilos compartidos ajustados; lista para su publicación en `origin/main`.

## Pendientes

- Decisiones funcionales abiertas de [docs/04-pendientes.md](04-pendientes.md), en particular el cálculo automático de IVA (P-07), aprobación de compras, devoluciones y reposiciones.
- Confirmar en la PC del usuario el recorrido visual y funcional con sus datos locales.

## Próximo paso

Actualizar la copia Ubuntu desde `origin/main` y probar el recorrido con los datos locales.

## UI-01 · 26 de noviembre de 2026

**Objetivo.** Unificar la navegación y presentación de inventario y listados sin alterar las reglas de stock, solicitudes, entregas o compras (RF-03, RF-04 y RF-05).

**Cambios implementados.** Sidebar agrupado sin iconos en los enlaces, franja contraída y control circular; acceso «Inventario» único en el menú; creación junto a filtros y búsqueda; enlaces generales redundantes retirados; tablas blancas con hover gris; filas de inventario navegables con enlace real; acciones de inventario accesibles desde la ficha; indicador «Pendiente» junto a entregados; ajuste de ancho mediante la API compartida de DataTables.

**Verificaciones realizadas y resultados.** `manage.py check`, `compileall`, `node --check` y `makemigrations --check --dry-run` pasaron; no se detectaron cambios de modelos. Pasaron 186 pruebas Django y 12 pruebas Chromium sobre bases temporales PostgreSQL 17. Chromium comprobó anchos 320, 390 y 1440 px, sidebar, controles, tablas, navegación por fila, indicador pendiente, cambios de tamaño y errores de consola.

**Limitaciones y pendientes.** Las decisiones funcionales de `docs/04-pendientes.md`, incluido el IVA automático, siguen abiertas. No se añadieron migraciones ni dependencias de producción.

**Entrega.** Verificada y preparada para publicar. El hash del commit que incluye esta entrada se informará con el push y podrá añadirse al documento en la próxima actualización.
