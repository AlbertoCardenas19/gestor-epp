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
