# Inventario único y solicitudes por proyecto

Estado actual: S23 revisa la presentación de S22 y mantiene el stock común,
las necesidades de compra y las entregas directas RF-04/RF-05/RF-08/RF-09.
No implementa cotizaciones, pedidos a proveedores, aprobación ni compras.

## Decisiones vigentes — S23

- Inventario reúne elementos y cantidades, con columnas **Stock** disponible para
  nuevas solicitudes y **Entregados**, que cuenta **solo entregas reales vigentes**.
  Las solicitudes ya no aparecen como entregas. Sustituye la presentación de S22.
- En el inventario del proyecto, **Solicitado** muestra la cantidad original de la
  solicitud; el detalle/historial conserva sus reducciones. **Entregados** muestra
  solo lo efectivamente entregado. Una exclamación roja y accesible «Pendiente de
  entrega», situada antes de esa cantidad, indica que todavía queda pendiente,
  incluso de compra; desaparece al completar la entrega. «En proceso» conserva el estado.
  No se agrega una columna Reservado ni tres clases de stock en la interfaz.
- Se mantiene la regla de compra confirmada expresamente al aclarar S23: pedir
  más del stock no rechaza la solicitud. Se compromete lo disponible y se guarda
  el resto como necesidad de compra. Solo se rechazan entregas que superen lo
  comprometido pendiente. No se reservan unidades inexistentes.
- Se mantiene el botón **Confirmar entrega** existente y sus entregas parciales,
  con nombre completo del trabajador, cantidad, fecha y observación opcional.
  Confirmar no descuenta otra vez lo comprometido al solicitar.
- La solicitud no pide fecha. El servidor establece `occurred_on` con
  `timezone.localdate()` y `created_at` conserva el momento automático de registro.
  Se muestra la fecha y el momento en el detalle usando la zona configurada
  (actualmente UTC). No se cambia la zona, fechas antiguas ni fechas de movimientos.
  Correcciones, reducciones y reintentos no modifican esas fechas de solicitud.
- Se mantienen reducciones/cancelaciones con motivo e historial: primero se reduce
  lo que falta comprar y después se liberan reservas, sin cambiar entregas reales.
- Las entradas no se asignan automáticamente entre proyectos. «Reservar disponibles»
  continúa completando manualmente una solicitud con compra pendiente.

## Ejemplo obligatorio

| Paso | Stock | Solicitado del proyecto | Entregado real |
|---|---:|---:|---:|
| Crear elemento con 20 unidades | 20 | 0 | 0 |
| Solicitar 5 | 15 | 5 | 0 |
| Confirmar entrega de las 5 | 15 | 5 | 5 |

Mientras hay pendiente se muestra «En proceso» y la exclamación. La confirmación
repetida no duplica entregas ni descuenta stock otra vez. Anular por error devuelve
las unidades a la misma solicitud pendiente; no se trata de una devolución física.

Ejemplo de compra que se conserva: pedir 5 con stock 2 compromete 2 y deja 3 como
necesidad de compra. Reducir su pendiente a 3 conserva las 2 y deja solo 1 por comprar.
Confirmar más de las 2 comprometidas se rechaza. Tras una entrada, «Reservar disponibles» puede completar la solicitud.

## Navegación y consulta

Proyectos conserva tarjetas, búsqueda y filtros con **seis por página**. El
selector de solicitudes usa tarjetas pequeñas de nombre y stock disponible,
búsqueda sobre todos los elementos y seis por página. Incluye elementos en cero,
pues pueden generar necesidad de compra. La selección se guarda en el formulario,
fuera de los resultados, y se conserva al buscar, paginar y corregir errores.
El servidor vuelve a comprobar el stock dentro de la transacción al guardar.

Desde el nombre del elemento en Inventario se abre su ficha. Conserva nombre,
tipo y descripción; añade movimientos de todos los proyectos con filtro por
proyecto/empresa y proyectos relacionados con **Solicitado vigente** (menos lo
cancelado) y **Entregado al trabajador** (solo real vigente). Una entrega histórica
sin solicitud puede mostrar solicitado cero y entregado mayor que cero: no se
fabrica una solicitud para cuadrar esas columnas. Son cálculos de los datos actuales,
no nuevos campos de negocio. Información, Historial de movimientos y Proyectos se
presentan como pestañas CoreUI. Las tablas reutilizan DataTables `serverSide` y
ajustan sus columnas mediante la integración compartida al hacerse visibles.

Las listas esperan 180 ms antes de mostrar skeletons CoreUI en una carga inicial
asíncrona o un indicador discreto en actualizaciones, conservando contenido. Las
respuestas rápidas no producen destellos y la espera visual no retrasa la petición.
Un fallo termina
la carga y muestra cómo reintentar; no se presenta como un resultado vacío. Las
tarjetas/selector inicialmente renderizados por Django ya tienen contenido y no
hacen una segunda consulta inicial solo para mostrar una animación.

