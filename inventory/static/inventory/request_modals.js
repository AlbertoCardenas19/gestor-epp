(() => {
  const root = document.getElementById('request-modal');
  if (!root) return;
  const content = root.querySelector('.modal-content');
  const modal = coreui.Modal.getOrCreateInstance(root);
  const table = document.querySelector('[data-datatable]');
  let opener;
  document.addEventListener('click', async event => {
    const link = event.target.closest('a[data-request-modal]');
    if (!link) return;
    event.preventDefault();
    opener = link;
    const response = await fetch(link.href);
    if (!response.ok) return;
    content.innerHTML = await response.text();
    modal.show();
  });
  root.addEventListener('submit', async event => {
    const form = event.target.closest('form[data-request-modal-form]');
    if (!form) return;
    event.preventDefault();
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form)});
      if (!response.ok) throw new Error('No se pudo guardar el cambio.');
      const type = response.headers.get('content-type') || '';
      if (type.includes('application/json')) {
        modal.hide();
        if (table && DataTable.isDataTable(table)) new DataTable.Api(table).ajax.reload(null, false);
      } else {
        content.innerHTML = await response.text();
        content.querySelector('.is-invalid, [role="alert"]')?.focus();
      }
    } catch (_) {
      submit.disabled = false;
      let error = content.querySelector('[data-modal-error]');
      if (!error) { error = document.createElement('p'); error.dataset.modalError = ''; error.className = 'alert alert-danger'; form.prepend(error); }
      error.textContent = 'No se pudo guardar. Inténtalo de nuevo.';
    }
  });
  root.addEventListener('hidden.coreui.modal', () => {
    content.innerHTML = '';
    // DataTables can redraw the row after a successful action.
    const trigger = opener?.closest('.dropdown')?.querySelector('[data-coreui-toggle="dropdown"]');
    const current = trigger?.isConnected && trigger.getClientRects().length
      ? trigger : table?.closest('.dt-container')?.querySelector('.dt-search input');
    current?.focus();
  });
})();
