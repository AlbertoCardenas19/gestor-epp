# Fuentes, trazabilidad y límites

## Procedencia
Base reconstruida el 12 de noviembre de 2026 a partir del historial recuperado del proyecto de la amiga prevencionista, principalmente la conversación «Recordar proyecto amiga». No es una transcripción completa ni una revisión del repositorio. Las fechas se usan para localizar conversaciones, sin convertir marcas técnicas en horas locales.

Los códigos S0–S17 son referencias internas de las fuentes, no IDs de decisiones previamente aprobadas.

| Ref. | Conversación o momento | Evidencia recuperada |
|---|---|---|
| S0 | 19 de octubre de 2026, presentación del proyecto | App web para la prevencionista, gestión de EPP y dinero/proyectos. |
| S1 | 19 de octubre de 2026, cuestionario, respuestas 1–10 | Detalle resumido debajo. |
| S2 | 19 de octubre de 2026, aclaraciones, respuestas 11–14 | Detalle resumido debajo. |
| S3 | 19 de octubre de 2026, mensaje posterior a las aclaraciones | El usuario deja las reglas de negocio detalladas para más adelante durante el desarrollo. |
| S4 | 20 de octubre de 2026, contexto de colaboración y práctica | Desarrollar el producto comercial junto con su amiga; intención de práctica profesional y eventual aporte menor de la empresa. |
| S5 | 12 de noviembre de 2026, corrección en la conversación actual | El usuario identifica que el paquete previo se basó en otra idea y confirma que el proyecto correcto es la app de gestión para su amiga prevencionista. Solicita solo contenido de este proyecto, sin inventar. |
| S6 | 19 de octubre de 2026, recomendación técnica del asistente | Django + PostgreSQL + Render fueron sugeridos; no se recuperó aprobación explícita. No se usan como requisito. |
| S7 | 12 de noviembre de 2026, inicio del desarrollo | Django, PostgreSQL, CoreUI con Bootstrap y campos y primer flujo de proyectos aceptados. |
| S8 | 12 de noviembre de 2026, propuesta del catálogo | Campos iniciales y catálogo común para todos los proyectos aceptados. |
| S9 | 12 de noviembre de 2026, definición inicial de inventario | Cantidades, apertura previa a entradas, responsable y datos mínimos aceptados. Correcciones por anulación con motivo y reemplazo vinculado aceptadas. |
| S10 | 12 de noviembre de 2026, definición inicial de entregas | Entrega directa al trabajador, identificado por nombre completo; descuento al entregar y bloqueo si supera el saldo disponible. |

## S7 — Decisiones posteriores al diagnóstico del repositorio

12 de noviembre de 2026, conversación de inicio del desarrollo:

- El usuario indicó conservar Django y comenzar con PostgreSQL.
- Eligió CoreUI y Bootstrap para la interfaz, y confirmó que «codeui» se refería a CoreUI.
- Aceptó nombre obligatorio y descripción opcional para proyectos en esta etapa; señaló que podrían añadirse más datos después.
- Tras el diagnóstico y la propuesta, autorizó avanzar con crear, listar y consultar proyectos como primer flujo.
- Estas decisiones no cierran el alojamiento, las reglas de inventario, los permisos ni el mecanismo de aprobación.

## S1 — Respuestas 1–10 del usuario
Resumen de las respuestas recuperadas; no son citas textuales:

1. Empresa con varios proyectos.
2. Inicialmente solo ella; posibilidad de más usuarios.
3. Uso desde computador y celular.
4. Ella pide los elementos y los entrega a otra persona.
5. Inventario por proyecto.
6. Registrar entregas, devoluciones y reposiciones.
7. Selección de una opción de gestión financiera completa, aclarada después en S2.
8. Cada proyecto tiene presupuesto, aunque no le influye a ella en su función.
9. Adjuntar facturas, comprobantes de transferencia y cotizaciones. Preparar lista de necesidades, cotizar y presentar al jefe.
10. No hay sistema definido; principalmente se usa WhatsApp.

