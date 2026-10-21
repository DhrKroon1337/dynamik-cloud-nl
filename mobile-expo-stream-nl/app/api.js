// app/api.js (NL): praat met jouw backend op Render.
// Vul hier je eigen Render-URL en hetzelfde SHARED_SECRET als op de server in.
const BASE_URL = 'https://<jouw-render-url>';
const SHARED_SECRET = '';

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${SHARED_SECRET}`,
    },
    body: JSON.stringify(body),
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* geen JSON */ }
  if (!res.ok) {
    // De backend stuurt een Nederlandse foutmelding mee in `detail`
    throw new Error((data && data.detail) || `Serverfout (${res.status})`);
  }
  return data;
}

// history: [{ role: 'user' | 'assistant', content: '...' }]
export async function sendToAgent(text, history = []) {
  const data = await post('/agent', { input_text: text, history });
  return data.response;
}

export async function callIntent(kind, idea) {
  return post('/intent', { kind, idea });
}
