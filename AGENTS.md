# Instrucciones para Codex — App prevención de riesgos

## Identidad del proyecto
Este repositorio corresponde a la app web de gestión para la amiga prevencionista del usuario: proyectos, EPP, señaléticas, inventario, cotizaciones, compras, entregas y finanzas por proyecto.

## Documentación que debes leer
1. [Índice y uso](docs/README.md).
2. [Producto y contexto](docs/01-producto.md).
3. [Requisitos recuperados](docs/02-requisitos.md).
4. [Flujos y responsabilidades](docs/03-flujos-y-responsabilidades.md).
5. [Pendientes](docs/04-pendientes.md).
6. [Fuentes y límites](docs/05-fuentes.md).
7. [Guía de desarrollo](docs/06-desarrollo.md).
8. [Inventario y solicitudes vigentes](docs/11-inventario-y-solicitudes.md): S23 distingue solicitado de entregado real; mantiene necesidades de compra y el stock común de S22.
9. [Registro de iteraciones](docs/ITERACIONES.md): lee su estado y pendientes antes de retomar el proyecto.

## Instrucciones de esta entrega
Las siguientes pautas sirven para trabajar con esta documentación; no son nuevos requisitos del producto.

- Usa solo necesidades de este proyecto. No incorpores la otra idea de automatizar documentos para profesionales, ni requisitos de otros repositorios del usuario.
- La generación de documentos PDF/Excel, IPER, AST, reportes de incidentes y charlas no tiene respaldo como alcance acordado de este proyecto en las fuentes recuperadas. Los adjuntos de facturas, transferencias y cotizaciones sí lo tienen.
- Distingue necesidad confirmada, contexto, detalle pendiente y propuesta técnica. Que una funcionalidad se haya conversado no significa que esté implementada ni que se haya priorizado para el MVP.
- Respeta la aclaración posterior: la prevencionista no administra dinero. La gestión financiera corresponde a una necesidad de la empresa y no autoriza asignarle esa responsabilidad a ella.
- La trazabilidad no termina en el encargado que recibe inicialmente los EPP; debe llegar a los trabajadores destinatarios.
- No interpretes actores del negocio como cuentas o roles de software ya definidos. Inicialmente solo ella usará la app.
- No supongas que la aprobación del jefe ocurre dentro de la aplicación: ese mecanismo está pendiente.
- No impongas reglas de stock, fórmulas financieras, firmas, campos obligatorios, estados, políticas de reposición ni permisos sin respaldo. Consulta el pendiente pertinente cuando bloquee una implementación solicitada.
- La recomendación histórica no fijó Django, PostgreSQL ni Render; la decisión posterior de conservar Django y PostgreSQL para la interfaz actual sí prevalece. Render no está fijado.
- Inspecciona el código y las instrucciones existentes antes de trabajar. Esta documentación no acredita ninguna implementación.
- Conserva el trabajo existente. No sobrescribas instrucciones vigentes sin integrarlas y resolver contradicciones con el usuario.
- Cuando trabajes en una funcionalidad solicitada, referencia RF-xx y explica qué decisión falta, si corresponde. Verifica el comportamiento modificado e informa el resultado real.
- Al terminar cada iteración, actualiza `docs/ITERACIONES.md`: conserva todas las entradas previas y registra estado, pendientes, próximo paso, cambios y verificaciones realmente realizadas.
- Si el usuario cierra una decisión pendiente, registra su respuesta y actualiza los documentos afectados. No presentes sugerencias propias como acuerdos previos.

## Convenciones actuales de interfaz — instrucción del usuario (12 de noviembre de 2026)

Estas convenciones se establecen en la solicitud actual, no en acuerdos históricos:

- Mantener Django, PostgreSQL, CoreUI con su base Bootstrap y la interfaz en español.
- Usar DataTables para toda tabla que requiera búsqueda, ordenación o paginación.
  Reutilizar la configuración compartida de `projects/static/projects/datatables.js`
  y el adaptador del servidor de `projects/datatables.py`, cuando corresponda.
- Asegurar que búsqueda y ordenación cubran todos los registros de la consulta.
  Elegir cliente o `serverSide` justificando volumen y arquitectura; nunca inicializar
  DataTables en cliente sobre una única página parcial de Django.
- Las columnas de acciones no se buscan ni ordenan. Conservar el alcance de negocio de cada consulta.
- Usar componentes oficiales CoreUI para interacciones estándar que cubra: dropdown,
  sidebar, modal, collapse, etc. El código propio debe limitarse a necesidades de la
  app, integración entre componentes, persistencia y presentación específica.
- Mantener versiones compatibles y fijadas, con sus licencias e integridad. No cargar
  Bootstrap CSS/JS además de CoreUI ni duplicar bibliotecas, controles o inicializaciones.
