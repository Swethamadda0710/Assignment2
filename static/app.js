const fileInput = document.querySelector('#file-input');
const dropzone = document.querySelector('#dropzone');
const fileLabel = document.querySelector('#file-label');
const uploadForm = document.querySelector('#upload-form');
const uploadButton = document.querySelector('#upload-button');
const uploadStatus = document.querySelector('#upload-status');
const documentCard = document.querySelector('#document-card');
const docName = document.querySelector('#doc-name');
const docMeta = document.querySelector('#doc-meta');
const questionForm = document.querySelector('#question-form');
const questionInput = document.querySelector('#question-input');
const askButton = document.querySelector('#ask-button');
const answerArea = document.querySelector('#answer-area');
const readyLabel = document.querySelector('#ready-label');

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) fileLabel.textContent = fileInput.files[0].name;
});
['dragenter', 'dragover'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
  event.preventDefault(); dropzone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
  event.preventDefault(); dropzone.classList.remove('dragging');
}));
dropzone.addEventListener('drop', (event) => {
  if (event.dataTransfer.files[0]) { fileInput.files = event.dataTransfer.files; fileLabel.textContent = fileInput.files[0].name; }
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!fileInput.files[0]) { uploadStatus.textContent = 'Choose a PDF first.'; return; }
  uploadButton.disabled = true; uploadButton.querySelector('span').textContent = 'Indexing...'; uploadStatus.textContent = '';
  const body = new FormData(); body.append('file', fileInput.files[0]);
  try {
    const response = await fetch('/api/upload', { method: 'POST', body }); const data = await readResponse(response);
    if (!response.ok) throw new Error(data.error);
    documentCard.hidden = false; docName.textContent = data.name; docMeta.textContent = `${data.pages} pages · ${data.chunks} chunks`;
    questionInput.disabled = false; askButton.disabled = false; readyLabel.textContent = 'READY TO ASK'; uploadStatus.textContent = data.message;
  } catch (error) { uploadStatus.textContent = error.message; }
  finally { uploadButton.disabled = false; uploadButton.querySelector('span').textContent = 'Index document'; }
});

questionForm.addEventListener('submit', async (event) => {
  event.preventDefault(); const question = questionInput.value.trim(); if (!question) return;
  askButton.disabled = true; answerArea.innerHTML = '<div class="empty-state"><span class="empty-line"></span><p>Searching your document...</p><span class="empty-line"></span></div>';
  try {
    const response = await fetch('/api/ask', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question}) }); const data = await readResponse(response);
    if (!response.ok) throw new Error(data.error);
    const sources = data.sources.map((source) => `<div class="source"><b>0${source.rank}</b>${escapeHtml(source.text.slice(0, 260))}${source.text.length > 260 ? '...' : ''}</div>`).join('');
    answerArea.innerHTML = `<article class="answer-card"><div class="answer-label">ANSWER FROM YOUR DOCUMENT</div><p class="answer-text">${escapeHtml(data.answer)}</p><div class="confidence">MODEL CONFIDENCE · ${Math.round(data.confidence * 100)}%</div><div class="sources"><div class="sources-title">RETRIEVED PASSAGES</div>${sources}</div></article>`;
  } catch (error) { answerArea.innerHTML = `<div class="status">${escapeHtml(error.message)}</div>`; }
  finally { askButton.disabled = false; }
});
function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value; return div.innerHTML; }
async function readResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  const message = await response.text();
  throw new Error(`Server error (${response.status}): ${message.slice(0, 120)}`);
}
