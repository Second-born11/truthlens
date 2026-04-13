/* analyze.js — Text + File Upload */

// ─── STATE ───────────────────────────────────────────────
let currentMode = 'text';
let selectedFiles = { audio: null, video: null, document: null, image: null };

// ─── MODE SWITCHER ────────────────────────────────────────
function switchMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

  const modes = ['text','audio','video','document','image'];
  modes.forEach(m => {
    const el = document.getElementById('mode' + m.charAt(0).toUpperCase() + m.slice(1));
    if (el) el.style.display = m === mode ? 'flex' : 'none';
  });

  clearAll();
}

// ─── TEXT MODE ────────────────────────────────────────────
const newsInput = document.getElementById('newsInput');
const charCount = document.getElementById('charCount');
const wordCount = document.getElementById('wordCount');

if (newsInput) {
  newsInput.addEventListener('input', () => {
    const t = newsInput.value;
    charCount.textContent = t.length;
    wordCount.textContent = t.trim() === '' ? 0 : t.trim().split(/\s+/).length;
  });
}

const samples = {
  real: `Scientists at Johns Hopkins University have published peer-reviewed research in the New England Journal of Medicine showing that a newly developed mRNA vaccine demonstrates 94.1% efficacy against severe outcomes. The clinical trial involved 43,448 participants across six countries over eighteen months. The data was independently verified by the FDA advisory committee before the findings were released publicly.`,
  fake: `BREAKING: Government secretly adds mind-control chemicals to tap water supply! Whistleblower reveals shocking truth that THEY don't want you to know! Scientists have PROVEN that the elites are using fluoride to dumb down the population! Share this before they DELETE IT! The mainstream media will NEVER report this bombshell story! Wake up sheeple! Your water is being weaponized RIGHT NOW by the deep state!`,
  mixed: `New study claims drinking coffee may prevent certain cancers, but experts remain divided. Some researchers suggest antioxidants in coffee could reduce specific cancer risks by up to 40%, while others warn the study was funded by a coffee industry group. The National Cancer Institute has not endorsed these findings. Critics say the shocking claims are overstated.`
};

function loadSample(type) {
  newsInput.value = samples[type];
  newsInput.dispatchEvent(new Event('input'));
  newsInput.focus();
}

// ─── FILE SELECT ──────────────────────────────────────────
function handleFileSelect(input, mode) {
  const file = input.files[0];
  if (!file) return;
  selectedFiles[mode] = file;

  document.getElementById('dropAudio' in document.getElementById('drop' + cap(mode)) ? 'drop' + cap(mode) : 'drop' + cap(mode)).style.display = 'none';
  const dropEl = document.getElementById('drop' + cap(mode));
  if (dropEl) dropEl.style.display = 'none';

  document.getElementById('fileName' + cap(mode)).textContent = file.name + ' (' + formatSize(file.size) + ')';
  document.getElementById('fileSelected' + cap(mode)).style.display = 'flex';
  document.getElementById('analyzeBtn' + cap(mode)).disabled = false;
}

function removeFile(mode) {
  selectedFiles[mode] = null;
  const fileInput = document.getElementById('file' + cap(mode));
  if (fileInput) fileInput.value = '';
  document.getElementById('fileSelected' + cap(mode)).style.display = 'none';
  document.getElementById('drop' + cap(mode)).style.display = 'flex';
  document.getElementById('analyzeBtn' + cap(mode)).disabled = true;
  showState('idle');
  document.getElementById('resultCard').className = 'result-card';
}

