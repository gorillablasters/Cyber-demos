const form = document.querySelector('#chat');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const buttons = document.querySelectorAll('button');
function add(text, role) {
  const article = document.createElement('article');
  article.className = role;
  article.textContent = text;
  messages.append(article);
  article.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
async function request(path, payload) {
  buttons.forEach(button => button.disabled = true);
  form.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    if (path === '/reset') messages.replaceChildren();
    add(data.reply, 'assistant');
  } catch (error) { add(error.message, 'error'); }
  finally { buttons.forEach(button => button.disabled = false); form.removeAttribute('aria-busy'); input.focus(); }
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  add(text, 'user'); input.value = '';
  await request('/chat', {message: text});
});
document.querySelector('#reset').addEventListener('click', () => request('/reset', {}));

const documentInput = document.querySelector('#document');
document.querySelector('#upload').addEventListener('click', async () => {
  const file = documentInput.files[0];
  if (!file || !file.name.toLowerCase().endsWith('.md') || file.size > 16384) {
    add('Choose a Markdown (.md) file of at most 16 KB.', 'error'); return;
  }
  try {
    const content = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer());
    await request('/upload', {filename: file.name, content});
    documentInput.value = '';
  } catch { add('The file must contain UTF-8 text.', 'error'); }
});
