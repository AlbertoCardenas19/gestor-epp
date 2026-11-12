# Flujos y responsabilidades conversados

## 1. Necesidad, cotización y compra
Proceso descrito por el usuario [S1, respuesta 9; S2, respuesta 11]:

1. La prevencionista prepara una lista de necesidades.
2. Obtiene cotizaciones.
3. Presenta las cotizaciones al jefe.
4. El jefe aprueba.
5. Tras la aprobación, la prevencionista efectúa la compra.

Esta secuencia representa el negocio. No fija estados de software, botones, notificaciones, cantidad de cotizaciones, comparación automática ni forma de aprobar dentro de la aplicación.

## 2. Entregas y destinatarios
Proceso descrito por el usuario [S1, respuestas 4 y 6; S2, respuesta 12]:

1. La prevencionista entrega los elementos a otra persona.
2. Posteriormente se entregan EPP a trabajadores.
3. El sistema debe permitir conocer a cuáles trabajadores llegaron.

Posteriormente el usuario acordó comenzar con entrega directa al trabajador,
identificado por nombre completo, y descontar la cantidad al entregar. Una entrega
que supere el saldo disponible se bloquea. [S10] El cargo del intermediario y la
distribución posterior no forman parte de esta primera versión y siguen pendientes.

S12 permite corregir los seis campos de una entrega mediante un reemplazo vinculado,
conservando el original. S13 permite anular una entrega vigente equivocada con
motivo obligatorio y restitución única en su proyecto y elemento actuales. Un
original sustituido no puede anularse. Esto no representa una devolución física.

## 3. Inventario, devoluciones y reposiciones
Se pidió inventario por proyecto y registro de entregas, devoluciones y reposiciones. [S1, respuestas 5 y 6]

Posteriormente se acordó el primer flujo de inventario: una apertura por proyecto
y elemento antes de las entradas, cantidades enteras, apertura de cero o más y
entradas mayores que cero. La prevencionista registra todas estas operaciones.
Las correcciones anulan con motivo y crean un reemplazo vinculado, conservando
el original; el saldo suma únicamente los registros vigentes. [S9]

S10 añade entregas directas que restan unidades del saldo del proyecto.
Las demás salidas, devoluciones y reposiciones siguen pendientes.
No trasladar reglas de ventas de otro proyecto a este sistema.

## 4. Finanzas por proyecto
La empresa necesita gestionar presupuestos y el dinero que ingresa y sale de cada proyecto. La prevencionista no administra dinero. [S1, respuestas 7 y 8; S2, respuesta 13]

La separación de responsabilidades es conocida; el cargo que se hará cargo de las finanzas, sus permisos y el momento de incorporar esa operación al software siguen pendientes.

## Actores del negocio conocidos
| Actor | Responsabilidad o relación descrita | Lo que no se ha definido |
|---|---|---|
| Prevencionista | Lista necesidades, cotiza, presenta al jefe, compra tras aprobación y entrega a otra persona; usuaria inicial de la app. | Permisos exactos y registro de etapas realizadas por terceros. |
| Jefe | Aprueba las compras. | Si tendrá cuenta y cómo se registrará su decisión. |
| Persona receptora inicial | Recibe elementos de la prevencionista. | Cargo, cuenta y responsabilidad de registro. |
| Trabajadores destinatarios | Reciben finalmente los EPP y deben ser identificables en la trazabilidad. | Datos de identificación, cuentas y comprobantes de entrega. |
| Empresa | Necesita gestionar presupuestos e ingresos/egresos por proyecto. | Responsable financiero concreto y permisos. |

Los actores son participantes del proceso. Esta tabla no establece roles de autenticación ni cuentas obligatorias para todos.

Referencias: [fuentes](05-fuentes.md).
