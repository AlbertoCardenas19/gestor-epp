# Recursos de navegador fijados

CoreUI 5.4.3 (CSS y bundle con Popper), jQuery 3.7.1, DataTables 2.3.5 e
integración DataTables Bootstrap 5 2.3.5. No se incluye una segunda copia de Bootstrap.
Cada carpeta contiene su licencia MIT. Los archivos vienen de los paquetes npm
oficiales indicados en `manifest.json`, con SHA-512 de archivo npm y SHA-256 por archivo.

Desde la raíz: `python scripts/frontend-vendor.py` verifica los archivos locales;
`python scripts/frontend-vendor.py --restore` restaura los archivos fijados desde npm.
No se necesita Node/npm para ejecutar la app. La guía de uso y actualización está en
[09-componentes-y-datatables.md](../../../docs/09-componentes-y-datatables.md).
