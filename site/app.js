(() => {
  const toggle = document.querySelector('.nav-toggle');
  const navigation = document.querySelector('.site-nav');
  if (toggle && navigation) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      navigation.classList.toggle('open', !expanded);
    });
    navigation.addEventListener('click', (event) => {
      if (event.target instanceof HTMLAnchorElement) {
        toggle.setAttribute('aria-expanded', 'false');
        navigation.classList.remove('open');
      }
    });
  }

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(button.dataset.copy || '');
        button.textContent = 'Copied';
      } catch {
        button.textContent = 'Select commands';
      }
      window.setTimeout(() => { button.textContent = original; }, 1800);
    });
  });
})();
