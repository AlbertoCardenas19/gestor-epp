# Requisitos recuperados del proyecto

Todos los RF de esta tabla corresponden a necesidades expresadas por el usuario en las fuentes indicadas. La redacción sintetiza conversaciones; no es transcripción literal. “Confirmado” no significa implementado ni prioridad de primera entrega.

| ID | Necesidad confirmada | Fuente | Detalle no cerrado |
|---|---|---|---|
| RF-01 | Contemplar una empresa con varios proyectos. | S1, respuesta 1 | Datos de cada proyecto y su ciclo de vida. |
| RF-02 | Permitir el uso inicial por la prevencionista y contemplar incorporar más usuarios posteriormente. | S1, respuesta 2 | Cuentas, autenticación, permisos y momento de ampliación. |
| RF-03 | Ser una aplicación web utilizable desde computador y celular. | S0, S1, respuesta 3 | Diseño de pantallas y dispositivos/navegadores específicos. |
| RF-04 | Mantener inventario por proyecto. | S1, respuesta 5 | Entradas, stock inicial, ajustes y reglas de movimientos. |
| RF-05 | Gestionar inicialmente EPP y señaléticas, con posibilidad de añadir otros elementos más adelante. | S2, respuesta 14 | Estructura del catálogo y atributos de cada tipo. |
| RF-06 | Contemplar la lista de necesidades y las cotizaciones que la prevencionista obtiene y presenta al jefe. | S1, respuesta 9 | Registro, comparación y estados dentro de la aplicación. |
| RF-07 | Contemplar que el jefe aprueba la compra y, tras esa aprobación, la prevencionista la realiza. | S2, respuesta 11 | Cómo se registra o realiza la aprobación y si el jefe usa la app. |
| RF-08 | Registrar entregas de los elementos; el proceso incluye que la prevencionista entrega a otra persona. | S1, respuestas 4 y 6 | Identificación del receptor, campos y responsable de registrar. |
| RF-09 | Conocer a qué trabajadores se entregan posteriormente los EPP; la trazabilidad debe llegar a ellos. | S2, respuesta 12 | Quién registra la entrega posterior y cómo se vincula con la inicial. |
| RF-10 | Registrar devoluciones. | S1, respuesta 6 | Motivos, destinos y efecto sobre el inventario. |
| RF-11 | Registrar reposiciones. | S1, respuesta 6 | Motivos, condiciones y relación con entregas anteriores. |
| RF-12 | Permitir adjuntar facturas, comprobantes de transferencia y cotizaciones. | S1, respuesta 9 | Registro al que se adjuntan, formatos, límites y acceso. |
| RF-13 | Contemplar la gestión de presupuestos de los proyectos para la empresa. | S1, respuesta 8; S2, respuesta 13 | Quién los gestiona, estructura y relación con compras. |
| RF-14 | Contemplar la gestión del dinero que ingresa y sale de cada proyecto. La prevencionista no administra dinero. | S1, respuesta 7; S2, respuesta 13 | Operaciones, responsables y permisos concretos. |

## Lectura conjunta de los requisitos
- RF-08 y RF-09 deben leerse juntos: registrar solo la entrega al intermediario no satisface la trazabilidad pedida.
- RF-07 describe una condición del proceso de negocio. No prueba que exista o deba existir ya una pantalla para que el jefe apruebe.
- RF-13 y RF-14 deben leerse con la aclaración de S2: la necesidad financiera de la empresa no asigna esas funciones a la prevencionista.
- RF-05 expresa extensibilidad del tipo de elementos, no un catálogo adicional ya definido.
- RF-02 expresa crecimiento futuro de usuarios; no permite asumir una matriz completa de roles.

## Lo que esta lista no fija
No se recuperaron campos definitivos, fórmulas, escalas, estados, umbrales de rendimiento, criterios de stock, firmas ni una prioridad por requisito. Los detalles permanecen en [pendientes](04-pendientes.md), de acuerdo con lo indicado por el usuario en S3.

Referencias: [fuentes](05-fuentes.md).