## Modelo y consistencia

`Item` sigue separado de las cantidades. El libro `StockRecord` sigue siendo la
fuente de existencias físicas: aperturas/entradas menos entregas vigentes, de todos
los proyectos y de empresa. No se copian saldos ni se fabrica historial.

`StockRequest` guarda proyecto, elemento, cantidad original, fecha y observación;
`allocated_quantity` incluye lo reservado y lo realmente entregado; lo cancelado
se registra aparte. Las entregas reales enlazan la solicitud mediante FK opcional.
`StockRequestEvent` guarda creación, ampliación de reserva y reducción, con antes,
después, fecha y motivo en las reducciones. Las entregas y sus rectificaciones
conservan además su propio historial original/reemplazo/anulación.

Fórmulas internas por solicitud:

- Entregado real = suma de sus entregas vigentes.
- Reservado pendiente = asignado − entregado real.
- Necesidad de compra = solicitado original − cancelado − asignado.
- Pendiente = reservado pendiente + necesidad de compra.

En Inventario: Stock = físico − reservas pendientes; Entregados = entregas
reales vigentes. La columna Solicitado del proyecto muestra el original; el resumen
de proyectos de una ficha muestra solicitado vigente, descontando lo cancelado. Se calculan con subconsultas SQL para evitar
multiplicar cantidades al unir movimientos y solicitudes.

Las escrituras bloquean primero los elementos comunes por ID, luego solicitudes
por ID y posiciones. Son transacciones atómicas; claves de envío únicas protegen
reintentos de creación, reserva, reducción y entrega. Se vuelve a validar el estado
con los bloqueos adquiridos. Las correcciones de entradas y rutas antiguas tampoco
pueden consumir existencias reservadas. No se permiten cantidades negativas.

Una corrección/anulación de entrega vinculada restituye su reserva pendiente en
la misma solicitud. Cambiar proyecto/elemento exige seleccionar explícitamente una
solicitud existente con reserva pendiente suficiente. Un original sustituido no
puede anularse. Una entrega histórica sin solicitud ajusta solo el stock común;
no se le crea una solicitud ficticia (S21). No son devoluciones físicas.

## Migración y compatibilidad

Aplicar `inventory/0004_stockrequestevent_stockrequest_and_more` con `migrate`.
Crea solicitudes/eventos, agrega la FK nullable y restricciones. No actualiza ni
elimina filas previas ni cambia sus cantidades; las entregas anteriores mantienen
FK nula. La migración 0003 anterior permite posiciones comunes de empresa.

El listado de Catálogo redirige a Inventario. Se conservan las rutas de fichas y
el endpoint JSON anterior para compatibilidad; la interfaz usa una sola tabla.
La pestaña Inventario del proyecto muestra ahora solicitudes; Entregas sigue como
pestaña inicial y muestra solo entregas reales, con filtro de estado. Los enlaces
antiguos de historial/corrección/anulación siguen funcionando. Las rutas antiguas
de apertura/entrada/entrega permanecen compatibles, pero no se ofrecen como el
recorrido nuevo: no se requiere abrir stock por proyecto para solicitar elementos.

## Interfaz y componentes

Inventario, solicitudes, historial común y entregas reutilizan DataTables
`serverSide`, adaptador SQL y configuración compartida. Búsqueda/ordenación se
aplican antes de paginar; Acciones no se busca ni ordena. Las tarjetas de proyectos
se conservan. CoreUI continúa gestionando menús y sidebar.

Se añade «×» accesible para limpiar y enfocar la búsqueda compartida de DataTables
y tarjetas. Es un complemento específico sobre sus controles existentes; no se
reimplementa un buscador ni un componente estándar de CoreUI. No hay nuevas
bibliotecas: DataTables 2.3.5, adapter Bootstrap 5 2.3.5, jQuery 3.7.1 y CoreUI 5.4.3
siguen locales y fijados. Consultar la [guía de componentes](09-componentes-y-datatables.md).

## Verificación de esta iteración — S23

- **169 pruebas Django aprobadas en PostgreSQL 17**, incluida la regresión completa
  de inventario, correcciones, anulaciones y concurrencia. El caso 20 → solicitar 5
  → confirmar 5 valida Stock 20/15/15 y Entregados 0/0/5. Cancelar devuelve a pendiente
  sin liberar para otro proyecto. Dos confirmaciones independientes simultáneas
  no entregan dos veces el mismo pendiente; los reintentos del mismo formulario
  siguen siendo idempotentes.
