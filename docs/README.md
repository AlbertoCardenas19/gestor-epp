# Guía del repositorio — App prevención de riesgos

Fecha de reconstrucción: 12 de noviembre de 2026.

## Qué contiene
Documentación del proyecto de gestión para la amiga prevencionista. Se reconstruyó a partir de sus acuerdos conversados en octubre y la corrección explícita del usuario en noviembre. La trazabilidad se encuentra en [fuentes](05-fuentes.md).

| Archivo | Uso |
|---|---|
| [AGENTS.md](../AGENTS.md) | Instrucciones para que Codex use correctamente esta base |
| [01-producto.md](01-producto.md) | Objetivo, contexto de trabajo y alcance conocido |
| [02-requisitos.md](02-requisitos.md) | Necesidades expresadas, con fuente por requisito |
| [03-flujos-y-responsabilidades.md](03-flujos-y-responsabilidades.md) | Proceso conversado y responsabilidades conocidas |
| [04-pendientes.md](04-pendientes.md) | Aspectos que las conversaciones no dejan definidos |
| [05-fuentes.md](05-fuentes.md) | Procedencia, exclusiones y límites de la recuperación |
| [06-desarrollo.md](06-desarrollo.md) | Instalación, PostgreSQL y comprobaciones de proyectos, catálogo e inventario |
| [07-iteraciones-entregas.md](07-iteraciones-entregas.md) | Acuerdos, verificación y prueba manual de corrección y anulación de entregas |
| [08-stock-comun-y-solicitudes.md](08-stock-comun-y-solicitudes.md) | Acuerdos y diseño para migrar a stock común y solicitudes con reserva, todavía sin implementar |

## Cómo usarlo
Coloca `AGENTS.md` en la raíz del repositorio y esta carpeta `docs/` también en la raíz. Si ya existen archivos con esos nombres, integra su contenido. Si copiaste el paquete anterior equivocado, reemplaza sus documentos por los de este paquete; no conserves aquel backlog como alcance de este producto.

Para Codex puedes usar este encargo:

> Lee AGENTS.md y los documentos indicados. Inspecciona el repositorio y contrasta lo existente con los requisitos RF-01 a RF-14. Resume lo que encuentres y las decisiones que bloqueen la tarea que te solicite. No implementes el paquete anterior de automatización documental ni completes decisiones pendientes por suposición.

## Estados documentales
- **Necesidad confirmada en conversación:** el usuario la expresó o aclaró; el detalle puede seguir abierto.
- **Contexto:** describe el trabajo actual o la intención del proyecto; no equivale a una funcionalidad.
- **Pendiente:** no se recuperó una decisión suficiente. No significa rechazo ni ausencia definitiva en el proyecto.
- **Propuesta previa:** recomendación del asistente sin aceptación recuperada; no es requisito aprobado.

La numeración y la distribución inicial de archivos se introdujeron para facilitar referencias, sin cerrar el MVP. Posteriormente se acordó comenzar con crear, listar y consultar proyectos; el estado de esa implementación y sus comprobaciones se explica en la guía de desarrollo.
