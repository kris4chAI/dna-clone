import { useEffect, useState } from 'react'
import { api } from '../api'
import { Md } from '../components/ui'

export default function Quality({ me, onNavigate }) {
  const [d, setD] = useState(null)
  const [sel, setSel] = useState(null)
  useEffect(() => { api.get('/api/quality').then((r) => { setD(r); const ed = r.sections.filter((x) => x.editable); setSel((ed.length ? ed : r.sections).slice().sort((a, b) => a.baseline - b.baseline)[0].id) }) }, [])
  if (!d) return <div className="page">Loading…</div>
  const s = d.sections.find((x) => x.id === sel)
  const passing = d.sections.filter((x) => x.passes).length

  const score = async (crit, val) => setD(await api.put(`/api/quality/${s.id}/score`, { criterion: crit, score: val, evidence: s.scores[crit]?.evidence || null }))
  const evidence = async (crit, text) => setD(await api.put(`/api/quality/${s.id}/score`, { criterion: crit, score: s.scores[crit]?.score ?? 0, evidence: text }))
  const must = async (i, met) => setD(await api.put(`/api/quality/${s.id}/musthave`, { idx: i, met }))
  const reset = async () => setD(await api.del(`/api/quality/${s.id}`))

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Response quality · stage 8 red team · shared</div>
          <h1>Every section earns 90 or escalates</h1>
          <p className="lede">Fourteen independently buildable sections, each scored on ten weighted criteria. Points = weight × score ÷ 4. A section passes at 90 only with every must-have met; a missing must-have caps it at 89. {me.lens === 'delivery' && <b>Delivery reviewers score the shared sections: engineering, delivery plan, and team and governance.</b>}</p>
        </div>
        <div className="gauge">
          <svg viewBox="0 0 120 70"><path d="M10 60 A50 50 0 0 1 110 60" className="g-bg" /><path d="M10 60 A50 50 0 0 1 110 60" className="g-fg" style={{ strokeDasharray: `${(d.overall / 100) * 157} 157` }} /></svg>
          <b>{d.overall}</b><span>overall · baseline {d.baseline} · target 90</span><small>{passing}/14 sections pass</small>
        </div>
      </header>

      <div className="q-split">
        <section className="panel">
          <h4>Sections</h4>
          <div className="sec-list">
            {d.sections.map((x) => (
              <button key={x.id} className={`sec ${x.id === sel ? 'on' : ''}`} onClick={() => setSel(x.id)}>
                <span className="sec-num">{x.num}</span>
                <span className="sec-main">
                  <b>{x.name}</b>
                  <small>slides {x.slides} · {x.owner_lens === 'shared' ? 'sales + delivery' : 'sales'}{!x.editable ? ' · view only' : ''}</small>
                  <span className="sec-bar"><i style={{ width: `${x.current}%` }} className={x.passes ? 'pass' : x.current >= 80 ? 'near' : 'low'} /><em style={{ left: '90%' }} /></span>
                </span>
                <span className={`sec-score ${x.passes ? 'pass' : ''}`}>{x.current}<small>{x.scored ? 'scored' : 'baseline'}</small></span>
              </button>
            ))}
          </div>
        </section>

        {s && (
          <section className="panel scorer">
            <div className="scorer-head">
              <div>
                <div className="eyebrow">Section {s.num} · slides {s.slides} · weight {s.weight.toFixed(1)}%</div>
                <h2>{s.name}</h2>
                <p className="muted">{s.proves}</p>
              </div>
              <div className={`big-score ${s.passes ? 'pass' : ''}`}><b>{s.current}</b><small>{s.scored ? 'your score' : `baseline ${s.baseline}`}</small></div>
            </div>
            {!s.editable && <div className="note">This section is scored by the sales team. You can view it; the shared sections are yours to score.</div>}

            <h5>Must-haves</h5>
            <div className="musts">
              {s.must_haves.map((m, i) => (
                <label key={i} className={`must ${s.musthave_met[i] ? 'on' : ''}`}>
                  <input type="checkbox" disabled={!s.editable} checked={s.musthave_met[i]} onChange={(e) => must(i, e.target.checked)} />{m}
                </label>
              ))}
            </div>

            <h5>Rubric · 0 absent · 1 generic · 2 partial · 3 strong with one gap · 4 complete with evidence</h5>
            <div className="crit-list">
              {d.criteria.map((c) => {
                const v = s.scores[c.code]?.score
                return (
                  <div key={c.code} className="crit">
                    <div className="crit-name"><b>{c.name}</b><small>{c.weight} pts · {c.full_marks}</small></div>
                    <div className="seg">
                      {[0, 1, 2, 3, 4].map((n) => <button key={n} disabled={!s.editable} className={v === n ? 'on' : ''} onClick={() => score(c.code, n)}>{n}</button>)}
                    </div>
                    <div className="crit-pts">{v != null ? (c.weight * v / 4).toFixed(2) : '—'}</div>
                    {v >= 3 && <input className="evidence" disabled={!s.editable} defaultValue={s.scores[c.code]?.evidence || ''} placeholder="Cite the slide and words that earn a 3 or 4" onBlur={(e) => evidence(c.code, e.target.value)} />}
                  </div>
                )
              })}
            </div>

            <div className="two" style={{ marginTop: 12 }}>
              <div className="note"><b>Missing at baseline:</b> {s.missing}</div>
              <div className="note"><b>Highest-leverage fixes:</b> {s.fixes}<br /><b>Blocked by:</b> {s.blocked_by}</div>
            </div>
            {s.editable && s.scored && <button className="btn ghost" onClick={reset}>Reset to baseline</button>}
            <LoopPanel key={s.id} s={s} onNavigate={onNavigate} />
          </section>
        )}
      </div>
    </div>
  )
}

function LoopPanel({ s, onNavigate }) {
  const [r, setR] = useState(null)
  const [fixes, setFixes] = useState('')
  const call = async (record) => setR(await api.post('/api/skills/rfp-section-loop/run', { params: { section: String(s.num), record: record ? 'yes' : 'no', fixes } }))
  useEffect(() => { call(false) }, []) // eslint-disable-line
  return (
    <div className="loop-panel">
      <h5>Loop (rfp-section-loop) · generate → score → revise, max four rounds</h5>
      {r && <><b className={`loop-status st-${r.loop.status.split(' ')[0].toLowerCase()}`}>{r.loop.status}</b><Md text={Object.values(r.files)[0].split('\n').slice(4).join('\n')} compact /></>}
      {s.editable && <div className="run-bar">
        <input placeholder="Fixes made this round" value={fixes} onChange={(e) => setFixes(e.target.value)} style={{ flex: 1 }} />
        <button className="btn primary" onClick={() => call(true)}>Record round</button>
        <button className="link" onClick={() => onNavigate('skills', 'rfp-section-builder')}>Section brief →</button>
      </div>}
    </div>
  )
}
