/* Shared states for actual lists: CoreUI placeholders initially, quiet updates later. */
(() => {
  function create(container, {content = container, shape = 'cards', status} = {}) {
    const feedback = status || document.createElement('p');
    feedback.classList.add('list-feedback', 'small', 'text-body-secondary');
    feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
    if (!status) container.append(feedback);
    const skeleton = document.createElement('div');
    skeleton.className = `list-skeleton skeleton-${shape} placeholder-glow`;
    skeleton.setAttribute('aria-hidden', 'true'); skeleton.hidden = true;
    for (let index = 0; index < 6; index++) {
      const block = document.createElement('div'); block.className = 'skeleton-block';
      block.innerHTML = '<span class="placeholder col-8"></span><span class="placeholder col-5"></span>';
      skeleton.append(block);
    }
    content.before(skeleton);
    function begin(initial = false) {
      feedback.classList.remove('text-danger');
      container.classList.remove('has-load-error'); container.setAttribute('aria-busy', 'true');
      content.hidden = initial; skeleton.hidden = !initial;
      feedback.innerHTML = initial ? '<span class="visually-hidden">Cargando contenido…</span>' : '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Actualizando…';
    }
    function finish(message = '') {
      content.hidden = false; skeleton.hidden = true; container.setAttribute('aria-busy', 'false');
      container.classList.toggle('has-load-error', Boolean(message));
      feedback.classList.toggle('text-danger', Boolean(message));
      feedback.textContent = message;
    }
    return {begin, finish};
  }
  window.EppLoading = {create};
})();
