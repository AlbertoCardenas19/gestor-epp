/* Shared DataTables conventions: keep per-screen declarations in table markup. */
(() => {
  const language = {
    decimal: ',', thousands: '.',
    emptyTable: 'No hay registros disponibles.', zeroRecords: 'No se encontraron resultados.',
    search: 'Buscar', searchPlaceholder: '', lengthMenu: 'Mostrar _MENU_ filas',
    info: '_START_–_END_ de _TOTAL_ registros', infoEmpty: '0 registros',
    infoFiltered: '(filtrados de _MAX_ registros)', loadingRecords: '', processing: '',
    paginate: { first: 'Primera', last: 'Última', next: 'Siguiente', previous: 'Anterior' },
    aria: { orderable: ': activar para ordenar', orderableReverse: ': activar para invertir el orden',
      orderableRemove: ': activar para quitar la ordenación', paginate: { first: 'Primera página', last: 'Última página', next: 'Página siguiente', previous: 'Página anterior' } },
  };
  DataTable.ext.errMode = 'none';
  // DataTables owns scroll header widths. One frame per layout change avoids stale
  // measurements while the sidebar, viewport, or a hidden tab changes size.
  let adjustmentFrame = 0;
  function adjust() {
    if (adjustmentFrame) cancelAnimationFrame(adjustmentFrame);
    adjustmentFrame = requestAnimationFrame(() => {
      adjustmentFrame = 0;
      const tables = DataTable.tables({visible: true, api: true});
      tables.columns.adjust();
      tables.responsive.recalc();
    });
  }
  window.addEventListener('resize', adjust);
  function init(root = document) {
    root.querySelectorAll('[data-datatable]').forEach(element => {
      if (DataTable.isDataTable(element)) return;
      const panel = element.closest('[data-datatable-panel]');
      const error = panel?.querySelector('[data-datatable-error]');
      const loading = EppLoading.create(panel || element.parentElement, {
        content: panel?.querySelector('.datatable-shell') || element, shape: 'table', status: error,
      });
      let loaded = false, controller, revision = 0;
      // The shared loader owns this status instead of a second visible error/control.
      if (error) error.hidden = false;
      const text = DataTable.render.text();
      const columns = [...element.tHead.rows[0].cells].map((header, index) => {
        const actions = header.hasAttribute('data-actions');
        return {
          data: header.dataset.column, orderable: !actions && header.dataset.orderable !== 'false', searchable: !actions,
          className: [actions ? 'table-actions' : '', index === 0 ? 'all' : ''].filter(Boolean).join(' '),
          width: actions ? '1%' : undefined,
          createdCell: index === 0 ? cell => {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'row-expand';
            button.setAttribute('aria-label', 'Mostrar columnas adicionales');
            button.setAttribute('aria-expanded', 'false');
            button.innerHTML = '<span aria-hidden="true">+</span>';
            cell.prepend(button);
          } : undefined,
          render: actions ? undefined : header.dataset.format === 'pending-delivery'
            ? (value, type, row) => type === 'display' ? (row.pending ? '<span class="badge pending-delivery">Pendiente</span> ' : '') + text.display(value) : value
            : header.dataset.format === 'excerpt'
            ? (value, type) => type === 'display' ? text.display(value.length > 100 ? value.slice(0, 97) + '…' : value) : value
            : header.dataset.link ? (value, type, row) => {
              if (type !== 'display') return value;
              const link = document.createElement('a'); link.textContent = value; link.href = row[header.dataset.link];
              link.className = 'table-name-link';
              return link.outerHTML;
            } : (header.dataset.format === 'date'
            ? (value, type) => type === 'display' && /^\d{4}-\d{2}-\d{2}$/.test(value)
              ? value.split('-').reverse().join('/') : text.display(value)
            : text),
        };
      });
      const table = new DataTable(element, {
        serverSide: true, processing: false, autoWidth: true, searchDelay: 300,
        responsive: {details: {type: 'column', target: 'button.row-expand',
          renderer: DataTable.Responsive.renderer.listHidden()}},
        pageLength: 10, lengthMenu: [10, 25, 50], language,
        search: { search: new URL(location.href).searchParams.get('q') || '' },
        order: JSON.parse(element.dataset.order || '[[0,"asc"]]'), columns,
        ajax: (params, callback) => {
          controller?.abort(); controller = new AbortController(); const current = ++revision;
          loading.begin(!loaded);
          const url = new URL(element.dataset.source, location.origin);
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
            loaded = true; loading.finish(); callback(json); adjust();
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
          adjust();
          element.closest('.dt-container')?.querySelector('.dt-paging nav')?.setAttribute('aria-label', 'Páginas de la tabla');
        },
      });
      // The BS5 adapter adds mt-2 (a utility with !important); the shared
      // table spacing below owns both gaps instead.
      element.closest('.dt-container')?.querySelector('.dt-layout-table')?.classList.remove('mt-2');
      table.on('responsive-display', (_event, _api, row, shown) => {
        const button = row.node()?.querySelector('.row-expand');
        if (button) {
          button.setAttribute('aria-expanded', String(shown));
          button.setAttribute('aria-label', shown ? 'Ocultar columnas adicionales' : 'Mostrar columnas adicionales');
        }
        if (shown) window.EppComponents.init(element);
      });
      const searchInput = element.closest('.dt-container')?.querySelector('.dt-search input');
      const shell = element.closest('.datatable-shell');
      if (searchInput) searchInput.placeholder = element.dataset.searchPlaceholder || '';
      if (shell && window.ResizeObserver) {
        let lastWidth = shell.clientWidth;
        new ResizeObserver(() => {
          const width = shell.clientWidth;
          if (width && Math.abs(width - lastWidth) >= 1) { lastWidth = width; adjust(); }
        }).observe(shell);
      }
      const rowKey = element.dataset.rowLink;
      if (rowKey) {
        let pointer;
        element.addEventListener('pointerdown', event => {
          pointer = event.button === 0 ? {x: event.clientX, y: event.clientY,
            selection: String(getSelection())} : null;
        });
        element.addEventListener('click', event => {
          if (!pointer || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
          const moved = Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) > 5;
          const selected = String(getSelection()) !== pointer.selection || Boolean(String(getSelection()));
          pointer = null;
          if (moved || selected || event.target.closest('a, button, input, select, textarea, label, [role="button"], [contenteditable]')) return;
          const row = event.target.closest('tbody tr');
          if (!row) return;
          const data = table.row(row).data();
          if (data?.[rowKey]) location.assign(data[rowKey]);
        });
      }
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
    });
  }
  window.EppTables = { init, adjust };
  init();
})();
