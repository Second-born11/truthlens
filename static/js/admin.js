async function refreshStats() {
  try {
    await fetch('/api/stats');
    location.reload();
  } catch (e) {
    alert('Could not refresh: ' + e.message);
  }
}

function confirmClear() {
  document.getElementById('clearModal').classList.add('open');
}

function closeModal() {
  document.getElementById('clearModal').classList.remove('open');
}

async function clearHistory() {
  try {
    const res = await fetch('/api/clear-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin'
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Server error');
    }

    closeModal();
    location.reload();

  } catch (e) {
    closeModal();
    alert('❌ Could not clear history: ' + e.message);
  }
}

// Close modal when clicking outside the box
document.getElementById('clearModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});