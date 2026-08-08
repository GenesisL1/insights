(() => {
  const menu = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-primary-nav]');
  if (menu && nav) {
    menu.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      menu.setAttribute('aria-expanded', String(open));
    });
  }

  const progress = document.querySelector('[data-reading-progress]');
  const updateProgress = () => {
    if (!progress) return;
    const doc = document.documentElement;
    const span = Math.max(1, doc.scrollHeight - doc.clientHeight);
    progress.style.width = `${Math.min(100, Math.max(0, (doc.scrollTop / span) * 100))}%`;
  };
  addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  const links = [...document.querySelectorAll('.toc-panel a[href^="#"]')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if ('IntersectionObserver' in window && sections.length) {
    const observer = new IntersectionObserver(entries => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      links.forEach(a => a.classList.toggle('is-active', a.getAttribute('href') === `#${visible.target.id}`));
    }, { rootMargin: '-18% 0px -72% 0px', threshold: 0 });
    sections.forEach(section => observer.observe(section));
  }

  document.querySelectorAll('pre.code-block').forEach(pre => {
    const button = document.createElement('button');
    button.className = 'copy-code';
    button.type = 'button';
    button.textContent = 'COPY';
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText.replace(/^COPY\s*/, ''));
        button.textContent = 'COPIED';
        setTimeout(() => { button.textContent = 'COPY'; }, 1400);
      } catch (_) {
        button.textContent = 'SELECT';
      }
    });
    pre.appendChild(button);
  });

  const copyLink = document.querySelector('[data-copy-link]');
  if (copyLink) {
    copyLink.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(location.href);
        copyLink.textContent = 'Link copied';
        setTimeout(() => { copyLink.textContent = 'Copy link'; }, 1400);
      } catch (_) {
        copyLink.textContent = 'Copy from address bar';
      }
    });
  }

  const lightbox = document.querySelector('[data-image-lightbox]');
  const zoomTriggers = [...document.querySelectorAll('[data-zoom-image]')];
  if (!lightbox || !zoomTriggers.length) return;

  const image = lightbox.querySelector('[data-lightbox-image]');
  const caption = lightbox.querySelector('[data-lightbox-caption]');
  const stage = lightbox.querySelector('[data-lightbox-stage]');
  const closeButton = lightbox.querySelector('[data-lightbox-close]');
  const zoomIn = lightbox.querySelector('[data-lightbox-zoom-in]');
  const zoomOut = lightbox.querySelector('[data-lightbox-zoom-out]');
  const resetButton = lightbox.querySelector('[data-lightbox-reset]');
  const controls = [...lightbox.querySelectorAll('button')];
  let scale = 1;
  let lastTrigger = null;
  let fallbackSrc = '';

  const setImageSize = () => {
    if (!image) return;
    const base = Math.min(window.innerWidth * 0.94, 1800);
    image.style.width = `${Math.round(base * scale)}px`;
    if (resetButton) resetButton.textContent = `${Math.round(scale * 100)}%`;
    if (stage) stage.classList.toggle('is-zoomed', scale > 1.01);
  };

  const setScale = value => {
    scale = Math.min(3, Math.max(0.75, value));
    setImageSize();
  };

  const openLightbox = trigger => {
    const sourceImage = trigger.querySelector('img');
    if (!sourceImage || !image || !caption) return;
    lastTrigger = trigger;
    fallbackSrc = trigger.dataset.fallbackSrc || sourceImage.currentSrc || sourceImage.src;
    image.src = trigger.dataset.fullSrc || sourceImage.currentSrc || sourceImage.src;
    image.alt = sourceImage.alt ? `Enlarged: ${sourceImage.alt}` : 'Enlarged article figure';
    caption.textContent = trigger.dataset.caption || '';
    lightbox.hidden = false;
    document.body.classList.add('lightbox-open');
    setScale(1);
    requestAnimationFrame(() => lightbox.classList.add('is-open'));
    closeButton?.focus();
  };

  const closeLightbox = () => {
    lightbox.classList.remove('is-open');
    document.body.classList.remove('lightbox-open');
    setTimeout(() => {
      lightbox.hidden = true;
      if (image) image.removeAttribute('src');
      lastTrigger?.focus();
      lastTrigger = null;
    }, 170);
  };

  zoomTriggers.forEach(trigger => trigger.addEventListener('click', () => openLightbox(trigger)));
  closeButton?.addEventListener('click', closeLightbox);
  zoomIn?.addEventListener('click', () => setScale(scale + 0.25));
  zoomOut?.addEventListener('click', () => setScale(scale - 0.25));
  resetButton?.addEventListener('click', () => setScale(1));

  image?.addEventListener('error', () => {
    if (fallbackSrc && image.src !== new URL(fallbackSrc, location.href).href) image.src = fallbackSrc;
  });

  lightbox.addEventListener('click', event => {
    if (event.target === lightbox || event.target === stage) closeLightbox();
  });

  addEventListener('resize', setImageSize, { passive: true });
  addEventListener('keydown', event => {
    if (lightbox.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeLightbox();
      return;
    }
    if (event.key === '+' || event.key === '=') setScale(scale + 0.25);
    if (event.key === '-') setScale(scale - 0.25);
    if (event.key === '0') setScale(1);
    if (event.key === 'Tab' && controls.length) {
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
})();
