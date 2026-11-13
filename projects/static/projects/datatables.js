/* Shared DataTables conventions: keep per-screen declarations in table markup. */
(() => {
  const language = {
    decimal: ',', thousands: '.',
    emptyTable: 'No hay registros disponibles.', zeroRecords: 'No se encontraron resultados.',
    search: 'Buscar:', searchPlaceholder: 'Escribe para buscar', lengthMenu: 'Mostrar _MENU_ filas',
    info: '_START_–_END_ de _TOTAL_ registros', infoEmpty: '0 registros',
    infoFiltered: '(filtrados de _MAX_ registros)', loadingRecords: '', processing: '',
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
      const filters = [...(panel?.querySelectorAll('[data-datatable-filter]') || [])];
      const loading = EppLoading.create(panel || element.parentElement, {
        content: panel?.querySelector('.datatable-shell') || element, shape: 'table', status: error,
      });
      let loaded = false, controller, revision = 0;
      // The shared loader owns this status instead of a second visible error/control.
      if (error) error.hidden = false;
      const text = DataTable.render.text();
      const columns = [...element.tHead.rows[0].cells].map(header => {
        const actions = header.hasAttribute('data-actions');
        return {
          data: header.dataset.column, orderable: !actions, searchable: !actions,
          render: actions ? undefined : header.dataset.format === 'pending-state'
            ? (value, type, row) => type === 'display' ? text.display(value) + (row.pending ? ' <span class="pending-delivery" role="img" aria-label="Pendiente de entrega" title="Pendiente de entrega">!</span>' : '') : value
            : header.dataset.link ? (value, type, row) => {
              if (type !== 'display') return value;
              const link = document.createElement('a'); link.textContent = value; link.href = row[header.dataset.link];
              return link.outerHTML;
            } : (header.dataset.format === 'date'
            ? (value, type) => type === 'display' && /^\d{4}-\d{2}-\d{2}$/.test(value)
              ? value.split('-').reverse().join('/') : text.display(value)
            : text),
        };
      });
      const table = new DataTable(element, {
        serverSide: true, processing: false, scrollX: true, searchDelay: 300,
        pageLength: 10, lengthMenu: [10, 25, 50], language,
        search: { search: new URL(location.href).searchParams.get('q') || '' },
        order: JSON.parse(element.dataset.order || '[[0,"asc"]]'), columns,
        ajax: (params, callback) => {
          controller?.abort(); controller = new AbortController(); const current = ++revision;
          loading.begin(!loaded);
          const url = new URL(element.dataset.source, location.origin);
          if (state) params.state = state.value;
          for (const filter of filters) params[filter.dataset.datatableFilter] = filter.value;
          // Preserve DataTables' bracket parameter protocol, including array order/search values.
          url.search = jQuery.param(params);
          const activeController = controller;
          (async () => {
          try {
            const response = await fetch(url, {signal: activeController.signal});
            if (!response.ok) throw new Error('request');
            const json = await response.json();
            if (!Array.isArray(json.data)) throw new Error('response');
            if (current !== revision) return;
            loaded = true; loading.finish(); callback(json); table.columns.adjust();
          } catch (failure) {
            if (current !== revision || failure.name === 'AbortError') return;
            if (!loaded) callback({draw: params.draw, recordsTotal: 0, recordsFiltered: 0, data: []});
            loading.finish('No se pudo cargar la tabla. Se conservan los resultados anteriores. Busca o cambia de página para reintentar.');
          }
          })();
          return {abort: () => activeController.abort()};
        },
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
      for (const filter of filters) filter.addEventListener('change', () => table.ajax.reload());
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
