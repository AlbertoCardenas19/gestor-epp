# Desarrollo local — proyectos, catálogo e inventario

## Alcance implementado

Crear, listar y consultar proyectos con nombre obligatorio y descripción opcional.
También crear, listar y consultar elementos del catálogo común, con nombre y
tipo obligatorios (EPP o señalética), y descripción opcional. Este catálogo no
está asociado a un proyecto y no guarda cantidades ni movimientos de inventario.
El inventario por proyecto permite registrar una apertura por elemento, nuevas
entradas y correcciones con anulación y reemplazo vinculado. La consulta distingue
«Sin registro inicial» de una apertura en cero y muestra el historial completo.
También permite entregas directas a trabajadores identificados por nombre completo,
que descuentan unidades del proyecto sin permitir cantidades superiores al saldo.
Avance de RF-01, RF-03, RF-04, RF-05 y del flujo directo de RF-08/RF-09;
no constituye el MVP completo. Los campos usan texto
sin una restricción de longitud o unicidad de negocio aún no acordada.
La interfaz está en español y usa CoreUI 5.4.3, basado en Bootstrap 5, servido
localmente para no depender de una CDN al abrir las pantallas.

Estos flujos son de desarrollo local. Todavía no se han definido cuentas,
permisos ni despliegue público (P-03 y P-12). El servidor se inicia en loopback.

## Dependencias

Para probar en un PC, sigue primero el [README principal](../README.md), que
incluye instalación con PostgreSQL local y comandos de Windows, Linux y macOS.
Las rutas `/workspace` de esta guía corresponden únicamente al entorno de nube.

Python 3.12, PostgreSQL 17 y los paquetes fijados en `requirements.txt`.
El `.venv` que estaba versionado se retiró del seguimiento de Git sin borrarlo
del disco y está excluido mediante `.gitignore`. No debe usarse: contiene rutas
de otra máquina. Crea un entorno propio fuera del checkout, por ejemplo:

```bash
cd /workspace/gestor-epp
python3 -m venv /workspace/.venvs/gestor-epp
/workspace/.venvs/gestor-epp/bin/python -m pip install -r requirements.txt
```

El archivo fija Django, Psycopg y python-dotenv, junto con sus dependencias transitivas
para Python 3.12. `tzdata` está fijado mediante un marcador exclusivo de Windows.
El extra `binary` de Psycopg fija también su paquete binario
a la misma versión. No se exporta el entorno global de la máquina ni se incluyen
paquetes de navegador o herramientas ajenas al funcionamiento de la aplicación.
CoreUI está incluido localmente con versión, integridad y licencia en
`projects/static/vendor/coreui/README.md`; no requiere instalar paquetes npm.

## Variables y credenciales

`.env.example` contiene únicamente ejemplos para conectar con un PostgreSQL
existente. `PGDATABASE` y `PGUSER` identifican la base y la cuenta; `PGHOST` y
`PGPORT` indican su dirección; `PGPASSWORD` aporta la contraseña cuando se requiere.
`config/settings.py` carga `.env` automáticamente mediante python-dotenv. Las
variables existentes en el proceso tienen prioridad. Prepara tu archivo desde
la raíz del repositorio:

```bash
# Copiar solo si aún no tienes .env; no sobrescribir una configuración existente.
test -e .env || cp .env.example .env
chmod 600 .env
# Edita .env localmente con los valores de tu instancia.
```

El archivo `.env` usa el formato dotenv (clave=valor, con comillas opcionales), y queda
ignorado junto con sus variantes; únicamente `.env.example` se comparte.
Los valores de ejemplo no crean usuarios ni bases de datos. No incluyas claves
reales en el ejemplo ni en Git. Para la base aislada de `dev-db.sh`, usa el socket,
puerto y usuario documentados abajo, con contraseña vacía. Esa configuración
local no admite conexiones TCP y no necesita una contraseña compartida.

## Base local

Con PostgreSQL instalado, `scripts/dev-db.sh` inicializa una base aislada,
sin acceso TCP y accesible únicamente por un socket dentro de `.local/`.
No necesita contraseñas para ese socket local, cuyo directorio es privado.
La cuenta local tiene permisos para crear la base temporal de pruebas.
No reutilizar esta configuración como configuración de producción.

