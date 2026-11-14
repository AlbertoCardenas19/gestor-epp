/* Shared states for actual lists: delay feedback so fast responses do not flash. */
(() => {
  function create(container, {content = container, shape = 'cards', status, delay = 180} = {}) {
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
    let timer;
    let pending = false;
    function begin(initial = false) {
      clearTimeout(timer); pending = true;
      feedback.classList.remove('text-danger');
      container.classList.remove('has-load-error'); container.setAttribute('aria-busy', 'true');
      container.classList.remove('is-loading'); content.hidden = false; skeleton.hidden = true;
      feedback.textContent = '';
      timer = setTimeout(() => {
        if (!pending) return;
        container.classList.add('is-loading'); content.hidden = initial; skeleton.hidden = !initial;
        feedback.innerHTML = initial ? '<span class="visually-hidden">Cargando contenido…</span>' : '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Actualizando…';
      }, delay);
    }
    function finish(message = '') {
      pending = false; clearTimeout(timer);
      content.hidden = false; skeleton.hidden = true; container.setAttribute('aria-busy', 'false');
      container.classList.remove('is-loading');
      container.classList.toggle('has-load-error', Boolean(message));
      feedback.classList.toggle('text-danger', Boolean(message));
      feedback.textContent = message;
    }
    return {begin, finish, cancel: () => finish()};
  }
  window.EppLoading = {create};
})();
