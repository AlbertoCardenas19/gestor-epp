# Sistema visual de gestor-epp basado en Punto Aparte

Fecha: 27 de noviembre de 2026. Versión 3.

## Decisiones vigentes

UI-06 implementó el espaciado de DataTables, los controles de búsqueda, el encabezado claro, la tarjeta Facturas y el área de acciones de Inicio, y retiró los filtros adicionales visibles de las tablas. UI-07 sustituyó Calibri por la familia de Punto Aparte y restauró la identidad original de Gestor EPP en el sidebar. El resto del plan de adopción queda pendiente. Las decisiones siguientes reemplazan cualquier indicación distinta en el análisis histórico de este documento:

- El buscador oficial de DataTables permanece **dentro** de la tarjeta, en la fila superior junto a «Mostrar X filas». Tiene etiqueta visible «Buscar», placeholder con los criterios reales sin «Buscar por» ni puntos suspensivos y búsqueda automática. Proyectos y los selectores de elementos no cambian.
- La tabla tiene 1rem de separación entre controles superiores y tabla, y entre tabla y controles inferiores, ajustable en móvil. El encabezado usa el token compartido `#EAF4FB` con texto oscuro, incluso al ordenar. Las filas permanecen blancas con hover gris.
- Inicio incluye una tarjeta Facturas hacia el listado existente. Todas sus tarjetas usan título, descripción y área de acciones con borde superior y botón alineado abajo mediante flex.
- Se retiran temporalmente los filtros adicionales de las tablas: categoría de Inventario, proyecto del historial de movimientos y estado de Entregas. Buscar, tamaño de página, orden y paginación permanecen. Entregas muestra todos los estados con su identificación; el alcance de proyecto y elemento se mantiene. No se dejan filtros implícitos por URL o persistencia.
- La fuente global de texto y controles es `system-ui, -apple-system, "Segoe UI", sans-serif`. Esta decisión reemplaza Calibri; UI-07 no cambia tamaños, pesos ni espaciados del texto.
- El sidebar conserva la identidad original «E» y «Gestor EPP» por encima de los grupos. En escritorio el primer encabezado de grupo comienza a la altura del título principal mediante medidas compartidas del encabezado y contenido. En móvil la navegación conserva un espacio cómodo bajo la identidad, sin forzar esa alineación. La identidad queda oculta dentro de la franja contraída.


## Estado y alcance

Este documento reúne el análisis original de código, decisiones confirmadas y una especificación de adaptación. El análisis original no ejecutó las aplicaciones ni midió estilos computados; su evidencia visual directa fue la captura del sidebar aportada por el usuario. UI-06 y UI-07 implementan solo las decisiones vigentes enumeradas arriba y registran su verificación en `docs/ITERACIONES.md`. El resto del plan de adaptación queda pendiente. No se auditó formalmente contraste, lector de pantalla ni interacción táctil.

Fuentes fijadas para evitar cambios silenciosos:
- Punto Aparte, rama work, commit `9f359ac45a5caf38c2321b6e79b7ec989ff06cbc`.
- Gestor EPP, main, commit `f08a625c74c488f3be46eb0442c7c10c6017fb65`.
- Requisitos del usuario en esta conversación: prevalecen sobre detalles de la referencia.

El objetivo es adoptar el lenguaje visual de Punto Aparte sin copiar su negocio, sus roles, ventas, pantalla de cliente ni arquitectura de navegación. Se mantienen Django, PostgreSQL, CoreUI, DataTables y los flujos existentes de EPP.

## 1. Análisis de la referencia

### Identidad visual

Punto Aparte concentra sus colores en variables: azul institucional #17324d, texto #1b2d48, texto secundario #566b86, borde #d9e1eb y fondo #f1f4f8. El blanco se reserva para superficies. Los botones principales usan el azul del menú. El rojo #c93440 aparece como acento y en errores; no es el color predominante de las acciones ordinarias.

Su apariencia depende de la combinación de superficies claras, bordes suaves, espacios generosos y una jerarquía consistente. Copiar solo el color del sidebar no reproduce esa apariencia.

### Tipografía y densidad

La fuente general declarada es system-ui, -apple-system, Segoe UI, sans-serif, con interlineado 1.6. No es Calibri. Títulos con peso alto y espaciado de letras ligeramente reducido; ayudas y metadatos usan tamaños menores. Los botones generales no reducen expresamente la fuente a .82rem como ocurre en EPP.