```bash
cd /workspace/gestor-epp
# Solo si los binarios no están en /usr/lib/postgresql/17/bin:
export PG_BIN=/workspace/.cloud/postgresql/usr/lib/postgresql/17/bin
bash scripts/dev-db.sh start
export PGHOST="$PWD/.local/pgsocket"
export PGPORT=55432 PGUSER=gestor_epp PGDATABASE=gestor_epp
export DJANGO_SETTINGS_MODULE=config.settings PYTHONDONTWRITEBYTECODE=1
/workspace/.venvs/gestor-epp/bin/python manage.py migrate --noinput
/workspace/.venvs/gestor-epp/bin/python manage.py runserver 127.0.0.1:8001 --noreload
```

Para una base PostgreSQL existente, configura `PGHOST`, `PGPORT`, `PGUSER`,
`PGDATABASE` y, si corresponde, `PGPASSWORD` mediante tu entorno seguro.
No ejecutes `dev-db.sh` para administrar esa base externa.
No hay retorno automático a SQLite.

## Comprobaciones

Con las mismas variables de conexión:

```bash
/workspace/.venvs/gestor-epp/bin/python manage.py check
/workspace/.venvs/gestor-epp/bin/python manage.py makemigrations --check --dry-run
/workspace/.venvs/gestor-epp/bin/python manage.py test projects catalog inventory
```

Las pruebas usan una base PostgreSQL temporal, separada de los datos locales.
Comprueban creación, consulta, descripción opcional, nombre vacío o con espacios,
conservación del formulario inválido, escape de HTML, CSRF y proyecto inexistente.
Para el catálogo también verifican ambos tipos permitidos, rechazo del tipo vacío
o desconocido (incluida la restricción PostgreSQL), consulta común al navegar
entre proyectos, elemento inexistente y navegación de la sección activa.

Prueba manual: abrir la lista, crear un proyecto, consultar el detalle, volver a
la lista y recargar. Repetir en tamaño móvil; probar también guardar sin nombre.
Para el catálogo, abrir «Catálogo» desde la navegación principal, crear un EPP y
una señalética, consultar sus detalles y recargar. Comprobar nombre y tipo
obligatorios, descripción opcional y conservación de datos al corregir errores.

Para detener la base local: `bash scripts/dev-db.sh stop` con el mismo `PG_BIN`.
Los procesos deben reiniciarse en cada nueva sesión; los datos quedan en `.local/`.

## Validación realizada el 12 de noviembre de 2026

- `check` sin errores y `makemigrations --check --dry-run` sin cambios pendientes.
- Migraciones aplicadas y 10 pruebas aprobadas sobre PostgreSQL 17.
- Chromium: creación, validación, consulta y recarga a 1366 × 900 y 390 × 844,
  sin desbordamiento horizontal ni errores de JavaScript.
- Persistencia comprobada tras detener e iniciar PostgreSQL. Se retiraron los
  dos registros creados exclusivamente por la comprobación de navegador.
- Instalación repetida sin migraciones pendientes; formulario, lista y CSS local
  responden HTTP 200. Estas comprobaciones no certifican despliegue público,
  permisos ni funcionalidades que todavía no se han implementado.

## Preparación del repositorio antes del catálogo

- Se retiraron 5.701 archivos de `.venv/` del índice de Git mediante
  `git rm --cached`, conservando el entorno en disco. La eliminación del índice
  forma parte de la entrega del código; no elimina archivos de commits anteriores.
- Se mantiene la exclusión de `.venv/` y se excluyen `.env` y sus variantes,
  con la excepción explícita de `.env.example`.
- Se revisaron las dependencias declaradas contra sus metadatos: corresponden
  al proyecto, con versiones fijadas, sin incorporar herramientas de la máquina.
- La configuración PostgreSQL lee `PGPASSWORD` del entorno con respaldo vacío;
  no hay contraseña PostgreSQL literal en esa configuración ni archivos `.env`
  o `.pgpass` en el índice. El ejemplo contiene únicamente valores ficticios.
- Después de los ajustes: `pip check`, comprobaciones de Django, consistencia
  de migraciones y las 10 pruebas sobre PostgreSQL pasaron. Chromium verificó
  lista, formulario, validación con conservación de descripción y cancelación
  a 1366 × 900 y 390 × 844, sin desbordamiento horizontal. También se comprobó
  la carga de las variables de ejemplo sin conectar con la base ficticia.
- No se hicieron commits ni push. Se conservaron los cambios previos del flujo
  de proyectos. En esa revisión el catálogo aún estaba pendiente; posteriormente
  se acordaron sus campos y alcance en S8 y se implementó el flujo descrito arriba.

