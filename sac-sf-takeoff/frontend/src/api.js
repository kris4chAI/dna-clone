const base = import.meta.env.VITE_API_BASE || ''

async function req(method, path, body) {
  const r = await fetch(base + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status}`)
  return r.json()
}

export const api = {
  get: (p) => req('GET', p),
  post: (p, b) => req('POST', p, b),
  put: (p, b) => req('PUT', p, b),
  del: (p) => req('DELETE', p),
  create: (table, data) => req('POST', `/api/curate/${table}`, data),
  update: (table, id, data) => req('PUT', `/api/curate/${table}/${id}`, data),
  remove: (table, id) => req('DELETE', `/api/curate/${table}/${id}`),
}

export function sessionId() {
  let id
  try { id = localStorage.getItem('kn_session') } catch { /* storage blocked */ }
  if (!id) {
    id = 's_' + Math.random().toString(36).slice(2, 10)
    try { localStorage.setItem('kn_session', id) } catch { /* ignore */ }
  }
  return id
}
