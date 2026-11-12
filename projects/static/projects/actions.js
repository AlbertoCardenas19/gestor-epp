document.addEventListener('change', event => {
  const select = event.target.closest('[data-row-action]');
  if (!select || !select.value) return;
  const target = new URL(select.value, location.href);
  if (target.origin !== location.origin) return;
  select.selectedIndex = 0;
  location.assign(target.href);
});