## S2 — Aclaraciones 11–14 del usuario
Resumen de las respuestas recuperadas; no son citas textuales:

11. El jefe aprueba y ella realiza la compra.
12. Se necesita saber a qué trabajadores se entregaron los EPP posteriormente.
13. Ella no administra dinero, pero la empresa debe gestionar presupuestos. La opción más cercana es abarcar el dinero que ingresa y sale de cada proyecto.
14. Inicialmente EPP y señaléticas; quizá más elementos después.

La aclaración 13 precisa las respuestas 7 y 8: no asignar finanzas a la prevencionista. No se recuperó una respuesta numerada 15.

## S8 — Primera versión del catálogo

12 de noviembre de 2026, respuesta del usuario a la propuesta de RF-05:

- Aceptó nombre obligatorio, tipo obligatorio (EPP o señalética) y descripción
  opcional como campos suficientes para la primera versión.
- Confirmó que el catálogo será común para todos los proyectos.
- El flujo propuesto comprende crear, listar y consultar elementos.
- Esto no define cantidades, movimientos, reglas de stock, tallas, medidas,
  modelos, unicidad de nombres, edición, eliminación ni ampliación de tipos.

## S9 — Acuerdos iniciales de inventario por proyecto

12 de noviembre de 2026, respuestas del usuario a la propuesta de RF-04:

- Aceptó cantidades enteras, existencia inicial de cero o más y entradas mayores
  que cero; no se admiten cantidades negativas en esos formularios.
- Tras aclarar el ejemplo, aceptó registrar primero un conteo inicial por cada
  proyecto y elemento, incluido cero cuando corresponda, y después nuevas entradas.
  La apertura se registra una sola vez para esa combinación. No tener apertura
  significa que todavía no se ha registrado el conteo; no equivale a contar cero.
- La prevencionista registrará todo, como única usuaria por el momento. Esto no
  cierra la implementación de cuentas ni la identificación técnica de la autora.
- Consideró suficiente por ahora la información propuesta: proyecto, elemento
  del catálogo común, operación, cantidad, fecha del hecho, persona que registra
  y observación opcional.
- Confirmó que es necesario corregir registros ya guardados y luego aceptó
  hacerlo mediante anulación con motivo y creación de un registro correcto
  vinculado al anterior. Se conserva el original en el historial y el saldo
  cuenta únicamente los registros válidos. Aplica a aperturas y entradas.
- Aclaró que acepta esta forma de trabajo de momento y que podría cambiar en
  el futuro. No se interpreta como requisito de implementar configuración de reglas.
- Al cerrar estos acuerdos el inventario aún no estaba implementado; el estado
  de desarrollo posterior se detalla en `06-desarrollo.md`. No se cierran salidas, entregas,
  devoluciones, reposiciones, transferencias, stock mínimo ni ajustes automáticos.

## S10 — Primera versión de entregas directas

12 de noviembre de 2026, respuestas del usuario a la propuesta de RF-08 y RF-09:

- Aceptó comenzar de momento con entregas directas, sin intermediarios en este flujo.
- Aceptó identificar al trabajador únicamente por nombre completo por ahora.
- Confirmó descontar el inventario al entregar al trabajador.
- Confirmó bloquear una entrega si supera el saldo disponible del proyecto.
- Las respuestas no cierran la corrección o anulación de entregas, ni el futuro
  flujo con intermediarios, RUT, cuentas, firmas, devoluciones o reposiciones.
- Estas decisiones corresponden a la primera versión y no impiden revisarlas.

## S11 — Alcance de las dos siguientes iteraciones

12 de noviembre de 2026, instrucciones posteriores del usuario:

- Confirmó haber descargado y probado las entregas directas en su PC.
- Ratificó entrega directa con destinatario, elemento, proyecto, cantidad, fecha
  y observación opcional, conservando descuento, bloqueo por saldo insuficiente
  y destinatario visible en el historial. No se implementarán intermediarios.