## Catálogo RF-05 — validación del 12 de noviembre de 2026

- Nueva tabla `catalog_item`, común a todos los proyectos, con nombre, tipo y
  descripción. La elección de tipo se valida en el formulario y en PostgreSQL.
  No se añadió una relación con proyectos, stock ni reglas de inventario.
- Migración `catalog/0001_initial.py` aplicada. Las comprobaciones de Django y
  de consistencia entre modelos y migraciones pasan.
- 23 pruebas aprobadas sobre PostgreSQL: 10 de proyectos y 13 de catálogo.
- Chromium verificó nombre y tipo obligatorios, conservación de campos al
  corregir errores, alta de EPP y señalética, detalle, recarga, lista y navegación
  a proyectos en escritorio (1366 × 900) y móvil (390 × 844).
- Se comprobaron pantallas sin desbordamiento horizontal y sin errores de
  JavaScript. Los dos elementos creados por la prueba se retiraron por sus
  identificadores y nombres únicos, conservando los demás datos.
- No se añadieron dependencias, commits ni push. Se mantienen pendientes los
  atributos adicionales, edición, eliminación, acceso y reglas de inventario.

## Inventario por proyecto — RF-04

Desde el detalle de un proyecto, la pestaña «Inventario» muestra los elementos del
catálogo común. Cada combinación proyecto–elemento tiene sus propios registros.
La lista distingue «Sin registro inicial» de una apertura con cantidad cero.

Flujo implementado conforme a S9:

1. Registrar la apertura con cantidad entera de cero o más y fecha del conteo.
2. Registrar nuevas entradas con cantidad entera mayor que cero y fecha de recepción.
3. Consultar el saldo registrado y el historial del elemento dentro del proyecto.
4. Corregir cantidad, fecha u observación mediante un reemplazo con motivo obligatorio.
   La operación, proyecto y elemento se mantienen en esta versión. El original
   conserva sus datos y queda anulado; ambos registros se enlazan en el historial.
5. Conforme a S10, registrar entregas directas con nombre completo del trabajador,
   cantidad positiva, fecha de entrega y observación opcional. Se requiere apertura
   previa y saldo suficiente en ese proyecto. No se crean cuentas para trabajadores.

La persona que registra se guarda como «Prevencionista», según la única usuaria
actual. Es una identificación funcional, no una cuenta autenticada. Se conserva
la fecha y hora de carga además de la fecha del hecho. La autenticación y
la identificación personal de futuras cuentas permanecen pendientes en P-03.

El saldo es la suma de la apertura y entradas vigentes menos las entregas directas,
calculado desde el historial. No se guarda una cantidad en el catálogo ni se actualiza un saldo
independiente. Las correcciones no admiten anular sin crear el reemplazo: ambas
acciones se guardan en una única transacción, conservando la apertura lógica.
El reemplazo vigente puede corregirse nuevamente y conserva la cadena anterior.

La unicidad de proyecto–elemento y de apertura vigente se protege en PostgreSQL.
Los servicios de `inventory/services.py` serializan las escrituras por posición
para evitar dobles aperturas o correcciones simultáneas sobre un mismo registro.
Un identificador oculto del formulario evita duplicar una operación al reenviar
la misma solicitud. Las nuevas escrituras de inventario deben usar estos servicios.

Ejemplo comprobado: el mismo casco tiene apertura 10 y entrada 5 en Norte
(saldo 15), y apertura 4 y entrada 2 en Sur (saldo 6). Corregir la apertura de
Norte a 8 cambia su saldo a 13; corregir su entrada de 5 a 2 lo deja en 10.
Sur permanece en 6 y los registros anulados siguen visibles.

Límites de esta versión:

- Se implementan únicamente entregas directas; otras salidas, intermediarios,
  devoluciones, reposiciones, transferencias, stock mínimo, compras, ajustes
  automáticos y nuevos permisos siguen pendientes.
- El saldo registrado no descuenta entregas efectuadas fuera de la aplicación.
- La fecha debe ser válida; reglas adicionales sobre retroactividad o fechas
  futuras siguen pendientes. Las horas de registro muestran su zona horaria.
- Las correcciones de aperturas y entradas mantienen proyecto, elemento y operación.
  En entregas, S12 permite corregir también proyecto, elemento y destinatario.
- La corrección de entregas está habilitada; S13 habilita también la anulación
  sin reemplazo de una entrega vigente equivocada, con restitución única.

