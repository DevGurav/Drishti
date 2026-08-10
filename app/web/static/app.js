/* Drishti front-end.
 *
 * Interaction rules follow from the users: number keys select a mode, space captures,
 * every state change is announced through an aria-live region, and nothing depends on
 * seeing the screen. No external scripts -- the app must work with the network off.
 */
'use strict';

const els = {
  video: document.getElementById('video'),
  canvas: document.getElementById('canvas'),
  cameraError: document.getElementById('camera-error'),
  answer: document.getElementById('answer'),
  answerEn: document.getElementById('answer-en'),
  live: document.getElementById('live'),
  capture: document.getElementById('capture'),
  lang: document.getElementById('lang'),
  speak: document.getElementById('speak'),
  askRow: document.getElementById('ask-row'),
  question: document.getElementById('question'),
  player: document.getElementById('player'),
  modes: Array.from(document.querySelectorAll('.mode')),
};

const MODE_LABELS = {
  read: 'Read text', medicine: 'Medicine', currency: 'Money',
  scene: 'Describe scene', ask: 'Ask a question',
};

let selectedMode = null;
let busy = false;

/* Announce to screen readers. Clearing first forces re-announcement when the same
   text repeats -- otherwise identical consecutive answers are silently dropped. */
function announce(text) {
  els.live.textContent = '';
  window.setTimeout(() => { els.live.textContent = text; }, 60);
}

/* Waiting, announced.

   Answers take real time on a laptop CPU: about a minute for OCR modes and several for
   the VLM (measured 2026-08-11 -- see RISK-1). A sighted user watches a spinner. A blind
   user heard 'Working…' once and then nothing, with no way to tell a slow model from a
   crash, a dropped connection, or a capture key that never registered -- and the honest
   reaction to that silence is to press capture again, which queues a second slow request.

   So: say how long it should take before the wait starts, then check in periodically.
   Intervals widen rather than repeat on a fixed beat, because a message every few seconds
   stops being information and becomes noise you have to listen past. */
const EXPECTED_WAIT = {
  currency: 'a few seconds',
  medicine: 'about a minute',
  read: 'about a minute',
  scene: 'several minutes',
  ask: 'several minutes',
};

const WAIT_CHECKPOINTS = [15, 40, 80, 140, 220, 320];
let waitTimers = [];

function startedMessage(mode) {
  const expected = EXPECTED_WAIT[mode] || 'a moment';
  return `Working… this usually takes ${expected}.`;
}

function startWaitUpdates() {
  stopWaitUpdates();
  waitTimers = WAIT_CHECKPOINTS.map((seconds) =>
    window.setTimeout(() => {
      /* Only the live region, not the visible answer: replacing the answer text would
         wipe the expectation the user is waiting against. */
      announce(`Still working. ${seconds} seconds so far.`);
    }, seconds * 1000),
  );
}

function stopWaitUpdates() {
  waitTimers.forEach(window.clearTimeout);
  waitTimers = [];
}

function setAnswer(text, { error = false, busyState = false, english = null } = {}) {
  els.answer.textContent = text;
  els.answer.classList.toggle('is-error', error);
  els.answer.classList.toggle('is-busy', busyState);

  if (english && english !== text) {
    els.answerEn.textContent = english;
    els.answerEn.hidden = false;
  } else {
    els.answerEn.hidden = true;
  }
  announce(text);
}

function selectMode(mode) {
  selectedMode = mode;
  els.modes.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  els.askRow.hidden = mode !== 'ask';
  els.capture.disabled = false;

  if (mode === 'ask') {
    els.question.focus();
    announce('Ask a question mode. Type your question, then press capture.');
  } else {
    announce(`${MODE_LABELS[mode]} selected. Press space to capture.`);
  }
}

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1600 } },
      audio: false,
    });
    els.video.srcObject = stream;
    announce('Camera ready. Choose a mode using keys 1 to 5.');
  } catch (err) {
    /* Without a camera the app is still usable by an examiner reviewing the UI, so
       fail with an explanation rather than a blank screen. */
    els.cameraError.textContent =
      `Camera unavailable (${err.name}). Grant camera permission and reload.`;
    els.cameraError.hidden = false;
    setAnswer('Camera unavailable. Grant permission and reload the page.', { error: true });
  }
}

