/* Shared DataTables conventions: keep per-screen declarations in table markup. */
(() => {
  const language = {
    decimal: ',', thousands: '.',
    emptyTable: 'No hay registros disponibles.', zeroRecords: 'No se encontraron resultados.',
    search: 'Buscar:', searchPlaceholder: 'Escribe para buscar', lengthMenu: 'Mostrar _MENU_ filas',
    info: '_START_–_END_ de _TOTAL_ registros', infoEmpty: '0 registros',
    infoFiltered: '(filtrados de _MAX_ registros)', loadingRecords: 'Cargando…', processing: 'Procesando…',
    paginate: { first: 'Primera', last: 'Última', next: 'Siguiente', previous: 'Anterior' },
    aria: { orderable: ': activar para ordenar', orderableReverse: ': activar para invertir el orden',
      orderableRemove: ': activar para quitar la ordenación', paginate: { first: 'Primera página', last: 'Última página', next: 'Página siguiente', previous: 'Página anterior' } },
  };
  DataTable.ext.errMode = 'none';
  function init(root = document) {
    root.querySelectorAll('[data-datatable]').forEach(element => {
      if (DataTable.isDataTable(element)) return;
      const panel = element.closest('[data-datatable-panel]');
      const state = panel?.querySelector('[data-datatable-state]');
      const error = panel?.querySelector('[data-datatable-error]');
      const text = DataTable.render.text();
      const columns = [...element.tHead.rows[0].cells].map(header => {
        const actions = header.hasAttribute('data-actions');
        return {
          data: header.dataset.column, orderable: !actions, searchable: !actions,
          render: actions ? undefined : (header.dataset.format === 'date'
            ? (value, type) => type === 'display' && /^\d{4}-\d{2}-\d{2}$/.test(value)
              ? value.split('-').reverse().join('/') : text.display(value)
            : text),
        };
      });
      const table = new DataTable(element, {
        serverSide: true, processing: true, scrollX: true, searchDelay: 300,
        pageLength: 10, lengthMenu: [10, 25, 50], language,
        search: { search: new URL(location.href).searchParams.get('q') || '' },
        order: JSON.parse(element.dataset.order || '[[0,"asc"]]'), columns,
        ajax: { url: element.dataset.source, data: params => { if (state) params.state = state.value; } },
        preDrawCallback() { window.EppComponents.dispose(element); },
        drawCallback() {
          window.EppComponents.init(element);
          element.closest('.dt-container')?.querySelector('.dt-paging nav')?.setAttribute('aria-label', 'Páginas de la tabla');
        },
      });
      const searchInput = element.closest('.dt-container').querySelector('.dt-search input');
      if (searchInput && !searchInput.parentElement.querySelector('[data-search-clear]')) {
        const clear = document.createElement('button');
        clear.type = 'button'; clear.className = 'search-clear'; clear.dataset.searchClear = '';
        clear.setAttribute('aria-label', 'Limpiar búsqueda'); clear.title = 'Limpiar búsqueda';
        clear.textContent = '×';
        searchInput.parentElement.classList.add('search-with-clear');
        searchInput.parentElement.append(clear);
        const sync = () => { clear.hidden = !searchInput.value; };
        searchInput.addEventListener('input', sync);
        table.on('search', sync);
        clear.addEventListener('click', () => { searchInput.value = ''; table.search('').draw(); sync(); searchInput.focus(); });
        sync();
      }
      table.on('dt-error', () => {
        if (error) { error.hidden = false; error.textContent = 'No se pudo cargar la tabla. Recarga la página para reintentar.'; }
      });
      table.on('xhr', (_event, _settings, json) => { if (json && error) error.hidden = true; });
      if (state) state.addEventListener('change', () => {
        const url = new URL(location.href);
        url.searchParams.set('state', state.value);
        history.replaceState(null, '', url);
        table.ajax.reload();
      });
    });
  }
  window.EppTables = { init };
  init();
})();
