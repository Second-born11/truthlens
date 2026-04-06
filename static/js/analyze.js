/* analyze.js */

const newsInput = document.getElementById('newsInput');
const charCount  = document.getElementById('charCount');
const wordCount  = document.getElementById('wordCount');

// ─── COUNTER ─────────────────────────────────────────────
newsInput.addEventListener('input', () => {
  const t = newsInput.value;
  charCount.textContent = t.length;
  wordCount.textContent = t.trim() === '' ? 0 : t.trim().split(/\s+/).length;
});

// ─── SAMPLES ─────────────────────────────────────────────
const samples = {
  real: `Scientists at Johns Hopkins University have published peer-reviewed research in the New England Journal of Medicine showing that a newly developed mRNA vaccine demonstrates 94.1% efficacy against severe outcomes. The clinical trial involved 43,448 participants across six countries over eighteen months. The data was independently verified by the FDA's advisory committee before the findings were released publicly. Researchers emphasized the importance of continued booster doses for at-risk populations and called for global distribution equity.`,
  fake: `BREAKING: Government secretly adds mind-control chemicals to tap water supply! Whistleblower reveals shocking truth that THEY don't want you to know! Scientists have PROVEN that the elites are using fluoride to dumb down the population and prevent them from seeing the REAL truth! Share this before they DELETE IT! The mainstream media will NEVER report this bombshell story! Wake up sheeple! Your water is being weaponized RIGHT NOW by the deep state! This is a cover-up of the century!`,
  mixed: `New study claims drinking coffee may prevent certain cancers, but experts remain divided. Some researchers suggest antioxidants in coffee could reduce specific cancer risks by up to 40%, while others warn the study was funded by a coffee industry group and involved only 200 participants over 3 months. The National Cancer Institute has not endorsed these findings and urges caution. Critics say the shocking claims are overstated and more research is needed before drawing any definitive conclusions.`
};

function loadSample(type) {
  newsInput.value = samples[type];
  newsInput.dispatchEvent(new Event('input'));
  newsInput.focus();
}

// ─── CLEAR ───────────────────────────────────────────────
function clearAll() {
  newsInput.value = '';
  charCount.textContent = '0';
  wordCount.textContent = '0';
  showState('idle');
  document.getElementById('resultCard').className = 'result-card';
}

// ─── STATE ───────────────────────────────────────────────
function showState(state) {
  document.getElementById('stateIdle').style.display       = state === 'idle'       ? 'flex'   : 'none';
  document.getElementById('stateProcessing').style.display = state === 'processing' ? 'flex'   : 'none';
  document.getElementById('stateResult').style.display     = state === 'result'     ? 'flex'   : 'none';
}

// ─── PROCESSING STEPS ANIMATION ──────────────────────────
function animateSteps(callback) {
  const ids = ['ps1','ps2','ps3','ps4'];
  ids.forEach(id => document.getElementById(id).className = 'pstep');
  let i = 0;
  const iv = setInterval(() => {
    if (i > 0) document.getElementById(ids[i-1]).className = 'pstep done';
    if (i < ids.length) { document.getElementById(ids[i]).className = 'pstep active'; i++; }
    else { clearInterval(iv); setTimeout(callback, 200); }
  }, 400);
}

// ─── ANALYZE ─────────────────────────────────────────────
async function analyzeNews() {
  const text = newsInput.value.trim();
  if (!text || text.length < 20) {
    alert('Please enter a longer news article (at least 20 characters).');
    return;
  }

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.querySelector('.btn-analyze-text').textContent = 'Analyzing...';

  showState('processing');
  document.getElementById('resultCard').className = 'result-card';

  animateSteps(async () => {
    try {
      const res  = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Server error');
      }
      displayResult(await res.json());
    } catch (e) {
      showState('idle');
      alert('❌ Error: ' + e.message + '\n\nMake sure:\n1. app.py is running\n2. You ran train_model.py first');
    } finally {
      btn.disabled = false;
      btn.querySelector('.btn-analyze-text').textContent = 'Analyze News';
    }
  });
}

// ─── DISPLAY ─────────────────────────────────────────────
function displayResult(data) {
  const { prediction, confidence, word_count, keywords, timestamp } = data;
  const isFake = prediction === 'FAKE';

  // Card border
  document.getElementById('resultCard').className = 'result-card ' + (isFake ? 'is-fake' : 'is-real');

  // Verdict banner
  const banner = document.getElementById('verdictBanner');
  banner.className = 'verdict-banner ' + (isFake ? 'is-fake' : 'is-real');

  const icon = document.getElementById('verdictIcon');
  icon.className = 'verdict-icon ' + (isFake ? 'fake' : 'real');
  icon.textContent = isFake ? '✗' : '✓';

  const word = document.getElementById('verdictWord');
  word.className = 'verdict-word ' + (isFake ? 'fake' : 'real');
  word.textContent = prediction;

  const big = document.getElementById('verdictConfBig');
  big.textContent = confidence + '%';
  big.style.color = isFake ? 'var(--accent-red)' : 'var(--accent-green)';

  // Meter
  document.getElementById('meterPct').textContent = confidence + '%';
  const fill = document.getElementById('meterFill');
  fill.className = 'meter-fill ' + (isFake ? 'fake' : 'real');
  fill.style.width = '0%';
  setTimeout(() => { fill.style.width = confidence + '%'; }, 80);

  // Keywords
  const kwContainer = document.getElementById('kwTags');
  kwContainer.innerHTML = '';
  if (keywords && keywords.length > 0) {
    keywords.forEach(kw => {
      const tag = document.createElement('span');
      tag.className = 'kw-tag'; tag.textContent = kw;
      kwContainer.appendChild(tag);
    });
  } else {
    const tag = document.createElement('span');
    tag.className = 'kw-tag neutral'; tag.textContent = 'No suspicious keywords detected';
    kwContainer.appendChild(tag);
  }

  // Meta
  const ts = new Date(timestamp).toLocaleTimeString();
  document.getElementById('resultMeta').innerHTML =
    `Model: Passive Aggressive Classifier &nbsp;·&nbsp; Vectorizer: TF-IDF<br/>` +
    `Words analyzed: ${word_count} &nbsp;·&nbsp; Time: ${ts}`;

  showState('result');
}

// ─── KEYBOARD SHORTCUT ───────────────────────────────────
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyzeNews();
});

// Init
showState('idle');