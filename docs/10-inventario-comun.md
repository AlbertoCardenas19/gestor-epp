# Inventario común: consulta, entradas y trazabilidad

Documento del primer incremento S16/S19/S21, migración 0003. Su verificación
corresponde a esa entrega. **El flujo vigente está en la [guía 11](11-inventario-y-solicitudes.md)**:
unificación con catálogo, solicitudes/reservas, necesidad de compra y migración 0004.
Las menciones de pendientes y recorridos anteriores de este documento son históricos.

## Qué cambia

- Acceso «Inventario común» desde Inicio, sidebar y detalle de un elemento.
- Lista de elementos con tipo y existencias comunes, usando DataTables serverSide.
- Historial conjunto de aperturas, entradas y entregas anteriores, más las nuevas
  entradas de empresa. Conserva fecha, origen, estado y acceso al registro completo.
- Una entrada de empresa pide cantidad entera positiva, fecha y observación opcional.
  No exige apertura en un proyecto. La prevencionista sigue siendo la usuaria inicial.
- Corregir una entrada común exige motivo y conserva original y reemplazo vinculados.
  Se pueden corregir cantidad, fecha y observación, como en las entradas existentes.
- El elemento sin movimientos muestra cero; consultar no crea posiciones ni conteos
  ficticios. Todavía no se añadió cantidad inicial al formulario de catálogo.

Las entradas comunes no se asignan automáticamente a proyectos. El siguiente
incremento implementará las solicitudes y reservas que permitirán entregar desde
este stock. Por ahora se conserva el flujo anterior de entregas por proyecto.
No se presentan reservas, disponibilidad para solicitudes ni entregas comunes
como si ya funcionaran.

## Conservación de saldos e historial

Las existencias comunes suman el libro de movimientos vigente del elemento en
todos los proyectos y en la empresa: aperturas + entradas − entregas vigentes.
Los originales sustituidos y registros anulados no afectan al saldo. El historial
los conserva, con sus datos, motivos y enlaces.

Ejemplo: 10 cascos en Norte, 7 en Sur y una entrega vigente de 3 de Norte equivalen
a 14 existencias comunes. Registrar una entrada de empresa de 5 deja 19. Corregir
esa entrada a 3 deja 17. Anular la entrega anterior devuelve las existencias a 20.
Todo esto se comprobó en navegador.

Se realiza un **traslado lógico** a una consulta común, sin copiar cantidades a un
segundo saldo ni duplicar los registros antiguos. Así, corregir o anular un registro
anterior actualiza también el total común una sola vez. Se conservan posiciones,
proyectos, fechas, destinatarios, IDs y enlaces anteriores. No se inventan solicitudes
para las entregas históricas.

## Modelo, migración y escrituras

La migración `inventory/0003_alter_stockposition_project_and_more.py` permite que
`StockPosition.project` sea nulo para movimientos de empresa y añade una restricción
PostgreSQL que permite una sola posición común por elemento. Mantiene la unicidad
existente por proyecto–elemento y no actualiza ni borra movimientos históricos.
No requiere un RunPython ni sumar saldos en un campo almacenado.

Las posiciones anteriores siguen representando su historial por proyecto.
`StockPosition.common_balance(item_id)` y `common_items()` consultan el libro
completo para el total común. Una posición de empresa calcula ese mismo total;
las posiciones anteriores conservan su consulta individual para el flujo legado.

`receive_common_stock()` bloquea el elemento y su posición común dentro de una
transacción. La clave de envío existente evita duplicar una entrada por reintento;
una misma clave con datos diferentes se rechaza. Se reutiliza el servicio de
corrección y su transacción para las entradas de empresa. El original no cambia
salvo sus marcas de sustitución y motivo. Un fallo revierte la operación completa.

Las rutas comunes de corrección solo aceptan registros de empresa. Los registros
anteriores conservan sus rutas y reglas actuales de corrección/anulación hasta
la siguiente etapa de solicitudes. La confirmación S21 define cómo continuar su
adaptación: ajustar stock común sin crear ni reservar solicitudes ficticias.

## Interfaz e integración

Nuevas rutas en el namespace `stock`:

- `/inventario/`: consulta común; `/inventario/datos/`: datos de la tabla.
- `/inventario/elementos/<id>/`: historial común y su endpoint `datos/`.
- `entrada/`: registrar una entrada.
- `registros/<id>/`: detalle y enlaces de trazabilidad.
- `registros/<id>/corregir/`: corrección de una entrada común.

Se reutilizan el adaptador `projects/datatables.py`, la configuración compartida
y los componentes CoreUI. Acciones no se busca ni ordena. El historial mantiene
Fecha primero; cantidades con signo y fechas se ordenan por expresiones SQL de
tipo numérico/fecha. Los menús mantienen teclado y no se recortan en móvil.
No se añaden bibliotecas ni se duplica Bootstrap.

## Verificación

- 138 pruebas aprobadas en PostgreSQL: 125 previas y 13 nuevas.
- Migración desde 0002 preservando todos los valores anteriores y el total conjunto.
- Cero sin movimientos; total de dos proyectos; corrección y anulación anteriores
  contadas una vez; entradas comunes independientes por elemento; formularios,
  motivo, original/reemplazo, reintentos, CSRF, alcance de rutas y rollback.
- Dos entradas simultáneas conservan ambas cantidades y una sola posición común;
  dos solicitudes simultáneas con la misma clave solo crean un registro.
- 4 pruebas de navegador aprobadas sobre una base PostgreSQL temporal: las tres
  de componentes anteriores y el flujo común de entrada, corrección, trazabilidad
  y anulación de una entrega anterior. Se comprobó el ejemplo de saldos 14/19/17/20.
- La migración 0003 se aplicó también en la base local del entorno; se compararon
  huellas SHA-256 de todos los valores de posiciones y movimientos antes/después:
  registros y cantidades anteriores idénticos.
- Nueva revisión a 320/390/1440 píxeles, búsqueda, menús con hit-test sin recorte,
  columnas alineadas tras la transición del sidebar y sin errores de consola.

## Probar en Ubuntu cuando estos cambios estén en tu copia

Con PostgreSQL iniciado y el `.env` habitual:

```bash
cd ~/Proyectos/gestor-epp
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` y recargar con Ctrl+Shift+R. Desde Inventario común,
consultar un elemento, registrar una entrada de 5 y corregirla a 3 con motivo.
Comprobar ambas versiones en el historial y que el saldo solo incluya la vigente.
Si el elemento tenía 14, debe pasar a 19 y después 17.

No hay nuevas dependencias. La migración 0003 sí debe aplicarse antes de usar las
entradas comunes. Se mantienen pendientes solicitudes/reservas, entregas parciales
vinculadas, cancelación de lo pendiente y el nuevo flujo de corrección entre
solicitudes. No se ha hecho commit ni push en este incremento.