- Conservar los diseños elegidos, incluidas las tarjetas de proyectos. No convertir
  todos los listados en tablas. Búsqueda de tarjetas no equivale a una tabla DataTables.
- Justificar cualquier excepción técnica **antes** de introducir una implementación
  alternativa; no reconstruir por comodidad componentes ya cubiertos por las bibliotecas.
- Consultar `docs/09-componentes-y-datatables.md` para versiones, carga, reutilización
  y verificación. Estas convenciones no autorizan cambiar reglas ni datos de inventario.
- Reutilizar los componentes compartidos para pestañas, paginaciones, indicadores de
  carga, búsquedas, estados y acciones. No crear variantes independientes por
  pantalla cuando cumplen la misma función.
- Toda paginación debe conservar su motor (DataTables, Django o selector) y aplicar la
  presentación global. Proyectos permanece en tarjetas con seis resultados por página.
- Las columnas `data-actions` deben usar la configuración y clase compacta compartidas,
  sin búsqueda ni ordenación y sin impedir interacción táctil, teclado o menús visibles.
- Los indicadores compartidos deben retrasar solo su presentación, nunca la petición:
  una respuesta rápida no destella; las actualizaciones conservan contenido y los
  errores se distinguen de resultados vacíos.
- Las pestañas interactivas deben usar CoreUI y el ajuste compartido de DataTables al
  mostrar contenido oculto. Los cambios comunes deben aplicarse a todas sus instancias
  equivalentes, no copiarse en una pantalla concreta.

## Convenciones de la iteración UI-04 — 26 de noviembre de 2026

- Inventario reemplaza el listado del catálogo. `/catalogo/` redirige a Inventario;
  creación, edición y ficha de elementos permanecen. Ningún Cancelar debe volver al
  listado retirado.
- Los buscadores automáticos no tienen botón Aplicar. El buscador de tarjetas de
  Proyectos mantiene su presentación; las búsquedas de tablas siguen la norma vigente
  de `docs/diseno-gestor-epp.md`.
- Los botones Agregar proyecto, elemento, categoría, factura y proveedor comparten
  presentación y se sitúan junto al título principal, también en móvil.
- Las tablas `serverSide` usan DataTables Responsive 3.0.8 y su adaptador BS5 local:
  al estrecharse muestran las columnas que caben y un botón por fila permite consultar
  las demás con teclado. El control no navega a la ficha. Buscar, ordenar y paginar
  siguen operando sobre el conjunto del servidor.
- Los formularios comparten etiquetas, errores, espaciado y acciones. Solo se indica
  `(opcional)` donde el campo realmente lo es; se respetan obligaciones condicionales.
- Calibri es la primera fuente solicitada, seguida de fuentes sans-serif. No se
  distribuye Calibri: solo aparece si el equipo la tiene instalada.
- Los proyectos nuevos reciben fecha de creación automática y estado En curso. La
  edición permite pasar a Terminado sin bloquear operaciones; proyectos antiguos sin
  fecha fiable muestran «Sin fecha registrada».

## Sistema visual permanente — 27 de noviembre de 2026

- Leer `docs/diseno-gestor-epp.md` antes de modificar la interfaz. Usar Punto Aparte
  `work` en `9f359ac` como referencia visual, conservando las decisiones propias de EPP.
- Reutilizar tokens y componentes compartidos; no inventar variantes de botones,
  campos, tarjetas, tablas, navegación o carga por pantalla.
- Mantener CoreUI, DataTables y `serverSide` existentes, sin copiar dependencias ni
  lógica de negocio de Punto Aparte. Calibri continúa primero como fuente local.
- En tablas, el buscador oficial permanece dentro de la tarjeta junto a «Mostrar X
  filas», con etiqueta visible «Buscar». El placeholder refleja solo criterios reales,
  sin «Buscar por» ni puntos suspensivos. No se añade otro motor ni botón de envío.
- Usar un token común `#EAF4FB` para encabezados de tabla con texto oscuro, y 1rem
  de separación entre controles superiores, tabla y controles inferiores. Mantener
  filas blancas y hover gris claro.
- No mostrar filtros adicionales en los listados de tablas por ahora. Conservar el
  alcance de cada pantalla y mostrar los estados consultables con identificación clara.
  Proyectos y los selectores de elementos quedan fuera de este cambio de búsqueda.
- Inicio usa tarjetas compartidas con área de acciones separada por línea y alineada
  abajo. Facturas enlaza al listado existente.
- Comparar visualmente las pantallas afectadas, teclado y anchos estrechos, incluido
  redimensionamiento de ida y vuelta. Retirar reglas sustituidas, actualizar la guía
  vigente y registrar cada iteración. Justificar y verificar toda excepción.
