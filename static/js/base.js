/* base.js — shared across all pages */

// ─── HAMBURGER MENU ───────────────────────────────────────
const hamburger  = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobileMenu');

if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
  });
  // close on outside click
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
    }
  });
}

// ─── SCROLL FADE ANIMATIONS ───────────────────────────────
const scrollObs = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });
document.querySelectorAll('.fade-up').forEach(el => scrollObs.observe(el));

// ─── AUTO-DISMISS FLASH MESSAGES ─────────────────────────
document.querySelectorAll('.flash').forEach(flash => {
  setTimeout(() => {
    flash.style.transition = 'opacity .4s, transform .4s';
    flash.style.opacity = '0';
    flash.style.transform = 'translateX(20px)';
    setTimeout(() => flash.remove(), 400);
  }, 4000);
});