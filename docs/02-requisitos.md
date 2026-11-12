# Requisitos recuperados del proyecto

Todos los RF de esta tabla corresponden a necesidades expresadas por el usuario en las fuentes indicadas. La redacción sintetiza conversaciones; no es transcripción literal. “Confirmado” no significa implementado ni prioridad de primera entrega.

| ID | Necesidad confirmada | Fuente | Detalle no cerrado |
|---|---|---|---|
| RF-01 | Contemplar una empresa con varios proyectos. | S1, respuesta 1; S7 | Primera etapa: nombre obligatorio y descripción opcional. Otros datos y el ciclo de vida siguen pendientes. |
| RF-02 | Permitir el uso inicial por la prevencionista y contemplar incorporar más usuarios posteriormente. | S1, respuesta 2 | Cuentas, autenticación, permisos y momento de ampliación. |
| RF-03 | Ser una aplicación web utilizable desde computador y celular. | S0, S1, respuesta 3 | Diseño de pantallas y dispositivos/navegadores específicos. |
| RF-04 | Mantener inventario por proyecto. | S1, respuesta 5; S9 | Primera versión: una apertura por proyecto y elemento, antes de entradas posteriores; cantidades enteras, apertura de cero o más y entradas mayores que cero. La prevencionista registra todo. Correcciones mediante anulación con motivo y reemplazo vinculado, conservando el original y contando solo registros válidos. Otras reglas de movimientos siguen pendientes. |
| RF-05 | Gestionar inicialmente EPP y señaléticas, con posibilidad de añadir otros elementos más adelante. | S2, respuesta 14; S8 | Primera versión: catálogo común a todos los proyectos, nombre y tipo obligatorios (EPP o señalética), descripción opcional. Otros atributos y ampliación de tipos siguen pendientes. |
| RF-06 | Contemplar la lista de necesidades y las cotizaciones que la prevencionista obtiene y presenta al jefe. | S1, respuesta 9 | Registro, comparación y estados dentro de la aplicación. |
| RF-07 | Contemplar que el jefe aprueba la compra y, tras esa aprobación, la prevencionista la realiza. | S2, respuesta 11 | Cómo se registra o realiza la aprobación y si el jefe usa la app. |
| RF-08 | Registrar entregas de los elementos; el proceso conversado incluye que la prevencionista entrega a otra persona. | S1, respuestas 4 y 6; S10; S12 | Entrega directa al trabajador con nombre completo y descuento al entregar. S12 aprueba corregir los seis campos mediante reemplazo vinculado y ajuste transaccional de los saldos. Intermediarios y anulación sin reemplazo siguen pendientes. |
| RF-09 | Conocer a qué trabajadores se entregan los EPP; la trazabilidad debe llegar a ellos. | S2, respuesta 12; S10 | Primera versión: destinatario por nombre completo en cada entrega directa. La distribución mediante intermediarios sigue pendiente. |
| RF-10 | Registrar devoluciones. | S1, respuesta 6 | Motivos, destinos y efecto sobre el inventario. |
| RF-11 | Registrar reposiciones. | S1, respuesta 6 | Motivos, condiciones y relación con entregas anteriores. |
| RF-12 | Permitir adjuntar facturas, comprobantes de transferencia y cotizaciones. | S1, respuesta 9 | Registro al que se adjuntan, formatos, límites y acceso. |
| RF-13 | Contemplar la gestión de presupuestos de los proyectos para la empresa. | S1, respuesta 8; S2, respuesta 13 | Quién los gestiona, estructura y relación con compras. |
| RF-14 | Contemplar la gestión del dinero que ingresa y sale de cada proyecto. La prevencionista no administra dinero. | S1, respuesta 7; S2, respuesta 13 | Operaciones, responsables y permisos concretos. |

## Lectura conjunta de los requisitos
- RF-08 y RF-09 deben leerse juntos: registrar solo la entrega al intermediario no satisface la trazabilidad pedida.
- S10 limita el primer flujo a entregas directas y bloquea cantidades superiores
  al saldo disponible del proyecto. No da por implementada la distribución posterior.
- RF-07 describe una condición del proceso de negocio. No prueba que exista o deba existir ya una pantalla para que el jefe apruebe.
- RF-13 y RF-14 deben leerse con la aclaración de S2: la necesidad financiera de la empresa no asigna esas funciones a la prevencionista.
- RF-05 expresa extensibilidad del tipo de elementos, no un catálogo adicional ya definido.
- RF-02 expresa crecimiento futuro de usuarios; no permite asumir una matriz completa de roles.

## Lo que esta lista no fija
S7 confirma nombre obligatorio y descripción opcional para proyectos en esta etapa. S8 confirma los campos iniciales y el alcance común del catálogo descritos en RF-05. S9 registra los acuerdos iniciales de inventario y sus límites; su primer flujo está implementado según la [guía de desarrollo](06-desarrollo.md). Las demás reglas permanecen en [pendientes](04-pendientes.md), de acuerdo con lo indicado por el usuario en S3.

Referencias: [fuentes](05-fuentes.md).
