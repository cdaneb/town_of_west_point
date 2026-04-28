// Countdown timer: reads data-phase-end (Unix timestamp) from #phase-timer-container
(function () {
  const timerEl = document.getElementById('phase-timer');
  if (!timerEl) return;

  const container = document.getElementById('phase-timer-container');
  const endTs = container ? parseInt(container.dataset.phaseEnd, 10) : NaN;

  function tick() {
    if (isNaN(endTs) || endTs === 0) {
      timerEl.textContent = '--:--';
      return;
    }
    const remaining = Math.max(0, endTs - Math.floor(Date.now() / 1000));
    const m = Math.floor(remaining / 60).toString().padStart(2, '0');
    const s = (remaining % 60).toString().padStart(2, '0');
    timerEl.textContent = m + ':' + s;
  }

  tick();
  setInterval(tick, 1000);
})();

// Auto-scroll chat windows to bottom on new messages
(function () {
  function watchChat(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    new MutationObserver(function () {
      el.scrollTop = el.scrollHeight;
    }).observe(el, { childList: true });
  }
  watchChat('public-chat-log');
  watchChat('mafia-chat-log');
})();