Esto aporta una hipótesis concreta para la sensación de texto pequeño o tosco de EPP: la diferencia incluye tamaños, pesos e interlineado, además de la familia. No se puede identificar la fuente realmente renderizada en la captura solo a partir del CSS.

### Estructura y sidebar

La estructura de escritorio usa una columna de 16rem y contenido minmax(0,1fr), evitando que el contenido fuerce el ancho del conjunto. Contraído pasa a 4.5rem. El contenido tiene ancho completo, límite de 1760px y padding adaptable.

Los grupos usan .72rem, peso 800, mayúsculas y espaciado .08em. Los enlaces tienen padding .65rem .75rem y radio .7rem. Los separadores usan blanco al 22%. Activo: fondo #304b68 y marca izquierda #dce7f2; hover: #294e70.

El botón lateral tiene área 2.75rem y un círculo interior menor, posición fija a media altura y flecha que cambia al contraer. En escritorio el overflow del sidebar pasa a visible para no recortar el control. En móvil se usa offcanvas Bootstrap, diferente de la franja actual de EPP. No debe copiarse ese comportamiento automáticamente.

### Tarjetas e inicio

Tarjetas blancas, borde de 1px, radio 1.25rem, sin sombra general. Padding clamp(1.25rem,2vw,2rem). El inicio usa una, dos o tres columnas según ancho. Cada tarjeta tiene título, descripción y un área de acciones separada por línea. Flex permite alinear las acciones abajo pese a descripciones de distinta longitud.

### Botones

Altura mínima 2.75rem, radio .65rem, padding .6rem 1.1rem y peso 600. Primarios azules; secundarios blancos con borde; peligros rojos. Los estados hover, activo, foco y deshabilitado están definidos. El tamaño pequeño es una variante explícita, no el valor de todas las acciones.

### Formularios

El formulario de producto se centra y limita a ocho columnas en escritorio. Usa tarjeta, etiquetas sobre controles, ayuda debajo, errores por campo y acciones Guardar/Cancelar separadas por línea superior. Los controles tienen altura mínima 2.75rem y radio .65rem. Hay variantes específicas para ofertas y acceso que no deben extenderse al resto de la aplicación.

### Tablas

El listado de productos declara table-hover y encabezado table-light: fondo #edf2f7, texto oscuro. Las celdas tienen padding 1rem; el móvil reduce a .75rem. DataTables incorpora Responsive y un adaptador Bootstrap 5.

No copiar la estructura funcional del listado: Punto Aparte renderiza productos en HTML y tiene columnas Detalle/Acciones con modales; EPP usa consultas serverSide y navegación a fichas desde filas. La posición del buscador se rige por las decisiones vigentes al inicio de este documento.

### Detalles, modales y estados

Los datos de detalle utilizan pares etiqueta/valor separados por bordes, etiquetas secundarias pequeñas y valores que admiten cortes de línea. Los modales de detalle están centrados y permiten scroll. Los menús y mensajes tienen radios coherentes. Hay foco explícito y tratamiento de movimiento reducido en parte del CSS.

### Pantallas especializadas

Acceso usa tarjeta de máximo 34rem, radios 1.5rem y botón mucho mayor. Caja emplea paneles, tarjetas de producto y resumen de venta. Pantalla del cliente usa tipografía y espaciado mayores para lectura a distancia. Son variantes por tarea: no son plantillas para todas las pantallas de EPP.

### Aspectos que no conviene copiar

La hoja general contiene reglas iniciales de sidebar blanco que luego se sobrescriben con azul; también cambia overflow hidden a visible. Es evidencia de evolución del CSS, no una causa probada de fallos. Copiar todo trasladaría reglas innecesarias. Evitar asimismo z-index arbitrarios, overflow-x:hidden como forma de esconder errores de ancho y estilos globales que convierten todos los outline-primary en botones sólidos sin una variante explícita.

## 2. Diferencias comprobadas en gestor-epp