Validación: migración `inventory/0001_initial.py` aplicada y 50 pruebas aprobadas
en PostgreSQL (23 previas y 27 de inventario). Incluyen concurrencia, reenvíos,
validación de cantidades y fechas, separación de proyectos, conservación del
historial, motivo obligatorio y reversión completa ante una corrección inválida.
En Chromium se recorrieron apertura, entrada, corrección de ambas operaciones,
consulta y recarga para dos proyectos con un elemento común; las pantallas se
comprobaron sin desbordamiento a 320, 390 y 1366 píxeles. No se añaden dependencias.

## Presentación visual y prueba en PC — 12 de noviembre de 2026

La primera presentación (reemplazada por S14, descrita al final) aplicó navegación lateral
en escritorio, navegación superior en móvil, paleta verde, tarjetas, formularios,
ilustración local y distinción visual entre registros vigentes y anulados.
CoreUI/Bootstrap continúa sirviéndose desde los archivos estáticos del proyecto.
No se agregaron pantallas de funciones aún pendientes ni cifras simuladas.

El README principal explica cómo clonar y ejecutar la app con PostgreSQL local.
Se incorporó python-dotenv para cargar `.env` automáticamente sin reemplazar
variables del proceso, y se fijó tzdata para Windows. La clave Django de desarrollo
es un valor ficticio y puede sustituirse mediante `DJANGO_SECRET_KEY`.

Comprobaciones de esta entrega:

- 50 pruebas aprobadas sobre PostgreSQL, sin cambios de modelos ni migraciones
  adicionales por el trabajo visual; `check` y consistencia de migraciones pasan.
- Chromium revisó siete pantallas, validación y navegación a 320, 390, 768 y
  1440 píxeles, sin desbordamiento horizontal, errores JavaScript ni recursos fallidos.
- Se extrajo una copia limpia del árbol preparado para Git en un directorio
  temporal de esta máquina Linux. Con una base PostgreSQL nueva y configuración
  leída solo desde `.env`, se ejecutaron `check`, las migraciones y un recorrido
  de proyectos, catálogo, apertura, entrada y corrección con saldo esperado 13.
- La base temporal y los datos de las comprobaciones visuales se retiraron.
  Las instrucciones para Windows y macOS no se han ejecutado en esos sistemas.

## Entregas directas — RF-08 y RF-09, primera versión

Acuerdos S10 implementados: desde el historial del elemento de un proyecto,
«Registrar entrega» pide nombre completo del trabajador, cantidad entera positiva,
fecha de entrega y observación opcional. La prevencionista carga la operación y
se conserva la fecha de registro además de la fecha del hecho. No se piden RUT,
cuentas, firmas ni datos del intermediario.

Cada entrega conserva su destinatario y descuenta unidades únicamente de ese
proyecto. El nombre se guarda en el registro, sin crear un maestro de personas
ni asumir que dos nombres iguales representan a la misma persona. El saldo de
la lista, el detalle y las validaciones usan el mismo cálculo con signo.

La entrega se valida y guarda bajo un bloqueo transaccional de la posición.
Si supera el saldo disponible, se revierte por completo y se conservan los datos
del formulario para corregirlos. El control de reenvíos incluye el destinatario,
evitando descontar otra vez la misma solicitud. La corrección de aperturas o
entradas también se revierte si deja un saldo negativo por entregas ya guardadas.

Se agregó la migración `inventory/0002_remove_stockrecord_inventory_valid_operation_quantity_and_more.py`:
añade el destinatario, la operación de entrega y sus restricciones. Los registros
anteriores mantienen sus datos y llevan nombre de trabajador vacío. En una copia
del PC actualizada, ejecutar `python manage.py migrate` antes de iniciar la app.

Comprobaciones realizadas:

- 69 pruebas aprobadas sobre PostgreSQL: las 50 anteriores y 19 nuevas. Incluyen
  nombre obligatorio, cantidades y fechas válidas, saldo insuficiente, descuento
  hasta cero, separación de proyectos, CSRF, escape de nombres, reenvíos y concurrencia.
- Chromium recorrió el formulario y el historial en escritorio y móvil. En un
  proyecto con 10 unidades se entregaron 3 a Ana Pérez y 2 a Luis Soto: saldo 5.
  Otro proyecto con el mismo elemento conservó su saldo 4. Se comprobó rechazo
  por cantidad excesiva, conservación de campos y recarga del historial.
- Formulario, historial e inventario sin desbordamiento a 320 píxeles. Los datos
  exclusivos de la prueba de navegador se retiraron.

