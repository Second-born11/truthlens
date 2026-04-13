let allArticles = [];
let currentFilter = 'all';

async function loadNews() {
  document.getElementById('statusText').textContent = 'Loading...';
  const grid = document.getElementById('newsGrid');
  grid.innerHTML = '';
  for (let i = 0; i < 6; i++) {
    const sk = document.createElement('div');
    sk.className = 'news-skeleton';
    grid.appendChild(sk);
  }

  try {
    // Add a timeout so it doesn't hang forever
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const res  = await fetch('/api/news', { signal: controller.signal });
    clearTimeout(timeout);

    if (!res.ok) throw new Error('Server returned ' + res.status);

    const data = await res.json();
    allArticles = data.articles || [];

    document.getElementById('statusText').textContent =
      data.source === 'live'
        ? '🟢 Live data'
        : '🟡 Offline mode';

    renderCards();

  } catch (e) {
    console.error('News load error:', e);
    document.getElementById('newsGrid').innerHTML =
      `<div style="font-family:var(--font-mono);font-size:0.8rem;color:var(--text-muted);padding:20px 0;">
        ⚠️ Could not load news feed.<br/>
        Make sure <strong>app.py</strong> is running, then refresh the page.
      </div>`;
    document.getElementById('statusText').textContent = ' Connection error';
  }
}

function renderCards() {
  const grid = document.getElementById('newsGrid');
  grid.innerHTML = '';

  if (!allArticles.length) {
    grid.innerHTML = '<div style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);">No articles found.</div>';
    return;
  }

  allArticles.forEach(art => {
    const card = document.createElement('div');
    card.className = 'news-card';
    card.dataset.pred = art.prediction;

    if (currentFilter !== 'all' && art.prediction !== currentFilter) {
      card.classList.add('filtered-out');
    }

    const conf = art.confidence > 0 ? art.confidence + '%' : '—';
    const link = art.url && art.url !== '#'
      ? `<a href="${art.url}" target="_blank" class="nc-link" onclick="event.stopPropagation()">Read original article →</a>`
      : '';

    card.innerHTML = `
      <div class="nc-source">${esc(art.source)}</div>
      <div class="nc-title">${esc(art.title)}</div>
      <div class="nc-snippet">${esc(art.snippet || '')}</div>
      <div class="nc-footer">
        <span class="nc-badge ${art.prediction}">${art.prediction}</span>
        <span class="nc-conf">Confidence: ${conf}</span>
      </div>
      ${link}
    `;

    // Click to go to analyze page with this text
    card.addEventListener('click', () => {
      sessionStorage.setItem('analyzeText', art.title + '\n\n' + (art.snippet || ''));
      window.location.href = '/analyze';
    });

    grid.appendChild(card);
  });
}

function setFilter(btn, filter) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = filter;
  renderCards();
}

function esc(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── INIT ────────────────────────────────────────────────
loadNews();