import { useEffect, useState } from 'react'
import { api, sessionId } from '../api'
import { Chip, Empty } from '../components/ui'

const LOOPS = [['Build', [1, 2, 3, 4, 5, 6]], ['Review', [7, 8]], ['Fix', [9]]]

export default function Pursuit({ me, code, onSelect, onAsk, onNavigate }) {
  const [ov, setOv] = useState(null)
  const [stage, setStage] = useState(null)
  const [err, setErr] = useState(null)
  const [done, setDone] = useState(new Set())
  const [tab, setTab] = useState('stages')
  const sid = sessionId()

  useEffect(() => {
    api.get('/api/pursuit/overview').then(setOv)
    api.get(`/api/progress/${sid}`).then((r) => setDone(new Set(r.map((x) => `${x.stage_code}:${x.step_index}`))))
  }, [sid])
  useEffect(() => {
    if (!code) return
    setErr(null)
    api.get(`/api/pursuit/stages/${code}`).then(setStage).catch((e) => { setStage(null); setErr(e.message) })
  }, [code])

  if (!ov) return <div className="page">Loading…</div>
  const open = ov.stages.filter((s) => !s.locked)
  const key = (c, i) => `p-${c}:${i}`
  const nDone = (s) => (s.questions || []).filter((_, i) => done.has(key(s.code, i))).length
  const complete = (s) => s.questions?.length && nDone(s) === s.questions.length
  const total = open.reduce((a, s) => a + s.questions.length, 0)
  const totalDone = open.reduce((a, s) => a + nDone(s), 0)
  const idx = open.findIndex((s) => s.code === code)
  const prev = open[idx - 1], next = open[idx + 1]

  const toggle = async (i) => {
    const k = key(code, i), on = !done.has(k)
    const n = new Set(done); on ? n.add(k) : n.delete(k); setDone(n)
    await api.post('/api/progress', { session_id: sid, stage_code: `p-${code}`, step_index: i, done: on })
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Pursuit lifecycle · AI Native Sales Engineering</div>
          <h1>Nine gated stages, from RFP signal to orals</h1>
          <p className="lede">Agents draft, people decide: every stage closes with a gate signed by a named approver. {me.lens === 'delivery' && <b>Delivery lens: you can open the shared final stages; the others stay with sales.</b>}</p>
        </div>
        <div className="progress-card">
          <div className="pc-top"><span>Gate questions closed</span><b>{total ? Math.round((totalDone / total) * 100) : 0}%</b></div>
          <div className="bar"><div style={{ width: `${total ? (totalDone / total) * 100 : 0}%` }} /></div>
          <div className="pc-foot">{totalDone} of {total} · {open.filter(complete).length}/{open.length} stages ready for their gate</div>
        </div>
      </header>

      <div className="tabs" style={{ marginBottom: 12 }}>
        <button className={tab === 'stages' ? 'on' : ''} onClick={() => setTab('stages')}>Stages and gates</button>
        <button className={tab === 'method' ? 'on' : ''} onClick={() => setTab('method')}>Method, roles and dependencies</button>
      </div>

      {tab === 'stages' && <>
        <div className="flow-wrap">
          <div className="pflow">
            {LOOPS.map(([loop, nums]) => (
              <div key={loop} className={`ploop loop-${loop.toLowerCase()}`} style={{ flex: nums.length }}>
                <div className="ploop-head">{loop}{loop === 'Review' && <small> · stage 8 also runs the fix loop</small>}</div>
                <div className="ploop-nodes">
                  {ov.stages.filter((s) => nums.includes(s.num)).map((s) => (
                    <div key={s.code} className="pnode-cell">
                      <button disabled={s.locked} onClick={() => onSelect(s.code)}
                        className={`pnode ${s.code === code ? 'current' : ''} ${s.locked ? 'locked' : ''} ${!s.locked && complete(s) ? 'complete' : ''} ${s.critical ? 'critical' : 'lane'}`}>
                        <div className="node-top">
                          <span className="node-num">{!s.locked && complete(s) ? '✓' : s.num}</span>
                          {s.audience === 'shared' && <span className="shared-tag">Shared</span>}
                          {s.locked && <span className="lock-tag">Sales only</span>}
                        </div>
                        <div className="node-name">{s.name}</div>
                        <div className="node-lead">{s.lane}</div>
                      </button>
                      <div className="pgate"><span>{s.gate_code}</span></div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="plegend">
            <span><i className="crit" />Critical path: requirements → solution scope → effort → commercials → red team → submission</span>
            <span><i className="lanei" />Parallel lane</span>
            <span className="handover-pill" onClick={() => onNavigate('lifecycle')}>After G8 → implementation Discover</span>
          </div>
        </div>

        {err && <Empty>{err}</Empty>}
        {stage && (
          <div className="stage">
            <div className="coach">
              <div className="coach-step">Stage {stage.num} · {stage.gate_code}</div>
              <div className="coach-text"><b>{stage.name}.</b> Close the gate questions, draft the artefacts with the named skills, stamp anything unvalidated, then get <b>{stage.approvers}</b> to sign <b>{stage.gate_code} · {stage.gate}</b>.</div>
              <div className="coach-nav">
                <button className="btn ghost" disabled={!prev} onClick={() => onSelect(prev.code)}>← {prev?.name || 'Start'}</button>
                <button className="btn primary" disabled={!next} onClick={() => onSelect(next.code)}>{next ? `Next: ${next.name} →` : 'Last open stage'}</button>
              </div>
            </div>

            <div className="stage-head">
              <div>
                <div className="eyebrow">{stage.loop} loop · {stage.lane}</div>
                <h2>{stage.num}. {stage.name}</h2>
                <p>{stage.purpose}</p>
                {stage.audience === 'shared' && <div className="note shared-note"><b>Shared with delivery.</b> {stage.extra.shared_reason}</div>}
              </div>
              <div className="stage-facts">
                <div><span>Gate</span><b className="gate-text">{stage.gate_code} · {stage.gate}</b></div>
                <div><span>Approvers</span><b>{stage.approvers}</b></div>
                <div><span>Critical path</span><b>{stage.critical ? 'Yes, blocks the next stage' : 'No, parallel lane'}</b></div>
              </div>
            </div>

            <div className="stage-grid">
              <div className="col-left">
                <section className="panel">
                  <h4>Questions to close before {stage.gate_code}</h4>
                  <ol className="checklist">
                    {stage.questions.map((k, i) => (
                      <li key={i} className={done.has(key(code, i)) ? 'on' : ''} onClick={() => toggle(i)}>
                        <span className="box">{done.has(key(code, i)) ? '✓' : i + 1}</span>{k}
                      </li>
                    ))}
                  </ol>
                </section>
                <section className="panel">
                  <h4>Input tiers</h4>
                  <div className="tier must"><b>Must have</b><span>{stage.inputs.must}</span><small>Blocks the gate; missing caps a section at 89</small></div>
                  <div className="tier good"><b>Good to have</b><span>{stage.inputs.good}</span></div>
                  <div className="tier nice"><b>Nice to have</b><span>{stage.inputs.nice}</span></div>
                </section>
                <section className="panel">
                  <h4>Ask the guide</h4>
                  <div className="prompt-list">
                    {[`What does gate ${stage.gate_code} need?`, 'Which templates help here?', "What's next?"].map((p) => <button key={p} onClick={() => onAsk(p)}>{p}</button>)}
                  </div>
                </section>
              </div>

              <div className="col-right">
                <section className="panel">
                  <h4>Artefacts</h4>
                  <table className="tbl">
                    <thead><tr><th>Artefact</th><th>Owner</th><th>Format</th><th>Drafted by</th></tr></thead>
                    <tbody>
                      {stage.artefact_detail.map((a) => (
                        <tr key={a.id}><td><b>{a.name}</b>{a.system_of_record && <span className="sor">System of record</span>}</td><td>{a.owner}</td><td>{a.format}</td><td className="muted">{a.drafted_by}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  <h5>Stage outputs</h5>
                  <div className="chips">{stage.artefacts.map((a) => <Chip key={a} tone="out">{a}</Chip>)}</div>
                </section>

                <section className="panel">
                  <h4>Skills and tools</h4>
                  <div className="agents">
                    {stage.skill_detail.map((s) => (
                      <div key={s.id} className="agent skillcard">
                        <div className="agent-cap">{s.type} · stages {s.stages}</div>
                        <div className="agent-name mono">{s.name}</div>
                        <div className="agent-desc">{s.contributes}</div>
                      </div>
                    ))}
                  </div>
                  <div className="chips" style={{ marginTop: 10 }}>{stage.tools.map((t) => <Chip key={t} tone="tool">{t}</Chip>)}</div>
                </section>

                <section className="panel">
                  <h4>Templates and aids</h4>
                  <div className="tmpl-list">
                    {stage.templates.map((t) => (
                      <div key={t.id} className={`tmpl ${t.sample ? 'sample' : ''}`}>
                        <span className={`fmt fmt-${t.format}`}>{t.format}</span>
                        <div><b>{t.file}</b><small>{t.sample ? 'FlyHigh sample · client-confidential, stays in the pursuit folder' : `${t.sheets} editable sheet${t.sheets === 1 ? '' : 's'} in the kit`}</small></div>
                        {t.sheets > 0 && <button className="btn ghost" onClick={() => onNavigate('kit', String(t.id))}>Open in kit</button>}
                        {t.download && <a className="btn ghost" href={api.downloadUrl(t.id)}>Download</a>}
                      </div>
                    ))}
                    {!stage.templates.length && <span className="muted">No template for this stage.</span>}
                  </div>
                </section>

                {(stage.extra.links || stage.handover?.length > 0) && (
                  <div className="two">
                    {stage.extra.links && <section className="panel"><h4>Solution content</h4>
                      <div className="chips">{stage.extra.links.map(([v, l]) => <Chip key={v} tone="agent" onClick={() => onNavigate(v)}>{l} →</Chip>)}</div></section>}
                    {stage.handover?.length > 0 && <section className="panel"><h4>Hands over to implementation</h4>
                      <div className="chips">{stage.handover.map((h) => (
                        <Chip key={h.code} tone={h.locked ? 'default' : 'fw'} onClick={h.locked ? undefined : () => onNavigate('workflow', h.code)}>
                          {h.seq}. {h.name}{h.locked ? ' · delivery lens' : ' →'}
                        </Chip>))}</div></section>}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </>}

      {tab === 'method' && <Method ov={ov} lens={me.lens} />}
    </div>
  )
}

function Method({ ov, lens }) {
  const m = ov.method
  return (
    <>
      <div className="metrics">{m.targets.map(([v, l, t]) => <div key={l} className="metric"><b>{v}</b><span>{l}</span><em>{t}</em></div>)}</div>
      <div className="two">
        <section className="panel"><h4>Principles</h4><ol className="plain">{m.principles.map((p) => <li key={p}>{p}</li>)}</ol>
          <h5>Honest labels</h5><div className="chips">{m.stamps.map((s) => <Chip key={s} tone="ev">{s}</Chip>)}</div></section>
        <section className="panel"><h4>Measures, reviewed at every gate</h4>
          {m.measures.map(([k, v]) => <div key={k} className="shared-row"><b>{k}</b><span className="muted">{v}</span></div>)}</section>
      </div>
      <section className="panel"><h4>A smaller core team · 13 → 6 <span className="muted small" style={{ textTransform: 'none' }}>indicative, validate in the pilot</span></h4>
        <table className="tbl"><thead><tr><th>Role</th><th>Traditional</th><th>AI native</th></tr></thead>
          <tbody>{m.team.map(([r, a, b]) => <tr key={r}><td>{r}</td><td>{a}</td><td><b>{b}</b></td></tr>)}</tbody></table></section>
      <section className="panel"><h4>Roles and lenses</h4>
        <table className="tbl"><thead><tr><th>Role</th><th>Lens</th><th>Owns</th><th>Agent support</th></tr></thead>
          <tbody>{ov.roles.map((r) => <tr key={r.code}><td><b>{r.name}</b></td><td><span className={`lens-pill ${r.lens}`}>{r.lens}</span></td><td>{r.owns}</td><td className="muted">{r.agent_support}</td></tr>)}</tbody></table></section>
      <section className="panel"><h4>Dependencies: what blocks and what runs in parallel</h4>
        <table className="tbl"><thead><tr><th>Artefact</th><th>Needs first</th><th>Blocks</th><th>Runs in parallel with</th></tr></thead>
          <tbody>{ov.dependencies.map((d) => <tr key={d[0]}>{d.map((x, i) => <td key={i}>{i === 0 ? <b>{x}</b> : x}</td>)}</tr>)}</tbody></table></section>
      <div className="two">
        <section className="panel"><h4>Input tiers set the score ceiling</h4>
          <table className="tbl"><thead><tr><th>Inputs provided</th><th>Ceiling</th><th>Gate</th></tr></thead>
            <tbody>{m.tiers.map((t) => <tr key={t[0]}>{t.map((x, i) => <td key={i}>{x}</td>)}</tr>)}</tbody></table></section>
        <section className="panel"><h4>Guardrails: four lenses × build, review, fix</h4>
          <table className="tbl"><thead><tr><th>Lens</th><th>Build</th><th>Review</th><th>Fix</th></tr></thead>
            <tbody>{m.guardrails.map((t) => <tr key={t[0]}>{t.map((x, i) => <td key={i}>{i === 0 ? <b>{x}</b> : x}</td>)}</tr>)}</tbody></table></section>
      </div>
      {lens === 'sales' && (
        <div className="two">
          <section className="panel"><h4>Intelligence only people bring</h4>
            <table className="tbl"><thead><tr><th>Human input</th><th>Owner</th><th>Stages</th><th>Shapes</th></tr></thead>
              <tbody>{ov.human_inputs.map((d) => <tr key={d[0]}>{d.map((x, i) => <td key={i}>{i === 0 ? <b>{x}</b> : x}</td>)}</tr>)}</tbody></table></section>
          <section className="panel"><h4>Objections by party</h4>
            <table className="tbl"><thead><tr><th>Party</th><th>Objection</th><th>Owner</th><th>Evidence</th></tr></thead>
              <tbody>{ov.objections.map((d) => <tr key={d[0]}>{d.map((x, i) => <td key={i}>{i === 0 ? <b>{x}</b> : x}</td>)}</tr>)}</tbody></table></section>
        </div>
      )}
      <section className="panel"><h4>Artefact catalogue {lens === 'delivery' && <span className="muted small" style={{ textTransform: 'none' }}>filtered to shared stages</span>}</h4>
        <table className="tbl"><thead><tr><th>Artefact</th><th>Stage</th><th>Owner</th><th>Format</th><th>Drafted by</th></tr></thead>
          <tbody>{ov.artefacts.map((a) => <tr key={a.id}><td><b>{a.name}</b>{a.system_of_record && <span className="sor">System of record</span>}</td><td>{a.stages}</td><td>{a.owner}</td><td>{a.format}</td><td className="muted">{a.drafted_by}</td></tr>)}</tbody></table></section>
    </>
  )
}
