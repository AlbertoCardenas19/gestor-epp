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

## Iteración 2 — reglas aprobadas (S13)

El usuario confirmó las cinco reglas:

- Anulación completa solo de una entrega vigente, con motivo obligatorio.
- Conservar datos, motivo y fecha; no crear un reemplazo.
- Restituir una vez su cantidad a la posición del registro vigente, incluso cuando
  sea un reemplazo corregido hacia otro proyecto o elemento.
- Informar «ya anulada» ante reenvíos, conservando la primera fecha y motivo y
  sin incrementar de nuevo las existencias.
- Rechazar originales sustituidos; se debe actuar sobre su reemplazo vigente.

Esto rectifica un registro equivocado, no una devolución física. Las devoluciones
siguen fuera del alcance de ambas iteraciones.

## Cierre de la iteración 2

Se agregó confirmación de anulación y estado «Anulado» con motivo y fecha en el
historial. El original corregido mantiene «Sustituido» aunque su reemplazo se anule.
Los enlaces entre ambos historiales se conservan; un registro anulado no ofrece
acciones de corrección ni otra confirmación de anulación.

El servicio bloquea la posición y marca el registro dentro de una transacción.
El saldo deja de descontarlo; no se crea una entrada de stock ni un registro extra.
Un reenvío conserva el motivo y fecha originales. Fallar después de actualizar
el registro también revierte la anulación y deja el saldo anterior.

Pasaron 109 pruebas en PostgreSQL: las 91 anteriores y 18 nuevas de anulación,
incluidas solicitudes simultáneas, carreras con corrección o nueva entrega,
conservación del original, sustitución entre posiciones, CSRF y fallo simulado
después de escribir en la base de datos. Chromium comprobó ambas iteraciones en
escritorio y móvil, sin desbordamiento a 320/390/1440 píxeles. Firefox se intentó
ejecutar y sigue sin estar instalado. No hay migraciones ni dependencias nuevas.

## Recorrido manual para ambas iteraciones

Con la aplicación iniciada y usando datos de prueba nuevos:

1. Crear los proyectos Norte y Sur, y los elementos Casco y Guantes en el catálogo común.
2. Abrir 20 cascos en Norte y 8 guantes en Sur.
3. Registrar una entrega de 5 cascos de Norte a Ana Pérez. Saldos: Norte/Casco 15,
   Sur/Guantes 8. El historial debe mostrar nombre, cantidad y fecha.
4. Corregir esa entrega: destinatario Luis Soto, proyecto Sur, elemento Guantes,
   cantidad 3, fecha correcta y observación nueva. Primero probar sin motivo y
   con cantidad 9: debe rechazarse sin cambios. Después indicar motivo y cantidad 3.
   Saldos: Norte/Casco 20 y Sur/Guantes 5.
5. Revisar el original «Sustituido», sus datos intactos y el enlace al reemplazo
   vigente de Sur. Comprobar el enlace de regreso al original. Intentar anular
   el original: debe rechazarse, sin cambiar ningún saldo.
6. En el reemplazo vigente, abrir «Anular entrega». Probar motivo vacío: no debe
   aplicarse. Confirmar con motivo «Registro duplicado»: Sur/Guantes vuelve a 8;
   Norte/Casco se mantiene en 20. Se conserva el destinatario y aparece «Anulado»
   con motivo y fecha, sin un nuevo reemplazo.
7. Volver a la dirección de anulación o reenviar la misma solicitud: debe informar
   que ya está anulada y mantener 20/8. El motivo y fecha no deben cambiar.
8. Registrar además una entrega directa de 2 cascos de Norte y anularla: el saldo
   pasa 20 → 18 → 20. Revisar que los originales sustituidos anteriores no cambien.
9. Repetir el recorrido con tamaño de móvil, comprobando formulario, validaciones,
   navegación entre historiales, datos originales y saldos tras recargar.

Si hubo una entrega real correcta y luego vuelve el material, no usar anulación:
eso requiere el futuro flujo de devolución física. Los dos commits de estas
iteraciones se conservan locales y no se hace push.
