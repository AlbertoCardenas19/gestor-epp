# Dos iteraciones de entregas directas

## Alcance confirmado — S11

Se mantiene el registro directo de destinatario por nombre completo, elemento del
catálogo común, proyecto, cantidad, fecha y observación opcional. Las entregas
descuentan el inventario del proyecto y se bloquean por saldo insuficiente.
El destinatario permanece visible en el historial. No se implementan intermediarios.

El usuario confirmó haber probado las entregas directas en su PC y solicitó:

1. Acordar e implementar correcciones de entregas.
2. Después de completar la primera iteración, acordar e implementar la anulación
   de un registro equivocado. Una devolución física no forma parte de estas iteraciones.

Cada iteración debe cerrar con comprobaciones de saldos, validaciones, historial
y regresión de los flujos existentes, revisión de escritorio y móvil y Firefox
si está disponible, resumen y un commit separado. No se hará push.

## Diagnóstico inicial

El punto de partida fue `bcffa50`. La corrección de entregas estaba deshabilitada
explícitamente tanto en el servicio como en la vista. Las correcciones de apertura
y entrada conservan el original anulado, el motivo y un reemplazo vinculado, con
transacción y control de saldo negativo. El historial enlazaba los reemplazos
dentro de una misma posición; cambiar proyecto o elemento requería enlaces
entre historiales y validación de las dos posiciones afectadas.

## Iteración 1 — reglas aprobadas (S12)

El usuario respondió «sí a todo» a las tres decisiones presentadas: campos,
conservación del original mediante reemplazo y ajustes de saldo. Quedan aprobadas
para esta iteración las siguientes reglas:

- Permitir corregir destinatario, elemento, proyecto, cantidad, fecha del hecho
  y observación. Mantener la operación como entrega directa y no modificar la
  fecha de captura ni los datos originales.
- Exigir un motivo, conservar el original como sustituido y crear un reemplazo
  vinculado. Solo el registro vigente afecta al saldo. Permitir corregir nuevamente
  el reemplazo, manteniendo la cadena; no corregir originales ya sustituidos.
- Cambiar solo destinatario, fecha u observación no cambia el saldo.
- Para la misma posición, calcular el efecto neto como saldo actual más cantidad
  anterior menos cantidad corregida. Una corrección de entrega no usa cantidad
  cero: la cantidad sigue siendo un entero positivo.
- Si cambia proyecto o elemento, deshacer contablemente el descuento original
  y descontar la cantidad correcta en la posición de destino. Esto rectifica un
  registro equivocado; no representa una transferencia física de materiales.
- Aplicar todo o nada, conservando las reglas de apertura previa y saldo suficiente.
  Si la posición de destino no tiene apertura o no alcanza el saldo, conservar el
  registro y ambos saldos sin cambios. No crear una apertura ni una entrada automática.

## Cierre de la iteración 1

La iteración 1 está implementada y verificada: 91 pruebas aprobadas sobre
PostgreSQL. Se comprobaron las seis modificaciones, ajustes netos, cambios de
proyecto y elemento, rechazo sin apertura o saldo, reenvíos, cadenas y concurrencia.
Chromium verificó escritorio y móvil, enlaces de ida y vuelta entre historiales
y pantallas sin desbordamiento a 320, 390 y 1440 píxeles. Se intentó Firefox,
pero falta su ejecutable y no hay instalación del navegador en esta máquina.
No fueron necesarias migraciones ni dependencias nuevas.

## Iteración 2 — todavía sin reglas acordadas

Después de la primera iteración se definirá la anulación sin reemplazo: conservación
del registro, motivo, efecto sobre existencias y protección ante solicitudes repetidas.
No se implementará como devolución física ni se adelantará su desarrollo sin acuerdo.