function grabFrame() {
  const { videoWidth: w, videoHeight: h } = els.video;
  if (!w || !h) return null;
  els.canvas.width = w;
  els.canvas.height = h;
  els.canvas.getContext('2d').drawImage(els.video, 0, 0, w, h);
  return new Promise((resolve) => els.canvas.toBlob(resolve, 'image/jpeg', 0.9));
}

async function capture() {
  if (busy || !selectedMode) return;

  if (selectedMode === 'ask' && !els.question.value.trim()) {
    setAnswer('Please type a question first.', { error: true });
    els.question.focus();
    return;
  }

  const blob = await grabFrame();
  if (!blob) {
    setAnswer('No camera image yet. Wait a moment and try again.', { error: true });
    return;
  }

  busy = true;
  els.capture.disabled = true;
  setAnswer(startedMessage(selectedMode), { busyState: true });
  startWaitUpdates();

  const form = new FormData();
  form.append('image', blob, 'capture.jpg');
  form.append('mode', selectedMode);
  form.append('lang', els.lang.value);
  form.append('question', els.question.value);
  form.append('speak', String(els.speak.checked));
  /* OCR script and spoken language are different choices.

     Medicine strips print the drug name and expiry in Latin script even on Marathi
     packaging, so OCR stays English there while the answer is spoken in the chosen
     language. Read mode is the opposite: a Marathi signboard or newspaper is *printed*
     in Devanagari, so the recogniser has to match the page, not the listener.

     Read mode previously sent no ocr_lang at all, which meant Devanagari went through the
     Latin recogniser and came back as transliterated noise -- no error, just confident
     gibberish read aloud to someone who cannot check it (DEC-045). */
  if (selectedMode === 'medicine') form.append('ocr_lang', 'en');
  else if (selectedMode === 'read') form.append('ocr_lang', els.lang.value);

  try {
    const res = await fetch('/api/answer', { method: 'POST', body: form });
    const data = await res.json();

    if (!data.ok) {
      setAnswer(data.error || 'Something went wrong. Try again.', { error: true });
    } else {
      setAnswer(data.text_out || data.text_en, { english: data.text_en });
      if (data.audio_url) {
        els.player.src = data.audio_url;
        els.player.play().catch(() => { /* autoplay blocked; the text is already announced */ });
      }
    }
  } catch (err) {
    setAnswer('Could not reach the app. Is the server still running?', { error: true });
  } finally {
    /* Before re-enabling capture: a pending "still working" firing after the answer has
       been read out would talk over it and suggest the request is still going. */
    stopWaitUpdates();
    busy = false;
    els.capture.disabled = false;
  }
}

els.modes.forEach((btn) => {
  btn.setAttribute('aria-pressed', 'false');
  btn.addEventListener('click', () => selectMode(btn.dataset.mode));
});
els.capture.addEventListener('click', capture);

document.addEventListener('keydown', (e) => {
  const typing = e.target === els.question;

  if (!typing && e.key >= '1' && e.key <= '5') {
    const btn = els.modes[Number(e.key) - 1];
    if (btn) { e.preventDefault(); selectMode(btn.dataset.mode); }
    return;
  }
  if (e.key === ' ' && !typing) { e.preventDefault(); capture(); return; }
  if (e.key === 'Enter' && typing) { e.preventDefault(); capture(); }
});

els.lang.addEventListener('change', () => {
  announce(`Answers will be spoken in ${els.lang.selectedOptions[0].textContent}.`);
});

startCamera();