Al cerrar el primer avance de entregas directas quedaron pendientes intermediarios,
corrección, anulación, devoluciones y reposiciones. Posteriormente S12 aprobó la
corrección de entregas, implementada en la primera iteración descrita más abajo.
Las demás funcionalidades no se presentan como ya implementadas.

## Siguientes dos iteraciones — S11

El alcance ratificado es entrega directa al trabajador, conservando los campos,
el descuento y el control de saldo actuales. Se trabaja primero en corrección
y después en anulación de registros equivocados, acordando las reglas antes de
cada implementación. Las devoluciones físicas quedan fuera. Cada iteración cierra
con sus comprobaciones y un commit propio, sin push. Los acuerdos y el diagnóstico
se detallan en [07-iteraciones-entregas.md](07-iteraciones-entregas.md).

## Iteración 1 completada — corrección de entregas, S12

El formulario permite corregir destinatario, proyecto, elemento del catálogo,
cantidad, fecha y observación, con motivo obligatorio. El original conserva todos
esos datos y su fecha de captura; queda sustituido y enlazado a un reemplazo con
su propia fecha de registro. Solo se puede corregir el registro vigente. Los
enlaces entre historiales funcionan aunque cambie proyecto o elemento.

En la misma posición se aplica el ajuste neto: saldo actual + cantidad anterior
− cantidad corregida. Entre posiciones se revierte el descuento anterior y se
aplica el nuevo. El destino debe tener apertura y saldo suficientes; no se generan
aperturas ni entradas automáticas. Es una rectificación del registro, no un traslado
de materiales. El servicio bloquea ambas posiciones en orden por identificador
y aplica todo en una transacción. Un fallo conserva registros y saldos anteriores.

Se reutilizan los campos de historial existentes: no hay migraciones ni paquetes
nuevos. Pasaron 91 pruebas en PostgreSQL, incluidas las anteriores, validaciones,
preservación del original, cadenas, enlaces, CSRF y correcciones cruzadas simultáneas.
Chromium comprobó los seis campos, rechazos por apertura o saldo insuficiente,
conservación de formulario, recarga y enlaces en escritorio y móvil, sin
desbordamiento a 320/390/1440 píxeles. Firefox se intentó ejecutar, pero no está
instalado (falta `/home/agent/.cache/ms-playwright/firefox-1538/firefox/firefox`).

Ejemplo de navegador: dos entregas de 5 y 2 dejan el saldo Norte en 13; Sur tiene
8. Corregir la primera a 3 en Sur deja Norte 18 y Sur 5. Corregir la segunda de
2 a 4, manteniéndola en Norte, deja Norte 16 y Sur 5. Se comprobó el recorrido de
ambos historiales y la conservación de nombres y datos originales. Los datos
exclusivos de la comprobación se retiraron al cerrar la iteración.

Al cerrar la primera iteración quedó pendiente la anulación sin reemplazo.
Posteriormente se aprobó en S13 y se implementó según el cierre siguiente.

## Iteración 2 completada — anulación de entregas, S13

Desde una entrega vigente, «Anular entrega» abre una confirmación con sus datos
y motivo obligatorio. El GET no modifica existencias. El POST bloquea la posición,
comprueba que no exista un reemplazo y conserva el registro con `voided_at` y
`void_reason`; el saldo deja de descontarlo. No se genera una entrada de stock,
un reemplazo ni un movimiento de devolución física.

La misma operación se aplica a un reemplazo vigente, restituyendo la cantidad
en su proyecto y elemento actuales. Un original sustituido se rechaza incluso
si después se anuló su reemplazo. El historial diferencia «Sustituido» de «Anulado»,
conserva los enlaces entre proyectos y muestra datos, motivo y fecha. Una entrega
anulada ya no ofrece corrección ni otra confirmación de anulación.

Repetir una solicitud válida devuelve «ya anulada» sin cambiar motivo, fecha ni
saldo. Las solicitudes simultáneas usan el mismo bloqueo que correcciones y
entregas. Todo se guarda en una transacción; si la escritura falla, se revierte
la marca de anulación y el saldo calculado permanece igual. La restitución está
implícita en excluir una sola vez el registro, sin un contador que pueda duplicarse.

