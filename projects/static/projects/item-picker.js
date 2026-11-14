/* App-specific card selection; shared loading, server search, no duplicate catalogue. */
(() => {
  document.querySelectorAll('[data-item-picker]').forEach(picker => {
    const input = picker.querySelector('[name="item"]');
    const query = picker.querySelector('[data-picker-search]');
    const results = picker.querySelector('[data-picker-results]');
    const selected = picker.querySelector('[data-picker-selected]');
    const clear = picker.querySelector('[data-picker-clear]');
    const loading = EppLoading.create(picker, {content: results});
    let controller, revision = 0, timer;
    function syncSelection() {
      results.querySelectorAll('[data-item-choice]').forEach(button => {
        const active = button.dataset.itemChoice === input.value;
        button.classList.toggle('selected', active); button.setAttribute('aria-pressed', String(active));
      });
    }
    async function load(page = 1) {
      clearTimeout(timer); controller?.abort(); controller = new AbortController();
      const current = ++revision;
      loading.begin();
      const url = new URL(picker.dataset.source, location.origin);
      url.search = new URLSearchParams({q: query.value, page}).toString();
      try {
        const response = await fetch(url, {signal: controller.signal});
        if (!response.ok) throw new Error('request');
        const html = await response.text();
        if (current !== revision) return;
        const parsed = new DOMParser().parseFromString(html, 'text/html');
        if (!parsed.querySelector('[data-picker-grid]')) throw new Error('response');
        results.replaceChildren(...parsed.body.childNodes); syncSelection(); loading.finish();
      } catch (error) {
        if (current !== revision || error.name === 'AbortError') return;
        loading.finish('No se pudieron actualizar los elementos. Se conservan los resultados. Vuelve a buscar para reintentar.');
      }
    }
    query.addEventListener('input', event => {
      clear.hidden = !query.value; clearTimeout(timer); controller?.abort(); ++revision;
      loading.cancel();
      if (!event.isComposing) timer = setTimeout(() => load(), 300);
    });
    query.addEventListener('compositionend', () => { clearTimeout(timer); timer = setTimeout(() => load(), 300); });
    query.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); load(); } });
    clear.addEventListener('click', () => { query.value = ''; clear.hidden = true; load(); query.focus(); });
    results.addEventListener('click', event => {
      const button = event.target.closest('[data-item-choice]');
      if (button) {
        input.value = button.dataset.itemChoice; selected.textContent = `Seleccionado: ${button.dataset.itemName}`;
        syncSelection(); return;
      }
      const page = event.target.closest('[data-picker-page]');
      if (page) load(page.dataset.pickerPage);
    });
    syncSelection();
  });
})();
