(() => {
  const button = document.querySelector('.sidebar-toggle');
  if (!button) return;
  let collapsed = window.matchMedia('(max-width: 767px)').matches;
  try {
    const saved = localStorage.getItem('gestor-epp-sidebar');
    if (saved !== null) collapsed = saved === 'collapsed';
  } catch (_) { /* El menú funciona aunque el almacenamiento esté deshabilitado. */ }
  function render() {
    document.documentElement.dataset.sidebarCollapsed = String(collapsed);
    const label = collapsed ? 'Expandir menú' : 'Contraer menú';
    button.setAttribute('aria-expanded', String(!collapsed));
    button.setAttribute('aria-label', label);
    button.title = label;
  }
  button.hidden = false;
  render();
  button.addEventListener('click', () => {
    collapsed = !collapsed;
    render();
    try { localStorage.setItem('gestor-epp-sidebar', collapsed ? 'collapsed' : 'expanded'); } catch (_) {}
  });
})();