| Aspecto | Punto Aparte | Gestor EPP revisado | Adaptación objetivo |
|---|---|---|---|
| Azul primario | #17324d | #1d4d85 | Unificar en #17324d |
| Sidebar | #17324d | #183450 | Igualar a referencia |
| Fondo | #f1f4f8 | #F1F5F9 | Igualar a referencia |
| Texto | #1b2d48 | #0F172A | Igualar a referencia |
| Bordes | #d9e1eb | #CBD5E1 | Borde más suave |
| Radio tarjeta | 1.25rem | 12px | Adoptar 1.25rem |
| Botones | Altura mínima 2.75rem | Fuente .82rem | Variante normal legible |
| Encabezado tabla | Claro y texto oscuro | Azul y texto blanco | Adoptar encabezado claro |
| Formulario | Tarjeta centrada | form-shell sin límite | Conservar estructura Nuevo elemento; ajustar tokens compartidos |
| Fuente | system-ui | Calibri primero antes de UI-07 | Usar `system-ui, -apple-system, "Segoe UI", sans-serif` |
| Sidebar contraído | 4.5rem | 28px | Conservar franja 28px de EPP |
| Motor de tablas | HTML con DataTables | serverSide | Conservar serverSide |

Los valores nuevos de esta tabla son especificaciones propuestas para cumplir el parecido solicitado, no cambios ya aplicados ni decisiones históricas del usuario.

La documentación docs/09-componentes-y-datatables.md mezcla resultados históricos (encabezado grafito y franjas), reglas posteriores sin franjas y dos agrupaciones distintas para Proyectos. Debe dividirse en estado vigente e historial. AGENTS.md conserva una instrucción antigua de no tratar Django/PostgreSQL como decisiones cerradas junto con otra posterior de mantenerlos: señalar expresamente que la decisión posterior prevalece.

## 3. Norma visual objetivo

### Tokens y propiedad

Una única fuente de valores en app.css o un archivo de tokens importado una vez. Mapear variables CoreUI y las variables Bootstrap que necesita el adaptador DataTables. No cargar otro Bootstrap ni modificar vendor. Los nombres siguientes indican funciones, no obligan a renombrar variables existentes:

| Función | Valor objetivo |
|---|---|
| Primario y sidebar | #17324d |
| Hover primario | #294e70 |
| Activo navegación | #304b68 |
| Texto principal | #1b2d48 |
| Texto secundario | #566b86 |
| Fondo página | #f1f4f8 |
| Superficie | #ffffff |
| Borde | #d9e1eb |
| Encabezado tabla | #EAF4FB |
| Hover fila | #f1f4f8 |
| Acción destructiva | #ad2431 |
| Foco | #6f91b5 |
| Radio tarjeta | 1.25rem |
| Radio control/botón | .65rem |
| Radio etiqueta | .5rem |
| Separaciones | .25, .5, .75, 1, 1.25, 1.5, 2, 3rem |

La familia vigente es `system-ui, -apple-system, "Segoe UI", sans-serif`, aplicada globalmente a texto y controles. UI-07 no modifica tamaños, pesos ni espaciados tipográficos. Los tamaños objetivo de una adaptación futura siguen pendientes de decisión e implementación: cuerpo y botones normales 1rem; etiquetas .9375rem; ayudas y encabezados de tabla .875rem; títulos de grupo .72rem; h1 adaptable entre 1.65 y 2rem. Interlineado general 1.6. No reducir texto para resolver problemas de ancho.

### Estructura de página

Orden: ruta contextual si existe; título y acción principal; filtros/búsqueda; contenido; información de resultados/paginación. Un solo h1. Las pestañas no repiten su título inmediatamente dentro del panel. Los botones Agregar van junto al título; móvil permite envolverlos. No añadir descripciones de relleno.

Contenedores flex/grid deben permitir encogimiento mediante min-width:0. Tablas y tarjetas ocupan el ancho útil, descontado el padding. No fijar una tabla al ancho medido al iniciar. No usar overflow oculto como sustituto de responsive.

### Sidebar

Mantener 255px expandido y franja 28px contraída. Fondo institucional; grupos pequeños en mayúsculas/negrita; títulos y opciones alineados al mismo eje izquierdo; sin iconos de navegación. Separadores solo entre grupos. Conservar opciones y permisos EPP. Marca activa y hover como referencia. Botón centrado sobre borde derecho, círculo visual aproximadamente 28–30px y área interactiva 44px. Fuera de cualquier recorte y alcanzable con teclado. El contenido oculto no recibe foco. Un único controlador CoreUI con integración de aplicación; nunca dos manejadores de toggle.
La identidad original «E» / «Gestor EPP» permanece encima de los grupos. En escritorio el primer título de grupo se alinea en altura con el título principal usando espaciados compartidos del encabezado y del contenido. En móvil se prioriza la navegación; en la franja contraída se ocultan identidad y enlaces.