- Solicitó acordar las reglas antes de implementar correcciones en la primera
  iteración y, después, acordar e implementar la anulación en una segunda.
- Excluyó las devoluciones físicas de estas dos iteraciones. La propuesta previa
  del asistente de hacer devoluciones como segunda iteración queda descartada.
- Pidió pruebas por iteración, revisión en escritorio y móvil y Firefox si está
  disponible, documentación de acuerdos y un commit separado por iteración, sin push.
- Al formular esta solicitud no había aprobado los campos editables, el mecanismo
  ni los efectos concretos de corrección o anulación. S12 recoge la aprobación
  posterior de la corrección; la anulación sigue pendiente.

## S12 — Corrección de entregas aprobada

12 de noviembre de 2026, el usuario respondió «sí a todo» a las tres decisiones
necesarias de la primera iteración:

- Permitir corregir destinatario, elemento, proyecto, cantidad, fecha y observación.
- Conservar el original, exigir motivo y crear un reemplazo vinculado, corrigiendo
  únicamente el registro vigente y manteniendo la cadena de correcciones.
- Aplicar el ajuste neto en una misma posición o revertir el descuento anterior
  y aplicar el correcto si cambia proyecto o elemento. Si el destino no tiene
  apertura o saldo suficiente, rechazar por completo sin cambiar registros ni saldos.

Al aprobar S12, la anulación sin reemplazo seguía pendiente para la segunda
iteración; posteriormente se acordó en S13. Las devoluciones físicas permanecen
fuera de ambas iteraciones.

## S13 — Anulación de entregas aprobada

12 de noviembre de 2026, el usuario confirmó las cinco reglas propuestas y pidió
implementar la segunda iteración:

1. Anular completamente solo una entrega vigente, con motivo obligatorio.
2. Conservar sus datos, motivo y fecha de anulación, sin crear un reemplazo.
3. Restituir una sola vez la cantidad al proyecto y elemento del registro vigente.
4. Ante solicitudes repetidas o simultáneas, informar que ya está anulada sin
   modificar el saldo otra vez.
5. Rechazar la anulación de un original sustituido; actuar sobre su reemplazo vigente.

La anulación corresponde a un registro equivocado y no representa una devolución
física. El usuario exigió reversión completa ante fallos, pruebas en PostgreSQL,
escritorio y móvil, informar la limitación de Firefox, conservar el commit de la
primera iteración y crear otro separado sin push, además de pasos de prueba manual.

## S14 — Navegación y presentación aprobadas

El usuario solicitó negro, blanco y dorado; retirar el banner de proyectos,
las etiquetas decorativas sobre los títulos, «Gestión de prevención» del header,
el footer y la nota inferior del sidebar. Solicitó inicio con paneles,
sidebar retráctil, entregas visibles al abrir un proyecto y catálogo en tabla.

En las aclaraciones confirmó:

- Una fila por entrega, sin agrupar por elemento ni trabajador.
- Entregas como pestaña inicial del proyecto e Inventario como segunda pestaña.
- Mostrar vigentes por defecto y permitir consultar todos los estados.
- Contraer el sidebar a una columna de iconos.

Aceptó el inicio con accesos a Proyectos y Catálogo y las tablas con búsqueda,
ordenación y paginación en español. Estos cambios de presentación no modifican
las reglas de existencias, corrección, anulación ni los datos del catálogo.

## S15 — Ajustes de interfaz y búsqueda automática

El usuario solicitó divisores entre grupos del sidebar, control de contracción
solo con flecha y más separado, formularios que aprovechen el ancho de pantalla,
filtrado mientras escribe y tablas con filas alternadas. Confirmó que la nueva
paleta se aplica a todo el sistema: principal `#334155`, secundario `#64748B`,
fondo `#F1F5F9`, superficies `#FFFFFF`, texto `#0F172A` y bordes `#CBD5E1`.
Sustituye la paleta negro/blanco/dorado de S14. Se conserva Entregas como vista
inicial del proyecto, según su respuesta posterior.

