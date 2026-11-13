# Stock común y solicitudes por proyecto

Estado actual: implementado. La [guía 11](11-inventario-y-solicitudes.md) describe
la interfaz, modelos, verificación y recorrido vigente conforme a S23. RF-04/RF-05,
RF-08/RF-09. La guía 10 conserva el primer incremento y migración 0003.

## Evolución de las decisiones

S16/S19 confirmaron stock común, solicitudes con reserva, entregas parciales,
reducción/cancelación pendiente con motivo, correcciones entre solicitudes y
conservación de saldos/historial. S21 mantiene las entregas antiguas sin solicitudes
ficticias: sus correcciones/anulaciones solo ajustan stock común.

S22 reemplaza el rechazo de solicitudes sin cobertura: se reserva lo disponible
y el resto queda como necesidad de compra. Une Catálogo e Inventario en una sola
sección y reúne reservas y entregas reales en la columna «Entregados», manteniendo
su diferencia internamente y la trazabilidad de entregas efectivas al trabajador.
Al reducir el pendiente se reduce primero lo que falta comprar, conservando reservas.

## Implementación

Se mantienen `Item`, posiciones y libro de movimientos; las reservas se modelan
con `StockRequest`, sus eventos y una FK nullable en las entregas reales.
No se duplican saldos ni se borran datos. Migraciones 0003 y 0004.

Inventario general muestra disponible para reservar y asignado/entregado. Dentro
del proyecto se solicita, reserva, confirma entrega o reduce/cancela pendiente.
Entregas sigue como pantalla inicial. Una entrega corregida/anulada devuelve
unidades a la reserva de su solicitud; una histórica sin solicitud solo ajusta
el stock común. Los cambios se validan con bloqueos y transacciones atómicas.

Las necesidades de compra no son compras ni reservas de unidades inexistentes.
Cotizaciones, aprobación, devoluciones y reposiciones siguen pendientes.

S23 sustituye la presentación combinada de S22: Entregados solo cuenta entregas
reales vigentes. La solicitud compromete stock, pero no acredita recepción. Se
conservan las necesidades de compra por aclaración explícita del usuario.