### Tarjetas y botones

Padding general adaptable entre 1.25 y 2rem. Tarjetas de tablas: 1.5rem escritorio y 1rem móvil como punto inicial. Sin sombras decorativas generales. Inicio sin iconos, acciones separadas por línea y alineadas abajo. Proyectos conserva seis tarjetas, fecha y estado.

Primario azul sólido: Agregar/Guardar/Confirmar. Secundario blanco con borde: Cancelar y acciones auxiliares. Peligro rojo únicamente para acciones destructivas. No colorear cada módulo con un azul diferente. Botones normales con área mínima 44px; variantes compactas explícitas sin perder usabilidad. Los enlaces de navegación no se convierten en botones de envío.

### Formularios

Nuevo elemento es la referencia estructural confirmada. Compartir renderizado de campo, ayuda, error y acciones; no copiar HTML por formulario. Etiqueta siempre asociada al control; (opcional) solo si realmente corresponde, con obligaciones condicionales respetadas. Fondo blanco incluso al enfocar, foco visible y error asociado. Guardar primero y Cancelar después, orden consistente. Cancelar no modifica datos ni lleva al catálogo retirado. Formularios complejos de factura pueden agrupar líneas y totales sin inventar otro estilo.

### Tablas, búsqueda y navegación

Encabezado claro, filas blancas y hover gris suave. Sin striped ni sombreado permanente de columna ordenada. Descripción solo en Inventario general; inventario del proyecto conserva sus datos. Texto puede envolver; cifras deben mantener legibilidad. Acciones compactas solo donde todavía sean necesarias.

DataTables Responsive muestra detalles mediante botón explícito; debe conservar identificación de elemento y acceso a los datos ocultos. Expandir nunca navega a la ficha. Mantener enlace semántico del nombre sin subrayado permanente, foco reconocible y clic de fila existente. No interceptar selección de texto, botones, controles o enlaces auxiliares.

Buscador oficial dentro de la tarjeta, con rótulo visible «Buscar» a la izquierda y sin botón de envío. Placeholder enumera únicamente campos realmente buscados, sin prefijo ni puntos suspensivos. Un solo buscador por listado. Conservar ordenación/búsqueda global en servidor, debounce y cancelación de peticiones obsoletas. Paginación común visualmente, sin reemplazar el motor de tarjetas por DataTables. Ocultarla cuando solo haya una página conservando recuento.

Reajustar columnas y Responsive al finalizar cambios relevantes de contenedor/sidebar y al mostrar pestañas. No reinicializar tablas ni emitir consultas de datos solo para corregir ancho. Pendiente aparece antes de la cantidad entregada y no se transforma en una entrega real.

### Pestañas, menús, carga y accesibilidad

Pestañas visibles y legibles en móvil, con foco y estado activo claros. Enlaces entre rutas conservan semántica de enlaces; paneles interactivos usan CoreUI Tab. Menús no recortados por tarjetas; respetar la jerarquía de capas de modales, sin poner un menú por encima de cualquier diálogo indiscriminadamente.

Carga, vacío, error y éxito son estados distintos. Conservar contenido durante actualización. Mantener demora de 180ms solo para presentar indicador, nunca para demorar petición. Mensajes de error con recuperación, sin confundirlos con cero resultados. Texto además de color para estados. Respetar movimiento reducido, teclado, Escape y retorno del foco. Validar contraste en la implementación; los tokens por sí solos no certifican accesibilidad.

## 4. Componentes que deben ser la fuente única

Reutilizar los ya presentes: page_heading.html, form_fields.html, sidebar_nav.html, pagination.html, project_tabs.html; app.css, components.js, datatables.js, loading.js, cards.js e item-picker.js. Revisar sus contratos antes de ampliar. Evitar un framework de componentes nuevo.

Toda pantalla nueva debe declarar qué componentes reutiliza. Solo crear una variante cuando la tarea del usuario realmente cambie; documentar el motivo y mantener tokens comunes. Las clases por módulo no deben redefinir el botón o campo base.

## 5. Plan de adopción y criterios de cierre