function cap(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Drag and drop support
['audio','video','document','image'].forEach(mode => {
  const dropEl = document.getElementById('drop' + cap(mode));
  if (!dropEl) return;
  dropEl.addEventListener('dragover', e => { e.preventDefault(); dropEl.classList.add('dragover'); });
  dropEl.addEventListener('dragleave', () => dropEl.classList.remove('dragover'));
  dropEl.addEventListener('drop', e => {
    e.preventDefault();
    dropEl.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const fakeInput = { files: [file] };
    handleFileSelect(fakeInput, mode);
    selectedFiles[mode] = file;
  });
});

// ─── CLEAR ───────────────────────────────────────────────
function clearAll() {
  if (currentMode === 'text') {
    if (newsInput) { newsInput.value = ''; newsInput.dispatchEvent(new Event('input')); }
  } else {
    removeFile(currentMode);
  }
  showState('idle');
  document.getElementById('resultCard').className = 'result-card';
}

// ─── STATE MANAGER ────────────────────────────────────────
function showState(state) {
  document.getElementById('stateIdle').style.display       = state === 'idle'       ? 'flex' : 'none';
  document.getElementById('stateProcessing').style.display = state === 'processing' ? 'flex' : 'none';
  document.getElementById('stateResult').style.display     = state === 'result'     ? 'flex' : 'none';
}

// ─── PROCESSING STEPS ────────────────────────────────────
function animateSteps(labels, callback) {
  const ids = ['ps1','ps2','ps3','ps4'];
  ids.forEach((id, i) => {
    const el = document.getElementById(id);
    el.className = 'pstep';
    el.textContent = labels[i] || el.textContent;
  });
  let i = 0;
  const iv = setInterval(() => {
    if (i > 0) document.getElementById(ids[i-1]).className = 'pstep done';
    if (i < ids.length) { document.getElementById(ids[i]).className = 'pstep active'; i++; }
    else { clearInterval(iv); setTimeout(callback, 200); }
  }, 500);
}

// ─── ANALYZE TEXT ─────────────────────────────────────────
async function analyzeNews() {
  const text = newsInput.value.trim();
  if (!text || text.length < 20) {
    alert('Please enter a longer news article (at least 20 characters).'); return;
  }
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.querySelector('.btn-analyze-text').textContent = 'Analyzing...';
  showState('processing');
  document.getElementById('procTitle').textContent = 'Analyzing text...';

  animateSteps([
    '⚙️ Preprocessing text',
    ' TF-IDF vectorizing',
    '🤖 Running classifier',
    ' Calculating confidence'
  ], async () => {
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Server error'); }
      displayResult(await res.json());
    } catch (e) {
      showState('idle');
      alert('❌ Error: ' + e.message + '\n\nMake sure app.py is running and train_model.py was run.');
    } finally {
      btn.disabled = false;
      btn.querySelector('.btn-analyze-text').textContent = 'Analyze Text';
    }
  });
}

// ─── ANALYZE FILE ─────────────────────────────────────────
async function analyzeFile(mode) {
  const file = selectedFiles[mode];
  if (!file) { alert('Please select a file first.'); return; }

  const btn = document.getElementById('analyzeBtn' + cap(mode));
  btn.disabled = true;
  btn.querySelector('.btn-analyze-text').textContent = 'Processing...';
  showState('processing');

  const stepLabels = {
    audio:    [' Reading audio file', ' Transcribing speech', '🤖 Running classifier', ' Calculating confidence'],
    video:    [' Extracting audio', ' Transcribing speech', '🤖 Running classifier', ' Calculating confidence'],
    document: [' Reading document', ' Extracting text', '🤖 Running classifier', ' Calculating confidence'],
    image:    ['️ Reading image', ' Running OCR scan', '🤖 Running classifier', ' Calculating confidence'],
  };
  document.getElementById('procTitle').textContent = 'Processing ' + mode + '...';

  animateSteps(stepLabels[mode] || ['⚙️ Processing',' Extracting','🤖 Classifying',' Scoring'], async () => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Upload failed');
      displayResult(data);

    } catch (e) {
      showState('idle');
      alert('❌ Error: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.querySelector('.btn-analyze-text').textContent = btn.querySelector('.btn-analyze-text').textContent.replace('Processing...', btn.dataset.label || 'Analyze');
    }
  });
}

// ─── DISPLAY RESULT ──────────────────────────────────────
function displayResult(data) {
  const { prediction, confidence, word_count, keywords, timestamp, source_type, extracted_text } = data;
  const isFake = prediction === 'FAKE';

  document.getElementById('resultCard').className = 'result-card ' + (isFake ? 'is-fake' : 'is-real');

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

  // Source badge
  const sourceIcons = { text:'', mp4:'', mp3:'', wav:'', m4a:'', pdf:'', docx:'', doc:'', jpg:'️', jpeg:'️', png:'️' };
  const sIcon = sourceIcons[source_type] || '';
  document.getElementById('sourceBadge').textContent = sIcon + ' ' + (source_type || 'text').toUpperCase();

  // Meter
  document.getElementById('meterPct').textContent = confidence + '%';
  const fill = document.getElementById('meterFill');
  fill.className = 'meter-fill ' + (isFake ? 'fake' : 'real');
  fill.style.width = '0%';
  setTimeout(() => { fill.style.width = confidence + '%'; }, 80);

  // Extracted text preview (only for file uploads)
  const previewEl = document.getElementById('extractedPreview');
  if (extracted_text && source_type !== 'text') {
    document.getElementById('extractedText').textContent = extracted_text;
    previewEl.style.display = 'block';
  } else {
    previewEl.style.display = 'none';
  }

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
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && currentMode === 'text') analyzeNews();
});

// Init
showState('idle');