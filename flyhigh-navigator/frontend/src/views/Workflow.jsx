import { useEffect, useMemo, useState } from 'react'
import { api, sessionId } from '../api'
import { Chip } from '../components/ui'

const GATE_AFTER = { discover: 'G1', design: 'G2', release: 'G3' }

export default function Workflow({ code, onSelect, onAsk, onNavigate }) {
  const [stages, setStages] = useState([])
  const [phases, setPhases] = useState([])
  const [stage, setStage] = useState(null)
  const [done, setDone] = useState(new Set())
  const sid = sessionId()

  useEffect(() => {
    api.get('/api/stages').then(setStages)
    api.get('/api/phases').then(setPhases)
    api.get(`/api/progress/${sid}`).then((r) => setDone(new Set(r.map((x) => `${x.stage_code}:${x.step_index}`))))
  }, [sid])
  useEffect(() => { if (code) api.get(`/api/stages/${code}`).then(setStage) }, [code])

  const stepsDone = (s) => (s.key_steps || []).filter((_, i) => done.has(`${s.code}:${i}`)).length
  const isComplete = (s) => s.key_steps?.length && stepsDone(s) === s.key_steps.length
  const totalSteps = stages.reduce((a, s) => a + (s.key_steps?.length || 0), 0)
  const totalDone = stages.reduce((a, s) => a + stepsDone(s), 0)
  const idx = stages.findIndex((s) => s.code === code)
  const prev = stages[idx - 1]
  const next = stages[idx + 1]

  const toggle = async (i) => {
    const key = `${code}:${i}`
    const on = !done.has(key)
    const n = new Set(done); on ? n.add(key) : n.delete(key); setDone(n)
    await api.post('/api/progress', { session_id: sid, stage_code: code, step_index: i, done: on })
  }
  const completeAll = async () => {
    const n = new Set(done)
    for (let i = 0; i < stage.key_steps.length; i++) {
      n.add(`${code}:${i}`)
      api.post('/api/progress', { session_id: sid, stage_code: code, step_index: i, done: true })
    }
    setDone(n)
    if (next) onSelect(next.code)
  }

  const phaseSpans = useMemo(() => phases.map((p) => ({ ...p, count: stages.filter((s) => s.phase === p.num).length })), [phases, stages])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Guided workflow</div>
          <h1>From discovery to monitoring</h1>
          <p className="lede">Ten human-gated steps. Each one names who leads, which agents draft the work, the skills they invoke, the tools they run on and the evidence that clears the gate.</p>
        </div>
        <div className="progress-card">
          <div className="pc-top"><span>Your progress</span><b>{totalSteps ? Math.round((totalDone / totalSteps) * 100) : 0}%</b></div>
          <div className="bar"><div style={{ width: `${totalSteps ? (totalDone / totalSteps) * 100 : 0}%` }} /></div>
          <div className="pc-foot">{totalDone} of {totalSteps} checklist items · {stages.filter(isComplete).length}/{stages.length} stages</div>
        </div>
      </header>

      {/* ---------- Flow map ---------- */}
      <div className="flow-wrap">
        {[[1, 2], [3, 4, 5]].map((row, ri) => {
          const rowPhases = phaseSpans.filter((p) => row.includes(p.num) && p.count > 0)
          const rowStages = stages.filter((s) => row.includes(s.phase))
          if (!rowStages.length) return null
          return (
        <div key={ri} className={`flow ${ri ? 'flow-2' : 'flow-1'}`} style={{ gridTemplateColumns: `repeat(${rowStages.length}, minmax(118px, 1fr))` }}>
          {rowPhases.map((p) => (
            <div key={p.num} className={`phase phase-${p.num}`} style={{ gridColumn: `span ${p.count}` }}>
              <b>{p.num} · {p.name}</b><span>{p.months}</span>
            </div>
          ))}
          {rowStages.map((s) => {
            const pct = s.key_steps?.length ? stepsDone(s) / s.key_steps.length : 0
            return (
              <div key={s.code} className="node-cell">
                <button className={`node ${s.code === code ? 'current' : ''} ${isComplete(s) ? 'complete' : ''}`} onClick={() => onSelect(s.code)}>
                  <div className="node-top">
                    <span className="node-num">{isComplete(s) ? '✓' : s.seq}</span>
                    <svg className="ring" viewBox="0 0 36 36"><circle cx="18" cy="18" r="15" /><circle cx="18" cy="18" r="15" className="ring-fg" style={{ strokeDasharray: `${pct * 94.2} 94.2`, opacity: pct ? 1 : 0 }} /></svg>
                  </div>
                  <div className="node-name">{s.name}</div>
                  <div className="node-lead">{s.lead_role}</div>
                  <div className="node-meta"><span>{s.agent_count} agents</span><span>{s.skill_count} skills</span></div>
                </button>
                {GATE_AFTER[s.code] && <span className="gate" title={s.gate}><span>{GATE_AFTER[s.code]}</span></span>}
              </div>
            )
          })}
        </div>
          )
        })}
        <div className="loop"><span>↺ Build learnings flow back to Discover · every artefact versioned in the repo</span></div>
      </div>

      {/* ---------- Stage detail ---------- */}
      {stage && (
        <div className="stage">
          <div className="coach">
            <div className="coach-step">Step {stage.seq} of {stages.length}</div>
            <div className="coach-text">
              <b>{stage.name}.</b> Work through the checklist on the left, review who does what on the right, then move on. {stage.gate.startsWith('G') ? <>This step closes with human gate <b>{stage.gate}</b>.</> : <>Exit: <b>{stage.gate}</b>.</>}
            </div>
            <div className="coach-nav">
              <button className="btn ghost" disabled={!prev} onClick={() => onSelect(prev.code)}>← {prev?.name || 'Start'}</button>
              <button className="btn primary" disabled={!next} onClick={() => onSelect(next.code)}>{next ? `Next: ${next.name} →` : 'Done'}</button>
            </div>
          </div>

          <div className="stage-head">
            <div>
              <div className="eyebrow">Phase {stage.phase} · slide {stage.slide}</div>
              <h2>{stage.seq}. {stage.name}</h2>
              <p>{stage.summary}</p>
            </div>
            <div className="stage-facts">
              <div><span>Led by</span><b>{stage.lead_role}</b></div>
              <div><span>Mode</span><b>{stage.mode}</b></div>
              <div><span>Gate</span><b className={stage.gate.startsWith('G') ? 'gate-text' : ''}>{stage.gate}</b></div>
            </div>
          </div>

          <div className="stage-grid">
            <div className="col-left">
              <section className="panel">
                <h4>Your checklist</h4>
                <ol className="checklist">
                  {stage.key_steps.map((k, i) => (
                    <li key={i} className={done.has(`${code}:${i}`) ? 'on' : ''} onClick={() => toggle(i)}>
                      <span className="box">{done.has(`${code}:${i}`) ? '✓' : i + 1}</span>{k}
                    </li>
                  ))}
                </ol>
                {!isComplete(stage) && <button className="btn primary block" onClick={completeAll}>Mark stage complete{next ? ' and continue' : ''}</button>}
              </section>
              <section className="panel">
                <h4>Ask the guide</h4>
                <div className="prompt-list">
                  {(stage.extra?.prompts || []).concat(['What\'s next?']).map((p) => <button key={p} onClick={() => onAsk(p)}>{p}</button>)}
                </div>
              </section>
              <section className="panel">
                <h4>Outputs</h4>
                <div className="chips">{stage.outputs.map((o) => <Chip key={o} tone="out">{o}</Chip>)}</div>
                {stage.extra?.evidence && <><h5>Evidence at the gate</h5><div className="chips">{stage.extra.evidence.map((o) => <Chip key={o} tone="ev">{o}</Chip>)}</div></>}
              </section>
            </div>

            <div className="col-right">
              {stage.extra?.metrics && (
                <div className="metrics">{stage.extra.metrics.map(([k, v]) => <div key={k} className="metric"><b>{v}</b><span>{k}</span></div>)}</div>
              )}

              {stage.extra?.steps && (
                <section className="panel">
                  <h4>Sequence</h4>
                  <div className="seq">
                    {stage.extra.steps.map((st, i) => (
                      <div key={i} className="seq-step">
                        <div className="seq-num">{i + 1}</div>
                        <div className="seq-body">
                          <div className="seq-name">{st.name}{st.track && <Chip tone={st.track === 'Greenfield' ? 'green' : st.track === 'Both' ? 'default' : 'purple'}>{st.track}</Chip>}</div>
                          {st.detail && <div className="seq-detail">{st.detail}</div>}
                          <div className="chips">
                            {st.snowflake.map((x) => <Chip key={x} tone="snow">{x}</Chip>)}
                            <Chip tone="agent">{st.agent}</Chip>
                            {(st.skills || []).map((x) => <Chip key={x} tone="skill">{x}</Chip>)}
                            {st.framework && <Chip tone="fw">{st.framework}</Chip>}
                            {st.output && <Chip tone="out">→ {st.output}</Chip>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <section className="panel">
                <h4>Agents · skills · tools <span className="legend"><Chip tone="agent">Agent</Chip><Chip tone="skill">Skill</Chip><Chip tone="tool">Tool</Chip></span></h4>
                <div className="agents">
                  {stage.agents.map((a) => (
                    <div key={a.id} className="agent">
                      <div className="agent-cap">{a.category}</div>
                      <div className="agent-name">{a.name}</div>
                      <div className="agent-desc">{a.description}</div>
                      <div className="chips">
                        {a.skills.map((s) => <Chip key={s.id} tone="skill">{s.name}</Chip>)}
                        {a.tools.map((t) => <Chip key={t.id} tone="tool" title={t.category}>{t.name}</Chip>)}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {stage.extra?.harnesses && (
                <section className="panel">
                  <h4>Deterministic harnesses <span className="muted">same spec, same result, every run</span></h4>
                  <div className="pipeline">{['Requirement', '9 agents', 'Canonical HIR', 'Gate', 'Harness layer', 'Adapters · Snowflake'].map((x, i) => <div key={x} className="pipe"><span>{i + 1}</span>{x}</div>)}</div>
                  <div className="chips">{stage.extra.harnesses.map((h) => <Chip key={h} tone="fw">{h}</Chip>)}</div>
                </section>
              )}

              {stage.extra?.test_types && (
                <section className="panel"><h4>Test types · run every wave</h4>
                  <div className="chips">{stage.extra.test_types.map((h) => <Chip key={h} tone="ev">{h}</Chip>)}</div></section>
              )}

              <div className="two">
                <section className="panel">
                  <h4>Frameworks · accelerators</h4>
                  {stage.frameworks.length ? <div className="chips">{stage.frameworks.map((f) => <Chip key={f.id} tone="fw" onClick={() => onNavigate('catalog', 'framework')}>{f.name}</Chip>)}</div> : <span className="muted">Agent-generated step</span>}
                </section>
                <section className="panel">
                  <h4>Snowflake components</h4>
                  {stage.snowflake.length ? <div className="chips">{stage.snowflake.map((f) => <Chip key={f.id} tone="snow">{f.name}</Chip>)}</div> : <span className="muted">—</span>}
                </section>
              </div>

              {stage.extra?.references && (
                <section className="panel"><h4>Proven in BI migrations</h4>
                  <div className="chips">{stage.extra.references.map((h) => <Chip key={h}>{h}</Chip>)}</div></section>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