Verificación: 109 pruebas aprobadas en PostgreSQL (91 anteriores y 18 nuevas).
Se cubrieron entrega vigente, reemplazo vigente en otra posición, original
sustituido rechazado, motivo, datos intactos, historial, CSRF, reenvíos, solicitudes
simultáneas y carreras con corrección o nueva entrega. Un fallo simulado después
de ejecutar la actualización SQL confirmó reversión completa del estado y saldo.
`check`, consistencia de migraciones y `migrate --check` pasan. No se requieren
migraciones ni dependencias nuevas.

Chromium recorrió corrección y anulación en escritorio y móvil: Norte/Casco pasó
de 13 a 18 al corregir una entrega hacia Sur/Guantes, que quedó en 5. Anular el
reemplazo restituyó Sur/Guantes a 8. Anular otra entrega directa de Norte restituyó
su saldo a 20. Los reenvíos mantuvieron 20/8 y conservaron el primer motivo.
Las pantallas no desbordaron a 320/390/1440 píxeles. Firefox se intentó ejecutar
nuevamente, pero sigue faltando su ejecutable. Los datos de navegador se retiraron.

El commit `ad800f5` de la primera iteración se conserva y esta segunda iteración
se cierra con otro commit, sin push. El recorrido manual de ambas está en
[07-iteraciones-entregas.md](07-iteraciones-entregas.md#recorrido-manual-para-ambas-iteraciones).


## Navegación y tablas — S14 (RF-01, RF-03, RF-04, RF-05, RF-08 y RF-09)

Presentación de S14 (la paleta fue sustituida por S15): negro, blanco y dorado,
conservando CoreUI/Bootstrap local.
La raíz `/` muestra Inicio con paneles a Proyectos y Catálogo. El sidebar tiene
un botón debajo de las opciones para contraerlo a iconos; conserva la preferencia
en el navegador y permite usar teclado. En móvil comienza contraído. Se retiraron
banner, etiquetas decorativas sobre títulos, subtítulo del header, nota del sidebar
y footer según lo solicitado.

El proyecto abre en Entregas: una fila por entrega vigente, con elemento,
trabajador, cantidad, fecha, estado y enlaces a historial, corrección y anulación.
El filtro permite consultar vigentes, anuladas, sustituidas o todas. Las acciones
que cambian registros solo aparecen para vigentes; las validaciones del servidor
continúan aplicándose. La pestaña Inventario conserva apertura, entrada, entrega
y consulta de saldos. La descripción del proyecto continúa guardándose y se ve
en la lista de proyectos; ya no ocupa el detalle.

Catálogo usa una tabla de nombre, tipo, descripción y acceso al detalle. Ambas
tablas buscan, ordenan y paginan en el servidor, con 10, 25 o 50 filas por página.
La búsqueda de entregas consulta elemento, trabajador y observación; la del
catálogo consulta nombre, tipo visible y descripción. Se conservan filtros al
cambiar de página. En móvil las tablas se desplazan horizontalmente dentro de
su contenedor, sin ensanchar la página. No se agregaron paquetes ni migraciones.

Verificación: 114 pruebas aprobadas en PostgreSQL, incluidas las 109 anteriores
adaptadas a la nueva navegación y cinco nuevas sobre las tablas. Se comprobaron
separación entre proyectos, estados, enlaces de acciones, búsqueda, ordenación,
paginación, parámetros inválidos y conservación de saldos al consultar.
Chromium verificó inicio, catálogo, entregas, acceso a corrección y anulación,
pestaña Inventario e historial, saldo, menú con teclado y preferencia tras recargar,
y ausencia de desborde de página a 320, 390 y 1440 píxeles. Firefox se intentó
iniciar, pero sigue sin estar disponible su ejecutable en el entorno.


## Ajustes de interfaz — S15 (RF-03, RF-05, RF-08 y RF-09)

Se aplica la paleta de seis colores acordada en S15 a toda la interfaz. El sidebar
separa Inicio, Proyectos y Catálogo con divisores; el control para contraer/expandir
es una flecha, con nombre accesible y 48 píxeles de separación bajo la navegación.
Conserva teclado y preferencia del navegador. Los formularios y el contenedor de
contenido aprovechan el ancho disponible, sin el límite anterior de 48 rem del
formulario. Catálogo y Entregas tienen filas alternadas (`table-striped`).

La búsqueda filtra al escribir tras una pausa de 300 ms. Consulta el conjunto
completo en el servidor, actualiza tabla y paginación sin reemplazar el campo ni
perder el foco y vuelve a la primera página al cambiar filtros. Estado, orden y
filas también se aplican automáticamente. Se cancelan consultas anteriores y se
ignoran respuestas obsoletas. El resumen se anuncia de forma accesible. Si falla
la consulta, se informa que los resultados anteriores siguen visibles y se puede
reintentar con Aplicar. Sin JavaScript se conserva el formulario GET y su botón.

Verificación: 114 pruebas pasan en PostgreSQL. Chromium comprobó búsquedas en
ambas tablas, foco, estados, ordenación, filas, paginación y Atrás, respuesta
anterior demorada, fallo de red y reintento, funcionamiento sin JavaScript,
colores y franjas, flecha y teclado, ancho de formularios y ausencia de desborde
de página a 320, 390, 1440 y 1920 píxeles. El saldo de los datos exclusivos de
prueba se mantuvo intacto. Firefox se intentó iniciar y sigue faltando su
ejecutable. No hay paquetes ni migraciones nuevas.

## Próximo flujo por acordar e implementar — S16

El usuario confirmó stock real común de empresa, solicitudes por proyecto que
reservan existencias y descuento al realizar la entrega. Las solicitudes deben
limitarse a lo disponible; se admiten entregas parciales y reducción/cancelación
de lo pendiente con motivo e historial. Un elemento sin cantidad inicial empieza
en cero. Los datos actuales del PC son de prueba, sin autorización para borrarlos.
Este destino funcional reemplazará las aperturas por
proyecto, pero **el código actual sigue usando el inventario por proyecto**.
Las aclaraciones y pendientes están en [S16](05-fuentes.md#s16--revisión-del-flujo-stock-común-y-solicitudes-por-proyecto).
No se ha iniciado una conversión de datos ni se deben usar las solicitudes como
si ya existieran. El rediseño requiere conservar el historial y acordar el
tratamiento de registros anteriores antes de preparar migraciones.


## Tablas y validación por campo — S17 (RF-01, RF-03, RF-04, RF-05, RF-08 y RF-09)

Proyectos ahora tiene tabla con búsqueda automática y paginación. Proyectos,
Catálogo y Entregas ordenan desde los encabezados, alternando ascendente y
descendente y mostrando la dirección; se retira el selector «Ordenar por».
Se conservan consulta, estado y tamaño de página, reiniciando la página al ordenar.
Acciones contiene un select por fila: abre detalles, historial o los formularios
existentes de corrección/anulación; seleccionar una acción no ejecuta escrituras.
Las acciones de modificar solo se ofrecen para entregas vigentes. Sin JavaScript
se conservan enlaces de ordenación, consulta y acciones equivalentes.

Fecha es la primera columna de Entregas. Las franjas usan blanco y gris azulado
`#E2E8F0`, distintos del fondo general `#F1F5F9`. El sidebar anima ancho y margen
del contenido durante 240 ms y respeta la preferencia de movimiento reducido.
Las opciones conservan 48 píxeles de alto, evitando que la flecha suba o baje.

Se retiraron los avisos de éxito y «Registrado por: Prevencionista» de la interfaz;
los datos históricos se conservan. Los errores aparecen bajo su campo, con texto
rojo y asociación accesible. El servicio identifica los rechazos por saldo en
`quantity`, también al corregir; los demás errores generales se muestran como
texto rojo sin tarjeta de alerta. Se conserva la transacción, la validación y
la restitución única existentes: no cambian las reglas de inventario.

Verificación: 119 pruebas pasan en PostgreSQL (114 anteriores y cinco nuevas).
Se comprueban búsqueda, páginas y ordenación de proyectos, dirección de los
encabezados, ordenación de estados y trabajadores, descripción descendente,
ausencia de aviso de creación y error de saldo vinculado a cantidad sin escritura
parcial. Chromium verificó las tres tablas, encabezados en ambos sentidos,
selectores de acciones, fecha primero, contraste de franjas, transición y altura
estable de la flecha, movimiento reducido, errores bajo cantidad al entregar y
corregir, éxito sin avisos ni responsable visible, ausencia de desborde de página
a 320/390/1440 píxeles y enlaces equivalentes sin JavaScript. Firefox se intentó
iniciar; sigue faltando su ejecutable. Los datos exclusivos de la comprobación
se retiraron. No hay dependencias ni migraciones nuevas; S16 sigue sin implementar.


## Menú Acciones y tarjetas — S18 (RF-01, RF-03, RF-05, RF-08 y RF-09)

Acciones es un botón que abre enlaces en un menú como la referencia del usuario,
no un select. El menú se muestra sobre la tabla sin recortarse por su contenedor,
se adapta al espacio disponible y permite clic exterior, Escape y teclado.
Conserva solo las acciones implementadas y las confirmaciones previas a escrituras.
Utiliza Popover API nativa; en navegadores compatibles también funciona sin JS.

Se elimina el mensaje duplicado de resultados que aparecía arriba al ordenar;
se conserva el resumen habitual de la paginación inferior y los errores de red.
Se quitan las etiquetas de tipo de los títulos del detalle de catálogo e historial
y de las tarjetas de inventario. El tipo permanece como dato del catálogo y en
la tabla. Proyectos vuelve a tarjetas, manteniendo búsqueda automática, páginas
y enlaces de consulta.

Verificación: 119 pruebas aprobadas en PostgreSQL, adaptando las comprobaciones
de tarjetas y menú. Chromium comprobó menú sin recorte, teclado, Escape, clic
exterior, enlaces y estados, ausencia del mensaje duplicado al ordenar, tarjetas
con búsqueda y páginas, etiquetas retiradas y saldo sin cambios. Se revisaron
320/390/1440 píxeles y navegación nativa sin JavaScript. Firefox se intentó
iniciar y sigue faltando su ejecutable. Se retiraron solo los datos creados por
la prueba. No hay dependencias ni migraciones nuevas en este ajuste.

El siguiente desarrollo corresponde a S16/S19; su diseño y verificación prevista
están en [08-stock-comun-y-solicitudes.md](08-stock-comun-y-solicitudes.md).


## Integración oficial de DataTables y CoreUI — S20

Se completó sobre el trabajo parcial conservado, sin reiniciar la implementación.
Catálogo y Entregas usan DataTables 2.3.5, integración Bootstrap 5 2.3.5 y jQuery
3.7.1 locales, con `serverSide` en PostgreSQL y configuración compartida. CoreUI
5.4.3 conserva su CSS y ahora usa su bundle oficial con Popper para Sidebar y
Dropdown, sin cargar Bootstrap separado. Se mantienen paleta y tarjetas de Proyectos.

Búsqueda y ordenación preceden a la paginación del queryset completo. Se mantienen
alcance por proyecto, estados y acciones; Acciones no se busca ni ordena. Los
archivos propios sustituidos se retiraron y la búsqueda de tarjetas queda separada.
Se añadieron convenciones permanentes actuales a AGENTS.md, sin atribuirlas a
acuerdos históricos. No se modificaron modelos, servicios, datos ni migraciones de
inventario; el futuro stock común de S16/S19 continúa fuera de esta integración.

Verificación final: 125 pruebas Django en PostgreSQL y 3 pruebas automatizadas de
navegador con PostgreSQL temporal aprobadas. Se comprobaron tablas vacías, una fila,
varias páginas, búsqueda fuera de la primera página, fechas/cantidades, filtros,
acciones tras redibujar, ausencia de controles duplicados, teclado, sidebar y
menús sin recorte a 320/390/1440 píxeles, tarjetas, corrección/anulación y saldos.
No hubo errores de consola. Se verificaron contraste de encabezados/franjas e
integridad de recursos locales; pasan comprobaciones Django, migraciones y diff.
Firefox se intentó ejecutar; sigue faltando el binario. Sin commit ni push.

Versiones, reemplazos, configuración reutilizable, pruebas reproducibles y pasos
para PC están en [09-componentes-y-datatables.md](09-componentes-y-datatables.md).
El estado de continuidad está en [09-continuidad-ui.md](09-continuidad-ui.md).


## Primer incremento de inventario común — S16/S19/S21, RF-04/RF-05

Se implementan consulta, historial, entradas de empresa y corrección de esas
entradas. Se agregan sin duplicar los saldos de todos los movimientos anteriores.
La migración 0003 permite posiciones de empresa sin proyecto y garantiza una por
elemento, sin modificar los registros históricos. Durante la transición se
conservan el inventario y las entregas anteriores por proyecto.

Verificación: 138 pruebas PostgreSQL aprobadas y 4 pruebas de navegador en base
temporal. Incluyen conservación mediante migración desde 0002, saldos, rollback,
CSRF, formularios, correcciones, reintentos y concurrencia de entradas comunes.
Chromium comprobó el flujo 14 → 19 → 17 → 20 y menús/tablas a 320/390/1440 píxeles.
No hay bibliotecas nuevas. Solicitudes/reservas y sus entregas siguen pendientes.
Guía de implementación y pasos Ubuntu: [10-inventario-comun.md](10-inventario-comun.md).
