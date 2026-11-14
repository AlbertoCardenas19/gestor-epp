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
  function alignScrollTables(element) {
    const container = element.closest('.dt-container');
    const tables = [...(container?.querySelectorAll('.dt-scroll-head table, .dt-scroll-body table') || [])];
    if (tables.length !== 2 || tables.some(table => !table.getBoundingClientRect().width)) return;
    const headers = [...container.querySelectorAll('.dt-scroll-head th[data-dt-column]')];
    if (!headers.length) return;
    const actionIndexes = new Set(headers.filter(header => header.hasAttribute('data-actions'))
      .flatMap(header => header.getAttribute('data-dt-column').split(',')));
    const widths = headers.map(header => header.getBoundingClientRect().width);
    const viewportWidth = container.clientWidth;
    const naturalWidth = widths.reduce((total, width) => total + width, 0);
    const width = Math.max(viewportWidth, naturalWidth);
    const flexibleWidth = widths.reduce((total, value, index) => total + (actionIndexes.has(String(index)) ? 0 : value), 0);
    const extra = Math.max(0, width - naturalWidth);
    widths.forEach((value, index) => {
      const finalWidth = actionIndexes.has(String(index)) || !flexibleWidth
        ? value : value + extra * value / flexibleWidth;
      container.querySelectorAll(`col[data-dt-column="${index}"]`).forEach(column => {
        column.style.setProperty('width', `${finalWidth}px`, 'important');
        column.style.setProperty('min-width', `${finalWidth}px`, 'important');
        column.dataset.eppAligned = '';
      });
    });
    tables.forEach(table => {
      table.style.setProperty('width', `${width}px`, 'important');
      table.dataset.eppAligned = '';
    });
  }
  function adjust(root = document) {
    root.querySelectorAll('table[data-epp-aligned]').forEach(table => {
      table.style.removeProperty('width'); delete table.dataset.eppAligned;
    });
    root.querySelectorAll('col[data-epp-aligned]').forEach(column => {
      column.style.removeProperty('width'); column.style.removeProperty('min-width'); delete column.dataset.eppAligned;
    });
    DataTable.tables({visible: true, api: true}).columns.adjust();
    requestAnimationFrame(() => root.querySelectorAll('[data-datatable]').forEach(alignScrollTables));
  }
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
          className: actions ? 'table-actions' : '',
          width: actions ? '1%' : undefined,
          render: actions ? undefined : header.dataset.format === 'pending-delivery'
            ? (value, type, row) => type === 'display' ? (row.pending ? '<span class="pending-delivery" role="img" aria-label="Pendiente de entrega" title="Pendiente de entrega">!</span> ' : '') + text.display(value) : value
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
        serverSide: true, processing: false, scrollX: true, autoWidth: false, searchDelay: 300,
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
            loaded = true; loading.finish(); callback(json); adjust(panel || document);
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
          requestAnimationFrame(() => alignScrollTables(element));
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
  window.EppTables = { init, adjust };
  init();
})();
