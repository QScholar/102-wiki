(() => {
  const modes = ['system', 'light', 'dark'];
  const details = {system:['跟随系统','monitor'],light:['浅色模式','sun'],dark:['夜间模式','moon-star']};
  let mode = 'system';
  try { mode = localStorage.getItem('yuna-wiki-theme') || 'system'; } catch (error) {}
  if (!modes.includes(mode)) mode = 'system';

  const apply = () => {
    if (mode === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = mode;
    const dark = mode === 'dark' || (mode === 'system' && matchMedia('(prefers-color-scheme:dark)').matches);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#181927' : '#f8f9fd');
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.querySelector('span').textContent = details[mode][0];
      button.querySelector('i,svg')?.setAttribute('data-lucide', details[mode][1]);
    });
    if (window.lucide) window.lucide.createIcons();
  };

  document.querySelectorAll('[data-theme-toggle]').forEach(button => button.addEventListener('click', () => {
    mode = modes[(modes.indexOf(mode) + 1) % modes.length];
    try { mode === 'system' ? localStorage.removeItem('yuna-wiki-theme') : localStorage.setItem('yuna-wiki-theme', mode); } catch (error) {}
    apply();
  }));
  matchMedia('(prefers-color-scheme:dark)').addEventListener('change', () => { if (mode === 'system') apply(); });

  const lightbox = document.getElementById('lightbox');
  document.querySelectorAll('[data-lightbox-src]').forEach(button => button.addEventListener('click', () => {
    lightbox.querySelector('img').src = button.dataset.lightboxSrc;
    lightbox.classList.add('active');
    lightbox.querySelector('button').focus();
  }));
  const closeLightbox = () => lightbox?.classList.remove('active');
  lightbox?.addEventListener('click', event => { if (event.target === lightbox || event.target.closest('[data-lightbox-close]')) closeLightbox(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeLightbox(); });
  apply();
})();
