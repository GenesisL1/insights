(() => {
  const desktopToc = document.querySelector('.toc .toc-links');
  const article = document.querySelector('.article-main');
  if (desktopToc && article && !document.querySelector('.mobile-toc')) {
    const details = document.createElement('details');
    details.className = 'mobile-toc';
    const summary = document.createElement('summary');
    summary.textContent = 'Article contents';
    details.appendChild(summary);
    const clone = desktopToc.cloneNode(true);
    details.appendChild(clone);
    const anchor = article.querySelector('.meta-row') || article.querySelector('.article-deck');
    if (anchor) anchor.insertAdjacentElement('afterend', details);
    clone.querySelectorAll('a').forEach(a => a.addEventListener('click', () => { details.open = false; }));
  }

  const tocLinks = [...document.querySelectorAll('.toc a[href^="#"]')];
  const sections = tocLinks.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if ('IntersectionObserver' in window && sections.length) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          tocLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + entry.target.id));
        }
      });
    }, { rootMargin: '-18% 0px -68% 0px' });
    sections.forEach(section => observer.observe(section));
  }

  const lightbox = document.querySelector('.lightbox');
  if (lightbox) {
    const image = lightbox.querySelector('img');
    document.querySelectorAll('[data-lightbox]').forEach(button => {
      button.addEventListener('click', () => {
        image.src = button.dataset.lightbox;
        image.alt = button.querySelector('img')?.alt || 'Expanded publication image';
        lightbox.classList.add('open');
        document.body.style.overflow = 'hidden';
      });
    });
    const close = () => {
      lightbox.classList.remove('open');
      document.body.style.overflow = '';
      image.removeAttribute('src');
    };
    lightbox.querySelector('.lightbox-close')?.addEventListener('click', close);
    lightbox.addEventListener('click', event => { if (event.target === lightbox) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && lightbox.classList.contains('open')) close(); });
  }
})();
