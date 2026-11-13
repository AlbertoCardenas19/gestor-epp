# Inventario único y solicitudes por proyecto

Estado actual: implementado según S16/S19/S21 y las revisiones S22 del usuario.
RF-04/RF-05 y entregas directas RF-08/RF-09; necesidades parciales de RF-06.
No implementa cotizaciones, pedidos a proveedores, aprobación ni compras.

## Decisiones confirmadas — S22

- Catálogo e Inventario se reúnen en «Inventario». Nombre y tipo se mantienen;
  la descripción opcional se conserva en formulario/ficha, fuera de la tabla.
- Dos columnas de cantidades en el inventario: **Existencias** disponibles para
  nuevas reservas y **Entregados**, que reúne entregas reales vigentes y reservas
  pendientes. Confirmar una entrega no vuelve a descontar lo reservado.
- Pedir más de lo disponible ya no se rechaza: se reserva lo disponible y el
  resto queda como necesidad de compra. Esto reemplaza el límite anterior de S16.
- Se confirma la entrega real, total o parcial, con nombre completo del trabajador,
  cantidad, fecha y observación opcional. Una reserva no acredita recepción física.
- Reducir/cancelar pendiente exige motivo e historial. Primero disminuye lo que
  falta comprar, conservando reservas mientras alcance la cantidad restante.
  Las entregas reales anteriores no cambian.

Implementación técnica: las entradas no asignan automáticamente unidades a las
solicitudes. «Reservar disponibles» permite completar una reserva manualmente,
mostrando antes lo disponible. Esta elección evita adjudicar prioridades entre
proyectos que no se han definido. No constituye una regla de prioridad automática
aprobada por el usuario.

## Ejemplo y significado de las cantidades

Se crean 5 cascos. Norte pide 4: quedan Existencias 1, Entregados 4. Sur pide 3:
se reserva 1 y faltan comprar 2; Inventario muestra Existencias 0, Entregados 5.
Norte confirma 2 entregas reales: las columnas siguen 0 y 5, pues esas unidades
ya estaban comprometidas. Su solicitud conserva otras 2 reservadas.

Caso de reducción confirmado: pedir 5, reservar 2 y necesitar comprar 3; reducir
el pendiente a 3 conserva las 2 reservadas y deja solo 1 por comprar. Reducirlo a
1 libera una reserva y elimina toda necesidad de compra. Cancelar el pendiente
libera las reservas restantes, sin borrar ni modificar entregas reales.

«Entregados» no es un límite sobre las existencias disponibles actuales: puede
superarlas porque incluye unidades que ya salieron. La regla es que una nueva
reserva nunca supere lo disponible y una entrega real nunca supere su reserva.
No se presentan reservas como entregas efectivas en el historial de trabajadores.

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

En Inventario: Existencias = físico − reservas pendientes; Entregados = entregas
reales vigentes + reservas pendientes. Se calculan con subconsultas SQL para evitar
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

## Verificación realizada

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

Con el código actualizado, PostgreSQL iniciado y tu `.env` habitual:

```bash
cd ~/Proyectos/gestor-epp
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py test projects catalog inventory
.venv/bin/python manage.py runserver
```

Abrir http://127.0.0.1:8000/ y recargar con Ctrl+Shift+R.

1. Crear un elemento de prueba en Inventario con cantidad inicial 2 (vacía = 0).
2. Crear/abrir un proyecto; Inventario → Solicitar elemento → pedir 5.
   Debe asignar 2 y mostrar necesidad de compra 3; Inventario general muestra 0/2.
3. Confirmar entrega de 1 a un trabajador: Inventario sigue 0/2; Entregas muestra
   al trabajador y su cantidad real. Intentar confirmar otras 2 debe rechazarse
   bajo Cantidad y conservar los datos/saldos.
4. Reducir el pendiente de 4 a 2 con motivo: conserva la reserva de 1 y deja
   necesidad de compra 1. La entrega real anterior permanece vigente.
5. Registrar entrada de 3 desde Inventario: muestra 3/2 y no cambia automáticamente
   la solicitud. «Reservar disponibles» asigna el 1 faltante: queda 2/3.
6. Corregir la entrega de 1, o anularla con motivo: las unidades devueltas quedan
   reservadas en su solicitud. Repetir no reintegra dos veces. Revisar historial.
7. Cancelar todo el pendiente con motivo: libera las reservas; conserva entregas
   reales que todavía estén vigentes. Probar con otro proyecto y el mismo elemento.
8. Probar la ×, búsqueda, ordenación y páginas; verificar tarjetas y menú móvil.

No se incorporan compras/finanzas, intermediarios, devoluciones ni reposiciones.
No se cambian datos de prueba por datos reales ni se borran registros anteriores.
