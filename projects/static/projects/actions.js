(() => {
  function position(menu, trigger) {
    const button = trigger.getBoundingClientRect();
    const width = parseFloat(getComputedStyle(menu).width);
    const height = menu.offsetHeight || menu.querySelectorAll('a').length * 44 + 16;
    const left = Math.max(8, Math.min(button.right - width, innerWidth - width - 8));
    const below = button.bottom + 4;
    const top = below + height > innerHeight - 8 ? Math.max(8, button.top - height - 4) : below;
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }
  document.addEventListener('click', event => {
    const trigger = event.target.closest('.action-trigger');
    if (!trigger) return;
    const menu = document.getElementById(trigger.getAttribute('popovertarget'));
    if (menu) {
      menu.actionTrigger = trigger;
      position(menu, trigger);
    }
  });
  document.addEventListener('toggle', event => {
    const menu = event.target;
    if (!menu.matches('.action-menu') || !menu.actionTrigger) return;
    const open = event.newState === 'open';
    menu.actionTrigger.setAttribute('aria-expanded', String(open));
    if (open) position(menu, menu.actionTrigger);
  }, true);
  function repositionMenus() {
    document.querySelectorAll('.action-menu:popover-open').forEach(menu => {
      const trigger = menu.actionTrigger;
      if (!trigger || !trigger.isConnected) return menu.hidePopover();
      const bounds = trigger.getBoundingClientRect();
      if (bounds.bottom < 0 || bounds.top > innerHeight) menu.hidePopover();
      else position(menu, trigger);
    });
  }
  document.addEventListener('scroll', repositionMenus, true);
  window.addEventListener('resize', repositionMenus);
})();
