# Stock común y solicitudes por proyecto

Estado: acuerdos confirmados S16/S19 y diseño técnico propuesto para el próximo
cambio. **Primer incremento de consulta y entradas comunes implementado;
solicitudes/reservas todavía pendientes**. RF-01, RF-04, RF-05, RF-08 y RF-09.

## Acuerdos confirmados

- Existencias reales comunes de empresa, en lugar de aperturas por proyecto.
- Al registrar un elemento, una cantidad inicial vacía equivale a cero. Se pueden
  registrar entradas después.
- Agregar un elemento a un proyecto representa una solicitud. Reserva unidades
  y se limita a lo disponible; no crea stock negativo ni solicitudes sin cobertura.
- La entrega real al trabajador descuenta existencias. Se permiten entregas
  parciales; lo pendiente permanece reservado.
- Se puede reducir o cancelar lo pendiente con motivo obligatorio e historial,
  liberando su reserva sin modificar las entregas ya realizadas.
- Anular o reducir una entrega devuelve esas unidades a lo pendiente/reservado
  de la misma solicitud.
- Corregir hacia otro proyecto o elemento exige seleccionar una solicitud de
  destino existente con cantidad pendiente suficiente.
- Se trasladan los saldos anteriores y se conserva su historial. Los datos del
  PC son de prueba; no se ha solicitado borrarlos.
- S21: las entregas anteriores sin solicitud conservan corrección/anulación y
  ajustarán el stock común sin solicitudes ni reservas ficticias.
- Entregas realizadas sigue siendo la vista inicial del proyecto. Se mantienen
  nombre completo del trabajador, fecha, observación opcional y trazabilidad.

## Modelo propuesto para implementar esos acuerdos

Separar tres conceptos: elemento del catálogo, existencias comunes y solicitud
de un proyecto. La cantidad no debe representar simultáneamente el stock de la
empresa y lo pedido por un proyecto.

- **Existencias:** apertura y entradas menos entregas vigentes.
- **Reservado:** suma de cantidades pendientes de solicitudes vigentes.
- **Disponible para nuevas solicitudes:** existencias menos reservado.

Ejemplo: 10 cascos comunes; Norte solicita 4 y Sur solicita 3. Hay 7 reservados
y 3 disponibles. Entregar 2 de Norte deja 8 existencias, 5 reservados y los mismos
3 disponibles. Anular esa entrega restituye 10 existencias y 7 reservados, con
3 disponibles. No es una devolución física.

Una solicitud de 4 con 2 ya entregados conserva 2 pendientes/reservados. Reducir
lo pendiente a 1 libera una unidad, con motivo e historial. No modifica las dos
unidades que ya se entregaron.

## Transición propuesta y secuencia de trabajo

1. Preparar la migración sin editar migraciones ya publicadas ni eliminar los
   registros actuales. Obtener el saldo vigente de cada combinación anterior
   proyecto–elemento y sumar los saldos del mismo elemento para trasladarlos al
   stock común. Excluir originales sustituidos y entregas anuladas del cálculo,
   como hace actualmente el inventario.
2. Conservar datos originales, enlaces entre correcciones, motivos, fechas y
   proyectos del historial. Documentar la correspondencia del inventario anterior
   con el nuevo; no fabricar solicitudes para entregas históricas.
3. Implementar consulta de stock común y registro de entradas. Sustituir el
   requisito de apertura por proyecto, conservando el catálogo compartido.
4. Implementar solicitudes con reserva, entrega parcial y reducción/cancelación
   de lo pendiente. Mantener Entregas como pestaña inicial del proyecto.
5. Adaptar corrección/anulación a las solicitudes y al stock común, incluyendo
   selección explícita de solicitud de destino. Comprobar el tratamiento de los
   registros históricos que no tienen solicitud antes de habilitar escrituras.

Los puntos 1–3 tienen ya un primer incremento de consulta y entradas comunes,
descrito al final. Solicitudes, reservas y la adaptación de sus entregas siguen
siendo pasos pendientes; no están disponibles todavía.
Cada escritura debe validar existencias, reservas y pendiente dentro de una misma
transacción. Las solicitudes simultáneas no pueden reservar las mismas unidades.

## Comprobaciones necesarias

- La suma de saldos anteriores por elemento coincide con el stock común migrado;
  se conserva la trazabilidad de originales, reemplazos y anulaciones.
- Dos proyectos solicitan el mismo elemento sin duplicar stock ni reservas.
- Una solicitud que supera lo disponible se rechaza íntegramente, incluidas
  solicitudes simultáneas cuando solo queda cantidad para una.
- Entregas parciales mantienen el pendiente reservado y nunca superan ese pendiente.
- Reducir/cancelar lo pendiente libera solo su reserva y conserva el motivo.
- Corregir/anular entregas devuelve stock y reserva una sola vez; un fallo no
  deja ajustes parciales. Una corrección entre solicitudes valida ambos destinos.
- Se mantienen los flujos existentes de proyectos, catálogo y trazabilidad, y
  se comprueban las pantallas en escritorio y móvil con PostgreSQL.


## Primer incremento implementado

La consulta común integra los saldos anteriores sin copiarlos ni duplicarlos.
Se pueden registrar y corregir entradas de empresa, con historial. La migración
0003 conserva los registros anteriores. Se mantiene el flujo legado de entregas
por proyecto durante la transición. Solicitudes/reservas y cantidades iniciales
al crear elementos siguen pendientes. Ver [10-inventario-comun.md](10-inventario-comun.md).
