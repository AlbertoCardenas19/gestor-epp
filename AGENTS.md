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
- No elijas Django, PostgreSQL o Render como decisiones cerradas por aparecer en una recomendación previa.
- Inspecciona el código y las instrucciones existentes antes de trabajar. Esta documentación no acredita ninguna implementación.
- Conserva el trabajo existente. No sobrescribas instrucciones vigentes sin integrarlas y resolver contradicciones con el usuario.
- Cuando trabajes en una funcionalidad solicitada, referencia RF-xx y explica qué decisión falta, si corresponde. Verifica el comportamiento modificado e informa el resultado real.
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
- Las columnas de acciones no se buscan ni ordenan. Conservar los filtros de negocio.
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