## S16 — Revisión del flujo: stock común y solicitudes por proyecto

Durante la ronda de preguntas, el usuario aclaró el modelo que desea:

- Las cantidades representan existencias reales de la empresa, compartidas entre
  proyectos, en lugar de exigir una apertura independiente en cada proyecto.
- Agregar un elemento al proyecto representa una solicitud, que puede estar
  pendiente de entrega; no una entrega ya realizada.
- La solicitud reserva existencias; la entrega real descuenta stock.
- No permitir solicitudes que superen el stock disponible.
- Mantener la consulta de entregas realizadas como vista inicial del proyecto.

Son decisiones para el próximo rediseño, **todavía no implementado**. La versión
actual continúa calculando existencias por proyecto, con las reglas S9–S13.
No se han modificado registros, modelos, servicios ni migraciones por S16.

En las siguientes respuestas confirmó:

- Un elemento sin cantidad inicial comienza con stock cero y permite entradas posteriores.
- Se permiten entregas parciales; lo pendiente sigue reservado.
- Se puede reducir o cancelar lo pendiente, liberando la reserva, con motivo
  obligatorio e historial, sin modificar las entregas ya realizadas.
- Los datos actuales de su PC son solo de prueba. Esto no autoriza borrarlos:
  se conserva el trabajo existente y se preparará una transición explícita.

Antes de implementar hay que concretar la transición del historial y la relación
entre solicitudes y las correcciones/anulaciones de entregas. No se asume su
comportamiento sobre las reservas ni se modifica el historial actual.

## S17 — Tablas, errores y comportamiento del sidebar

El usuario pidió retirar los avisos de éxito como «Elemento creado correctamente»
y el texto visible «Registrado por: Prevencionista»; diferenciar las franjas de
las tablas del fondo de página; transición suave del sidebar y corregir el salto
vertical de su flecha; errores en rojo bajo el campo correspondiente, incluido
saldo insuficiente; Proyectos como tabla; ordenación desde cada encabezado de
datos, retirando «Ordenar por»; Fecha como primera columna de Entregas; y opciones
de acciones dentro de un select por fila.

Son cambios de presentación y ubicación de errores. No modifican las reglas de
existencias, corrección ni anulación. El stock común y las solicitudes de S16
siguen pendientes de implementación.

## Qué se excluyó
- La idea de junio de automatizar documentos para distintos profesionales: no corresponde a este producto. Se excluyen sus requisitos de plantillas, generación PDF/Excel, IPER, AST, reportes de incidentes y charlas.
- Requisitos, decisiones y tecnología de otros proyectos del usuario.
- Propuestas del asistente que no tienen aceptación recuperada, salvo la mención explícita de S6 para evitar que se confunda con una decisión.
- Reglas, criterios de aceptación y prioridades que exigirían inventar detalle.

La exclusión significa que no se incorporan a esta base como acuerdos; no prohíbe que el usuario los solicite en el futuro.

## Límites
La reconstrucción inicial no recuperó decisiones suficientes para cerrar el MVP, tecnologías, permisos, campos o reglas de stock. S7 registra las decisiones posteriores sobre tecnologías y los campos iniciales de proyectos; S8 registra los campos y el alcance del catálogo inicial. Eso no demuestra que no existan conversaciones adicionales. Se documentan únicamente los acuerdos que pudieron recuperarse y atribuirse a este proyecto.

No se certifican funcionalidades ya implementadas, cumplimiento normativo, contratos, aprobación de práctica, presupuesto de infraestructura ni estado de un repositorio.

## Corrección del paquete anterior
Esta entrega reemplaza por completo la documentación anterior basada erróneamente en la app de automatización documental. Sus requisitos RF-001 y siguientes y su backlog no son fuente válida para este proyecto. Los identificadores RF-01 a RF-14 de esta entrega corresponden al alcance de gestión recuperado aquí.