- Se comprobó reserva parcial y necesidad de compra, rechazo de entrega por encima
  de lo comprometido, consulta/ordenación de cantidades reales, filtros de movimientos,
  separación del historial sin solicitud, selector fuera de primera página y fecha
  del servidor en una zona distinta de UTC. No se modifican fechas previas.
- **8 pruebas Chromium aprobadas** con servidor y PostgreSQL temporales: seis
  proyectos por página, búsqueda/páginas del selector, selección persistente, estado
  y exclamación, confirmación existente y detalle con dos tablas independientes.
  Red retenida simuló carga inicial y actualización; respuestas 503 intencionales
  comprobaron errores, conservación y recuperación en DataTables, tarjetas y selector.
- Revisión a 320/390/1440 píxeles, menús/teclado y tarjetas previas. La revisión
  móvil usa emulación Chromium, no un teléfono físico. No hubo errores de JavaScript
  ni consola inesperados; los 503 anteriores fueron provocados por las pruebas.
- Firefox se intentó iniciar y sigue faltando su ejecutable. No se afirma su verificación.
- `check`, `makemigrations --check --dry-run`, integridad de bibliotecas locales,
  comprobación sintáctica JavaScript y `git diff --check` pasan. **Sin migraciones
  ni dependencias nuevas.** Sin conversión de datos históricos, commit ni push.

## Verificación anterior — S22

- 161 pruebas Django aprobadas en PostgreSQL 17: flujos anteriores, reserva parcial,
  necesidad sin existencias, confirmación parcial, reducción en la prioridad acordada,
  historial, formularios, CSRF, consulta entre proyectos, ordenación/páginas y búsqueda.
- Reintentos y concurrencia real: dos proyectos reservando lo mismo, creación y
  entrega repetidas, ampliación, anulación simultánea y reducción frente a entrega.
- Fallos después de escribir una entrega o reemplazo revierten toda la operación;
  se conserva el original y no quedan ajustes parciales. Las correcciones de entrada
  y las rutas antiguas protegen las reservas existentes.
- La migración 0004 se aplicó en la base local del entorno, que tenía cero
  movimientos; no cambió filas previas. La prueba de migración usa datos históricos
  en una base temporal y comprueba conservación campo a campo y saldo conjunto.
- 5 pruebas Chromium aprobadas sobre PostgreSQL temporal: flujo completo de pedir,
  registrar entrada, reservar, confirmar, corregir, anular y cancelar pendiente;
  búsqueda con ×, menús, teclado, tarjetas y tablas a 320/390/1440 píxeles.
  Sin desbordamiento horizontal ni errores de consola.
- Firefox se intentó iniciar; falta su ejecutable `firefox-1538/firefox/firefox`.
  No se certifica compatibilidad en ese navegador.

## Probar en Ubuntu

Con PostgreSQL iniciado, el código de esta iteración en tu copia y tu `.env` habitual:

```bash
cd ~/Proyectos/gestor-epp
.venv/bin/python manage.py check
.venv/bin/python manage.py test projects catalog inventory
.venv/bin/python manage.py runserver
```

Abrir http://127.0.0.1:8000/ y recargar con Ctrl+Shift+R. Esta iteración no agrega
migraciones ni dependencias; conservar las migraciones anteriores aplicadas.

1. Crear más de 6 proyectos; comprobar dos páginas, filtros y búsqueda.
2. En Inventario, crear un elemento de prueba con stock inicial 20.
3. En un proyecto, Inventario → Solicitar elemento. Buscar el elemento, seleccionarlo,
   buscar otro nombre/cambiar página y comprobar que se mantiene la selección.
4. Solicitar 5 sin indicar fecha: Stock 15, Solicitado 5, Entregados 0. Debe figurar
   «En proceso» con «Pendiente de entrega». Revisar la fecha automática en el detalle.
5. Desde el botón de entrega existente, confirmar 5 al trabajador: Stock 15,
   Solicitado 5, Entregados 5. Reenviar el mismo formulario no duplica unidades.
6. Solicitar más del stock: conserva necesidad de compra; no permite entregar más
   de lo comprometido. Se conservan entregas parciales y correcciones/anulaciones.
7. Pulsar el nombre del elemento en Inventario. Revisar datos, cantidades por proyecto
   e historial; filtrar otro proyecto y «Empresa (sin proyecto)». Las solicitudes
   pendientes no aparecen como entregas a trabajadores.
8. Probar vacío, búsqueda sin resultados y (con herramientas de red del navegador)
   red lenta/desconexión. La carga inicial asíncrona usa skeleton; al actualizar
   mantiene resultados. Un fallo muestra error y termina el indicador. Reintentar
   con otra búsqueda tras restablecer la red. Revisar también en móvil y con teclado.

No se incorporan compras/finanzas, intermediarios, devoluciones ni reposiciones.
No se reclasifican ni borran registros históricos.
