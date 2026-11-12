(() => {
  const form = document.querySelector('[data-live-table]');
  const results = document.querySelector('[data-table-results]');
  const feedback = document.querySelector('[data-table-feedback]');
  if (!form || !results || !feedback || !window.fetch || !window.AbortController) return;

  const query = form.elements.namedItem('q');
  let timer;
  let controller;
  let revision = 0;
  let composing = false;

  function filterURL() {
    const url = new URL(form.action || location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();
    url.hash = '';
    return url;
  }

  function cancelPending() {
    clearTimeout(timer);
    controller?.abort();
    return ++revision;
  }

  function update(url, mode = 'replace', delay = 0, restoreForm = false, focusTable = false) {
    const current = cancelPending();
    results.setAttribute('aria-busy', 'true');
    feedback.textContent = 'Buscando…';
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error('No se pudo consultar la tabla.');
        const documentResult = new DOMParser().parseFromString(await response.text(), 'text/html');
        const nextResults = documentResult.querySelector('[data-table-results]');
        if (!nextResults) throw new Error('La respuesta no contiene una tabla.');
        // Una respuesta anterior nunca debe reemplazar una búsqueda más reciente.
        if (current !== revision) return;
        results.replaceChildren(...nextResults.childNodes);
        form.elements.namedItem('sort').value = documentResult.querySelector('[name=sort]').value;
        if (restoreForm) {
          const nextForm = documentResult.querySelector('[data-live-table]');
          for (const field of form.elements) {
            if (field.name) field.value = nextForm.elements.namedItem(field.name).value;
          }
        }
        if (mode === 'push') history.pushState(null, '', url);
        if (mode === 'replace') history.replaceState(null, '', url);
        feedback.textContent = results.querySelector('.table-summary p').textContent;
        if (focusTable) results.querySelector('[role="region"]').focus({ preventScroll: true });
      } catch (error) {
        if (current !== revision || error.name === 'AbortError') return;
        feedback.textContent = 'No se pudo actualizar la tabla. Se mantienen los resultados anteriores. Pulsa Aplicar para reintentar.';
      } finally {
        if (current === revision) results.setAttribute('aria-busy', 'false');
      }
    }, delay);
  }

  query.addEventListener('compositionstart', () => {
    composing = true;
    cancelPending();
    results.setAttribute('aria-busy', 'false');
    feedback.textContent = '';
  });
  query.addEventListener('compositionend', () => {
    composing = false;
    update(filterURL(), 'replace', 300);
  });
  query.addEventListener('input', event => {
    if (!composing && !event.isComposing) update(filterURL(), 'replace', 300);
  });
  form.addEventListener('change', event => {
    if (event.target.tagName === 'SELECT') update(filterURL());
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    update(filterURL());
  });
  results.addEventListener('click', event => {
    const link = event.target.closest('.pagination a, [data-table-sort]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (results.getAttribute('aria-busy') === 'true') return;
    const url = new URL(link.href);
    if (link.hasAttribute('data-table-sort')) {
      form.elements.namedItem('sort').value = url.searchParams.get('sort');
    }
    update(url, 'push', 0, false, true);
  });
  window.addEventListener('popstate', () => update(new URL(location.href), 'none', 0, true));
})();
