/* CoreUI owns interactions; this file only adds app persistence and Popper options. */
(() => {
  function init(root = document) {
    root.querySelectorAll('[data-coreui-toggle="dropdown"]').forEach(button => {
      coreui.Dropdown.getOrCreateInstance(button, {
        popperConfig: defaults => ({
          ...defaults,
          strategy: 'fixed',
          modifiers: [...defaults.modifiers, { name: 'preventOverflow', options: { boundary: document.body } }],
        }),
      });
    });
  }
  function dispose(root) {
    root.querySelectorAll('[data-coreui-toggle="dropdown"]').forEach(button => {
      const dropdown = coreui.Dropdown.getInstance(button);
      if (dropdown) { dropdown.hide(); dropdown.dispose(); }
    });
  }
  window.EppComponents = { init, dispose };
  init();

  const sidebar = document.querySelector('#sidebar');
  if (!sidebar) return;
  const button = sidebar.querySelector('.sidebar-toggle');
  const component = coreui.Sidebar.getOrCreateInstance(sidebar);
  let collapsed = matchMedia('(max-width: 767px)').matches;
  try {
    const saved = localStorage.getItem('gestor-epp-sidebar');
    if (saved !== null) collapsed = saved === 'collapsed';
  } catch (_) {}
  if (collapsed) component.narrow();
  function sync() {
    const narrow = sidebar.classList.contains('sidebar-narrow');
    const label = narrow ? 'Expandir menú' : 'Contraer menú';
    button.setAttribute('aria-expanded', String(!narrow));
    button.setAttribute('aria-label', label);
    button.title = label;
    try { localStorage.setItem('gestor-epp-sidebar', narrow ? 'collapsed' : 'expanded'); } catch (_) {}
  }
  new MutationObserver(sync).observe(sidebar, { attributes: true, attributeFilter: ['class'] });
  button.hidden = false;
  sync();
})();
