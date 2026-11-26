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
  rows.lastElementChild.querySelector('input:not([type=hidden]), select')?.focus();
});
