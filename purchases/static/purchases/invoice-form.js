document.addEventListener('click', event => {
  const button = event.target.closest('[data-form-add]');
  if (!button) return;
  const group = button.closest('[data-form-group]');
  const prefix = group.dataset.formPrefix;
  const count = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  const template = group.querySelector(':scope > [data-form-template]');
  const rows = group.querySelector(':scope > [data-form-rows]');
  const index = Number(count.value);
  const rowHtml = template.innerHTML.replaceAll(`${prefix}-__prefix__`, `${prefix}-${index}`);
  rows.insertAdjacentHTML('beforeend', rowHtml);
  count.value = index + 1;
  EppPicker.init(rows.lastElementChild);
  if (prefix === 'lines') syncLine(rows.lastElementChild);
  rows.lastElementChild.querySelector('input:not([type=hidden]), select')?.focus();
});

function syncLine(row, clear = false) {
  const service = row.querySelector('[name$="-type"]')?.value === 'service';
  row.querySelector('[data-item-fields]').hidden = service;
  row.querySelector('[data-service-fields]').hidden = !service;
  row.querySelector('[data-allocation-fields]').hidden = service;
  if (!clear) return;
  if (service) {
    row.querySelector('[data-picker-value]').value = '';
    row.querySelector('[data-picker-selected]').textContent = 'Sin selección';
    row.querySelectorAll('[data-item-fields] input, [data-item-fields] textarea').forEach(input => {
      if (!input.matches('[data-picker-search]')) input.value = '';
    });
    const allocations = row.querySelector('[data-allocation-fields]');
    allocations.querySelector('[name$="-TOTAL_FORMS"]').value = '0';
    allocations.querySelector('[data-form-rows]').replaceChildren();
  } else {
    row.querySelector('[name$="-description"]').value = '';
  }
}
document.addEventListener('change', event => {
  if (event.target.matches('[name$="-type"]')) syncLine(event.target.closest('[data-form-row]'), true);
});
document.querySelectorAll('[data-form-group][data-form-prefix="lines"] > [data-form-rows] > [data-form-row]').forEach(row => syncLine(row));
