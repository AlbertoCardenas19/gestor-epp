# Aspectos pendientes de definir

El usuario indicó que las reglas de negocio detalladas se verán más adelante durante el desarrollo. [S3]

Esta lista explicita huecos de la evidencia recuperada para evitar que Codex los rellene. No introduce funcionalidades ni condiciones nuevas. “No definido” significa que no se encontró una decisión suficiente, no que el usuario nunca haya tratado el tema.

| ID | Tema | Falta definir |
|---|---|---|
| P-01 | Primera entrega | Se acordó iniciar con crear, listar y consultar proyectos (S7). El alcance completo del MVP y el orden de los siguientes flujos siguen pendientes. |
| P-02 | Proyectos | Primera etapa: nombre obligatorio y descripción opcional, aceptados por el usuario en S7. Otros datos y el ciclo de vida siguen pendientes. |
| P-03 | Personas y acceso | S10 confirma nombre completo del trabajador en cada entrega directa. Identificación adicional, intermediarios, cuentas y permisos siguen pendientes. |
| P-04 | Catálogo | La iteración de compras incorpora categorías múltiples y creación de categorías. Sigue pendiente qué destinatarios alternativos podrán recibir elementos y qué datos requieren. |
| P-05 | Inventario | S9 confirma apertura inicial por proyecto y elemento, entradas posteriores, cantidades enteras y registro por la prevencionista para esta versión. Correcciones de aperturas y entradas mediante anulación con motivo y reemplazo vinculado. S10 añade descuento por entrega directa y bloqueo por saldo insuficiente. Otras salidas y movimientos siguen pendientes. Los acuerdos actuales pueden revisarse en el futuro. |
| P-06 | Cotización y aprobación | Datos y estados; cómo registrar la aprobación del jefe y si participa directamente en la app. |
| P-07 | Compra | Cálculo de IVA y total: tasas, redondeo, descuentos, flete, otros cargos y compras exentas u otros tratamientos. También queda pendiente la obligatoriedad de los datos de contacto del proveedor. |
| P-08 | Entregas | S10 confirma entrega directa; S12, corrección de seis campos con original conservado y reemplazo; S13, anulación de una entrega vigente o reemplazo vigente, con motivo y restitución única. Estas dos iteraciones están implementadas. Intermediarios y devoluciones físicas siguen fuera de su alcance. |
| P-09 | Devolución y reposición | Motivos, condiciones y efectos sobre stock y entregas. |
| P-10 | Adjuntos | Registro asociado, formatos, límites y acceso. |
| P-11 | Finanzas | Responsable, permisos, operaciones y relación de presupuestos con ingresos/egresos. |
| P-12 | Tecnologías | Django, PostgreSQL y CoreUI con Bootstrap confirmados en S7. Estructura detallada y alojamiento siguen pendientes. |
| P-13 | Comercialización y práctica | Condiciones formales de práctica y acuerdos comerciales concretos. La intención no equivale a un contrato. |

## Estado vigente de inventario y entregas — S16/S19/S21/S22/S23

P-05/P-08 se revisaron: stock común, solicitudes por proyecto con reserva parcial,
necesidad de compra por lo faltante, entregas parciales y reducción/cancelación del
pendiente con motivo e historial están implementados. Las correcciones/anulaciones
vinculadas restituyen reservas; las históricas sin solicitud solo afectan stock
común. S22 prioriza reducir necesidad de compra antes de liberar reservas. S23 separa
solicitado de entregado real y confirma conservar las necesidades de compra; limita
las entregas a lo comprometido pendiente.
[Guía actual](11-inventario-y-solicitudes.md). Los enunciados S9 de la tabla describen
la primera versión histórica, no la necesidad de abrir stock por proyecto hoy.

El registro de compras, proveedores y recepción se describe en la [guía de desarrollo](06-desarrollo.md#categorías-proveedores-y-facturas-de-compra--26-de-noviembre-de-2026). La aprobación, la prioridad automática entre proyectos y las devoluciones/reposiciones siguen pendientes.

## Recomendaciones anteriores que no son decisiones cerradas
Se recuperó una recomendación del asistente de usar Django, PostgreSQL y Render. No se recuperó aceptación explícita del usuario de esa combinación. [S6]

La decisión posterior S7 confirma Django, PostgreSQL y CoreUI con Bootstrap. Render sigue sin aprobación. No se fija una modalidad SaaS, licencia, reparto comercial ni costos mensuales.

## Instrucción al trabajar en un pendiente
Cuando una tarea dependa de un punto abierto, identificar qué falta y consultar lo necesario para esa tarea. No volver a preguntar necesidades que ya están confirmadas en [requisitos](02-requisitos.md). Una respuesta nueva debe registrarse con fecha y actualizar el requisito afectado, sin convertir una propuesta de Codex en aprobación del usuario.

Referencias: [fuentes](05-fuentes.md).