1. Consolidar documentación vigente y registrar esta especificación. No aplicar todos los cambios visuales a ciegas.
2. Implementar tokens, tipografía y controles; comparar Inventario y Nuevo elemento como pantallas piloto.
3. Adaptar estructura y sidebar con la captura de referencia; probar abierto, contraído, scroll y alturas pequeñas.
4. Adaptar tablas y pestañas: Inventario, entregas, historial; verificar dimensiones después de redimensionar.
5. Extender a inicio, proyectos, categorías, proveedores y facturas mediante los componentes compartidos.
6. Revisar vacíos, errores, cargas y formularios largos. Eliminar reglas sustituidas y referencias documentales obsoletas.

Por bloque: antes/después a igual viewport y datos; 320,390,768,1024,1440px; escritorio→móvil→escritorio sin recargar; zoom 200%; teclado; tablas vacías, una fila y varias páginas; textos largos; pestañas ocultas; menús cercanos al borde. Probar Firefox y Chromium; si uno falta, declararlo. No afirmar equivalencia visual a partir de tests Django.

Pruebas funcionales: solicitudes descuentan stock una vez, entrega no vuelve a descontar reserva, corrección/anulación conservan trazabilidad, recepción no duplica stock. Ejecutar pruebas pertinentes cuando los cambios afecten sus formularios o acciones. Una iteración visual no autoriza modificar esos cálculos ni cerrar IVA pendiente.

Cada cierre registra rutas verificadas, capturas, tamaños, navegadores, diferencias pendientes y commit en ITERACIONES.md. No declarar terminada la adaptación si falta validación visual.

## 6. Bloque para integrar en AGENTS.md

Integrar en las convenciones vigentes; no sustituir el archivo completo ni dejar reglas incompatibles:

```markdown
## Sistema visual permanente

- Leer docs/diseno-gestor-epp.md antes de modificar interfaz.
- Usar Punto Aparte work, commit 9f359ac, como referencia visual; las decisiones propias de EPP prevalecen.
- Reutilizar tokens y componentes compartidos. No inventar variantes de botones, campos, tarjetas, tablas, navegación o carga por pantalla.
- Mantener CoreUI y DataTables oficiales, carga única y serverSide existente. No copiar dependencias ni lógica de negocio de Punto Aparte.
- Aplicar las decisiones vigentes de esta guía. La familia global es `system-ui, -apple-system, "Segoe UI", sans-serif`; no cambiar tamaños, pesos ni espaciados sin una solicitud específica.
- Comparar visualmente las pantallas afectadas; cubrir teclado, tamaños estrechos y redimensionamiento de ida y vuelta.
- Retirar reglas sustituidas, actualizar la guía vigente y registrar la iteración. Separar explícitamente historia de instrucciones actuales.
- Toda excepción debe explicar la necesidad, su alcance y su verificación; no ampliar el producto por razones estéticas.
```

## 7. Trazabilidad de fuentes

Base de enlaces: https://github.com/AlbertoCardenas19/punto-aparte/blob/9f359ac45a5caf38c2321b6e79b7ec989ff06cbc/

- static/css/punto-aparte.css: paleta, sidebar, botones, tarjetas, campos, tablas y adaptaciones.
- templates/base.html e includes/menu_principal.html: composición y navegación.
- templates/inicio.html: tarjetas y área de acciones.
- templates/catalogo/formulario.html y lista_productos.html: formularios y tabla de referencia.
- templates/includes/datatables_js.html: carga de extensiones.
- static/css/acceso.css, caja.css y pantalla-cliente.css: variantes especializadas.
- templates/ventas/detalle.html: detalle de operación.

Base EPP: https://github.com/AlbertoCardenas19/gestor-epp/blob/f08a625c74c488f3be46eb0442c7c10c6017fb65/

- AGENTS.md y docs/09-componentes-y-datatables.md: reglas actuales e historia mezclada.
- projects/static/projects/app.css: comparación de valores y comportamiento declarado.
- projects/templates/projects/base.html, form_fields.html y page_heading.html: componentes existentes.
- inventory/templates/inventory/common_list.html: listado que debe conservar su contrato funcional.

Este informe cubre el sistema visual y una muestra representativa de plantillas. No es una auditoría exhaustiva de seguridad, negocio, rendimiento ni de todas las rutas ejecutadas. Queda pendiente comprobar el resultado renderizado completo durante la adopción.
