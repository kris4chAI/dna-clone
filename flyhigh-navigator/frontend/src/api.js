const base = import.meta.env.VITE_API_BASE || ''

function store(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key)
    if (val === null) localStorage.removeItem(key)
    else localStorage.setItem(key, val)
  } catch { /* storage blocked */ }
  return null
}

let personaCode = store('kn_persona')
export const getPersona = () => personaCode
export const setPersona = (code) => { personaCode = code; store('kn_persona', code || null) }

export class ApiError extends Error {
  constructor(status, detail) { super(detail || `HTTP ${status}`); this.status = status }
}

async function req(method, path, body) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (personaCode) headers['X-Persona'] = personaCode
  const r = await fetch(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) {
    let detail
    try { detail = (await r.json()).detail } catch { /* not json */ }
    throw new ApiError(r.status, detail)
  }
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
  downloadUrl: (tid) => `${base}/api/kit/download/${tid}?persona_code=${encodeURIComponent(personaCode || '')}`,
}

export function sessionId() {
  let id = store('kn_session')
  if (!id) {
    id = 's_' + Math.random().toString(36).slice(2, 10)
    store('kn_session', id)
  }
  return id
}
