(() => {
  const navToggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');
  const languageSwitch = document.querySelector('[data-language-switch]');
  const languageToast = document.querySelector('[data-language-toast]');
  const header = document.querySelector('[data-header]');

  navToggle?.addEventListener('click', () => {
    const isOpen = nav?.classList.toggle('is-open') ?? false;
    navToggle.setAttribute('aria-expanded', String(isOpen));
    navToggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
  });

  languageSwitch?.addEventListener('click', () => {
    languageToast?.classList.add('is-visible');
    window.clearTimeout(window.languageToastTimer);
    window.languageToastTimer = window.setTimeout(() => {
      languageToast?.classList.remove('is-visible');
    }, 2800);
  });

  nav?.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      nav.classList.remove('is-open');
      navToggle?.setAttribute('aria-expanded', 'false');
    });
  });

  document.querySelectorAll('[data-current-year]').forEach((node) => {
    node.textContent = String(new Date().getFullYear());
  });

  const updateHeader = () => {
    header?.classList.toggle('is-scrolled', window.scrollY > 120);
  };
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  document.querySelectorAll('[data-compare]').forEach((compare) => {
    const range = compare.querySelector('.compare-range');
    range?.addEventListener('input', () => {
      compare.style.setProperty('--compare-position', `${range.value}%`);
    });
  });

  const filters = document.querySelectorAll('[data-gallery-filter]');
  const galleryItems = document.querySelectorAll('[data-gallery-item]');
  filters.forEach((filter) => {
    filter.addEventListener('click', () => {
      const activeCategory = filter.dataset.galleryFilter;
      filters.forEach((item) => item.classList.toggle('is-active', item === filter));
      galleryItems.forEach((item) => {
        const categories = (item.dataset.category || '').split(' ');
        item.hidden = activeCategory !== 'all' && !categories.includes(activeCategory);
      });
    });
  });

  const dialog = document.querySelector('[data-gallery-dialog]');
  const dialogImage = dialog?.querySelector('[data-dialog-image]');
  const dialogTitle = dialog?.querySelector('[data-dialog-title]');
  document.querySelectorAll('[data-gallery-open]').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      if (!dialog || !dialogImage || !dialogTitle) return;
      dialogImage.src = trigger.dataset.galleryOpen || '';
      dialogImage.alt = trigger.dataset.galleryTitle || 'Gallery study';
      dialogTitle.textContent = trigger.dataset.galleryTitle || '';
      dialog.showModal();
    });
  });
  dialog?.querySelector('[data-dialog-close]')?.addEventListener('click', () => dialog.close());
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });

  const reveals = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    reveals.forEach((item) => observer.observe(item));
  } else {
    reveals.forEach((item) => item.classList.add('is-visible'));
  }
})();
