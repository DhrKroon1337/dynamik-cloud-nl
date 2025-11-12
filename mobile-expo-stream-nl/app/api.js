// app/api.js (NL)
const BASE_URL = 'https://<jouw-render-url>';
const SHARED_SECRET = '';

export async function sendToAgent(text, {stream=false} = {}) {
  if (stream) {
    const res = await fetch(`${BASE_URL}/agent_stream`, { method:'POST', headers:{'Content-Type':'application/json', ...(SHARED_SECRET?{'Authorization':`Bearer ${SHARED_SECRET}`}:{})}, body: JSON.stringify({ input_text: text }) });
    if (!res.ok || !res.body) throw new Error('Stream error');
    return res.body.getReader();
  } else {
    const res = await fetch(`${BASE_URL}/agent`, { method:'POST', headers:{'Content-Type':'application/json', ...(SHARED_SECRET?{'Authorization':`Bearer ${SHARED_SECRET}`}:{})}, body: JSON.stringify({ input_text: text }) });
    const data = await res.json();
    return data.response;
  }
}
export async function callIntent(kind, idea) {
  const res = await fetch(`${BASE_URL}/intent`, { method:'POST', headers:{'Content-Type':'application/json', ...(SHARED_SECRET?{'Authorization':`Bearer ${SHARED_SECRET}`}:{})}, body: JSON.stringify({ kind, idea }) });
  return res.json();
}
