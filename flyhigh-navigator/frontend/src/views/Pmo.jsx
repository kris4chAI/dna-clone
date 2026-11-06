import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { Chip, Editor, Empty, Md } from '../components/ui'

/* PMO lens: the AI Native Delivery Playbook as a working program office. */

const Tabs = ({ tabs, tab, setTab }) => (
  <div className="tabs" style={{ margin: '4px 0 14px' }}>
    {tabs.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}
  </div>
)
const Head = ({ eyebrow, title, lede, children }) => (
  <header className="page-head">
    <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{lede && <p className="lede">{lede}</p>}</div>
    {children && <div className="status-pills">{children}</div>}
  </header>
)
const useLoad = (path, deps = []) => {
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  const reload = () => api.get(path).then(setD).catch((e) => setErr(e.message))
  useEffect(() => { reload() }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return [d, setD, reload, err]
}
const Table = ({ cols, rows, keys }) => (
  <div className="md-table"><table className="tbl">
    <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{keys.map((k) => <td key={k}>{typeof k === 'function' ? k(r) : r[k]}</td>)}</tr>)}</tbody>
  </table></div>
)
const BAND_TONE = { Ready: 'g', 'Ready with remediation': 'a', 'Not ready yet': 'r', 'Not scored yet': 'n' }
const RAG = { green: 'g', amber: 'a', red: 'r', na: 'n' }
const Rag = ({ s, children }) => <span className={`pm-rag ${RAG[s] || s}`}>{children || (s === 'na' ? 'not set' : s)}</span>

/* ---------------------------------------------------------------- Playbook */
export function Playbook({ onNavigate }) {
  const [d] = useLoad('/api/pmo/playbook')
  const [tab, setTab] = useState('primer')
  const [sec, setSec] = useState('why')
  if (!d) return <div className="page">Loading…</div>
  const p = d.primer.find((x) => x.code === sec) || d.primer[0]
  return (
    <div className="page">
      <Head eyebrow="Program office · AI Native Delivery Playbook" title="Deliver trusted data on date, with agents doing the work and people owning the gates"
        lede="The playbook for AI-native Snowflake data modernization: why delivery is changing, the four archetypes, the harness that keeps agents governed, and the practices that retire legacy on the licence date.">
        <span className="spill"><b>4</b> archetypes</span><span className="spill"><b>3</b> human gates</span><span className="spill"><b>7</b> accelerators</span>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['primer', 'Primer'], ['arch', 'Archetypes'], ['harness', 'Harness'], ['practices', 'Ten practices'], ['worked', 'FlyHigh worked example'], ['refs', 'Artefacts and references']]} />

      {tab === 'primer' && (
        <div className="split">
          <aside className="list">
            {d.primer.map((x) => (
              <button key={x.code} className={`list-item ${x.code === sec ? 'on' : ''}`} onClick={() => setSec(x.code)}>
                <b>{x.title}</b>{x.summary && <small>{x.summary}</small>}
              </button>
            ))}
            <div className="list-group">Niche Accelerate services</div>
            {d.accelerators.map((a) => <div key={a.name} className="pm-acc"><b>{a.name}</b><small>{a.what}</small></div>)}
          </aside>
          <section className="detail panel pm-doc"><h2>{p.title}</h2><Md text={p.body} /></section>
        </div>
      )}

      {tab === 'arch' && (
        <div className="pm-grid2">
          {d.archetypes.map((a) => (
            <section key={a.key} className="panel pm-arch">
              <div className="pm-arch-top"><Chip tone="purple">{a.lc}</Chip><span className="muted small">{a.tag}</span></div>
              <h2>{a.title}</h2>
              <p className="muted">{a.q}</p>
              <p>{a.summary}</p>
              <h5>Method</h5><p className="pm-flow">{a.method}</p>
              <div className="pm-cols">
                <div><h5>Signals</h5><ul>{a.chars.map((x) => <li key={x}>{x}</li>)}</ul></div>
                <div><h5>Artefacts</h5><ul>{a.artefacts.map((x) => <li key={x}>{x}</li>)}</ul></div>
              </div>
              <h5>Tools</h5><div className="chips">{a.tools.map((x) => <Chip key={x} tone="snow">{x}</Chip>)}</div>
              <div className="note" style={{ marginTop: 10 }}><b>FlyHigh:</b> {a.example}</div>
              <button className="btn ghost" style={{ marginTop: 10 }} onClick={() => onNavigate('roadmap', a.key)}>Execute activities →</button>
            </section>
          ))}
        </div>
      )}

      {tab === 'harness' && (
        <>
          <div className="two">
            <section className="panel"><h4>What it is</h4><ul>{d.harness.what.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section className="panel"><h4>Why it matters</h4><ul>{d.harness.why.map((x) => <li key={x}>{x}</li>)}</ul></section>
          </div>
          <section className="panel"><h4>Delivery harness flow</h4><Flow steps={d.harness.flow} /></section>
          <section className="panel"><h4>Data Harness flow</h4><Flow steps={d.harness.dataFlow} /></section>
          <div className="two">
            <section className="panel"><h4>Toolkit</h4><Table cols={['Tool', 'What', 'Used for', 'Control']} rows={d.harness.tools} keys={[0, 1, 2, 3]} /></section>
            <section className="panel"><h4>Anatomy</h4>{d.harness.blocks.map(([t, x]) => <div key={t} className="shared-row"><b>{t}</b><span className="muted">{x}</span></div>)}</section>
          </div>
          <section className="panel"><h4>Agents and skills by lane</h4>
            <div className="pm-grid4">{d.harness.skills.map(([lane, owner, agents]) => (
              <div key={lane} className="pm-lane"><b>{lane}</b><small>{owner}</small>{agents.map(([a, s]) => <div key={a}><span>{a}</span><code>{s}</code></div>)}</div>
            ))}</div>
          </section>
        </>
      )}

      {tab === 'practices' && (
        <div className="pm-grid2">
          {d.practices.map((x, i) => <section key={x.title} className="panel pm-practice"><span className="pm-num">{i + 1}</span><div><b>{x.title}</b><p className="muted">{x.detail}</p></div></section>)}
        </div>
      )}

      {tab === 'worked' && <Worked w={d.worked} />}

      {tab === 'refs' && (
        <>
          {d.artefacts.map((g) => (
            <section key={g.group} className="panel"><h4>{g.group}</h4><Table cols={['Artefact', 'What it holds', 'FlyHigh source']} rows={g.items} keys={['name', 'what', 'source']} /></section>
          ))}
          <section className="panel"><h4>Reference programs</h4>
            <div className="pm-grid2">{d.cases.map((c) => (
              <div key={c.k} className="pm-case"><Chip tone="purple">{c.arch}</Chip><b>{c.title}</b><p className="muted small">{c.sum}</p>
                <div className="pm-stats">{c.stats.map(([v, l]) => <div key={l}><b>{v}</b><small>{l}</small></div>)}</div></div>
            ))}</div>
            <p className="muted small">Outcomes from reference programs are targets or reported results of those programs; size FlyHigh's own figures in discovery and prove them in the pilot.</p>
          </section>
        </>
      )}
    </div>
  )
}

function Flow({ steps }) {
  return (
    <div className="pm-flowrow">
      {steps.map((s) => (
        <div key={s.label} className={`pm-step ${s.gate ? 'gate' : ''}`}>
          <b>{s.label}</b><small className="muted">{s.who}</small><span>{s.what}</span><em>→ {s.out}</em>
        </div>
      ))}
    </div>
  )
}

function Worked({ w }) {
  const n = w.months.length
  return (
    <>
      <section className="panel">
        <h2>{w.title}</h2><p>{w.summary}</p>
        <div className="pm-stats big">{w.stats.map(([v, l]) => <div key={l}><b>{v}</b><small>{l}</small></div>)}</div>
      </section>
      <section className="panel"><h4>How the archetypes map</h4><Table cols={['Track', 'Archetype', 'Scope', 'Why now']} rows={w.tracks} keys={[0, 1, 2, 3]} /></section>
      <section className="panel"><h4>Ten-month integrated plan</h4>
        <div className="pm-gantt" style={{ gridTemplateColumns: `180px repeat(${n}, 1fr)` }}>
          <span />{w.months.map((m, i) => <span key={m} className="pm-gm">M{i + 1}<small>{m}</small></span>)}
          {w.timeline.map(([label, a, b]) => (
            <div key={label} className="pm-grow" style={{ display: 'contents' }}>
              <span className="pm-gl">{label}</span>
              {w.months.map((m, i) => <span key={m} className={`pm-gc ${i + 1 >= a && i + 1 <= b ? 'on' : ''} ${/cut|go-live/i.test(label) ? 'hot' : /Track B/.test(label) ? 'b' : /Parallel/.test(label) ? 'par' : ''}`} />)}
            </div>
          ))}
        </div>
      </section>
      <div className="three">
        <section className="panel"><h4>Pods</h4><ul>{w.pods.map((x) => <li key={x}>{x}</li>)}</ul></section>
        <section className="panel"><h4>Decisions that shaped delivery</h4><ul>{w.decisions.map((x) => <li key={x}>{x}</li>)}</ul></section>
        <section className="panel"><h4>Risks managed</h4>{w.risks.map(([r, m, o]) => <div key={r} className="shared-row"><b>{r}</b><span className="muted">{m} · {o}</span></div>)}</section>
      </div>
      <p className="muted small">Planning figures, not results.</p>
    </>
  )
}

/* ---------------------------------------------------------------- Readiness */
export function Readiness({ onNavigate }) {
  const [track, setTrack] = useState('')
  const [d, setD] = useState(null)
  const load = (t) => api.get(`/api/pmo/readiness${t ? `?track=${encodeURIComponent(t)}` : ''}`).then((r) => { setD(r); setTrack(r.track) })
  useEffect(() => { load('') }, [])
  if (!d) return <div className="page">Loading…</div>
  const answer = async (qid, score) => {
    const r = await api.put(`/api/pmo/readiness/${encodeURIComponent(track)}/${qid}`, { score })
    setD((o) => ({ ...o, ...r, tracks: o.tracks.map((t) => (t.track === track ? { ...t, overall: r.overall } : t)) }))
  }
  const addTrack = async () => {
    const name = prompt('Name the track (for example: Track C · Cortex AI)')
    if (name) { const r = await api.post('/api/pmo/readiness/tracks', { name }); setD(r); setTrack(r.track) }
  }
  let dim = ''
  return (
    <div className="page">
      <Head eyebrow="Program office · Readiness and qualification" title="Is each track ready for AI-native delivery?"
        lede="Score the 17 questions with the client team. Five weighted dimensions give the band: 75% and above is ready, 50% and above is ready with remediation. Lagging dimensions turn into owned remediation actions before Sprint 0 ends.">
        <button className="btn ghost" onClick={() => onNavigate('skills', 'pmo-readiness-scorecard')}>Run the readiness skill</button>
      </Head>
      <div className="pm-tracks">
        {d.tracks.map((t) => <button key={t.track} className={`pm-track ${t.track === track ? 'on' : ''}`} onClick={() => load(t.track)}><b>{t.track}</b><small>{t.overall}%</small></button>)}
        <button className="pm-track add" onClick={addTrack}>+ Add track</button>
      </div>
      <div className="pm-ready">
        <section className="panel">
          {d.questions.map((x) => {
            const h = x.dim !== dim ? <h5 key={`h${x.id}`}>{(dim = x.dim)} · weight {d.dims.find((k) => k.dim === x.dim).weight}%</h5> : null
            return (
              <div key={x.id}>{h}
                <div className="pm-q">
                  <span className="pm-qn">{x.id + 1}</span>
                  <div className="pm-qt">{x.question}</div>
                  <div className="pm-scores">{x.levels.map((lv, i) => (
                    <button key={i} title={lv} className={`pm-sc s${i} ${x.score === i ? 'on' : ''}`} onClick={() => answer(x.id, i)}>{i}</button>
                  ))}</div>
                </div>
                {x.score != null && <div className="pm-qlv muted small">{x.levels[x.score]}</div>}
              </div>
            )
          })}
        </section>
        <aside>
          <section className="panel pm-gauge-card">
            <Gauge pct={d.overall} tone={BAND_TONE[d.band]} />
            <div><b className={`pm-band ${BAND_TONE[d.band]}`}>{d.band}</b><small className="muted">{d.answered} of {d.total} answered</small></div>
          </section>
          <section className="panel">
            <h4>Dimensions</h4>
            {d.dims.map((k) => (
              <div key={k.dim} className="pm-dim">
                <div><span>{k.dim}</span><b>{k.pct}%</b></div>
                <i><em style={{ width: `${k.pct}%` }} className={k.pct >= 75 ? 'g' : k.pct >= 50 ? 'a' : 'r'} /></i>
              </div>
            ))}
          </section>
          {d.dims.some((k) => k.lagging) && (
            <section className="panel">
              <h4>Remediation for lagging dimensions</h4>
              {d.dims.filter((k) => k.lagging).map((k) => <div key={k.dim}><h5>{k.dim}</h5><ul>{k.remedy.map((r) => <li key={r}>{r}</li>)}</ul></div>)}
            </section>
          )}
          <section className="panel">
            <h4>FlyHigh qualification</h4>
            {Object.entries(d.qualification).map(([k, v]) => <div key={k} className="shared-row"><b>{k[0].toUpperCase() + k.slice(1)}</b><span className="muted">{v}</span></div>)}
          </section>
        </aside>
      </div>
    </div>
  )
}

function Gauge({ pct, tone }) {
  const r = 46; const c = 2 * Math.PI * r
  return (
    <svg viewBox="0 0 110 110" className={`pm-gauge ${tone}`} width="110" height="110">
      <circle cx="55" cy="55" r={r} className="bg" />
      <circle cx="55" cy="55" r={r} className="fg" strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 55 55)" />
      <text x="55" y="61" textAnchor="middle">{pct}%</text>
    </svg>
  )
}

/* ---------------------------------------------------------------- Plan and execute */
export function Roadmap({ focus, onNavigate }) {
  const archKeys = ['migrate', 'product', 'bi', 'ai']
  const [arch, setArch] = useState(archKeys.includes(focus) ? focus : 'migrate')
  const [d, setD] = useState(null)
  const [tab, setTab] = useState(archKeys.includes(focus) ? 'execute' : ['plan', 'setup', 'execute', 'optimize'].includes(focus) ? focus : 'journey')
  useEffect(() => { api.get(`/api/pmo/roadmap?archetype=${arch}`).then(setD) }, [arch])
  useEffect(() => { if (archKeys.includes(focus)) { setArch(focus); setTab('execute') } else if (['plan', 'setup', 'execute', 'optimize'].includes(focus)) setTab(focus) }, [focus]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return <div className="page">Loading…</div>
  const toggle = async (stage, idx, done) => {
    const c = await api.put('/api/pmo/roadmap/check', { stage, archetype: arch, idx, done })
    setD((o) => ({ ...o, checks: c }))
  }
  const Checks = ({ stage }) => (
    <div className="checklist pm-checks">
      {d.checks[stage].map((c, i) => (
        <label key={i} className={c.done ? 'done' : ''}><input type="checkbox" checked={c.done} onChange={(e) => toggle(stage, i, e.target.checked)} /> {c.text}</label>
      ))}
    </div>
  )
  const a = d.archetype
  return (
    <div className="page">
      <Head eyebrow="Program office · Plan, set up, execute, optimize" title="Run the program from kickoff to transition"
        lede="Six playbook stages with an exit checklist each, the 13 planning steps, the 7 setup steps, the activities per archetype with the agent or skill and the human gate, and the measures that close the loop.">
        <span className="spill"><b>{Object.values(d.checks).flat().filter((c) => c.done).length}</b> of {Object.values(d.checks).flat().length} checks done</span>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['journey', 'Stages and exit checks'], ['onboard', 'Onboarding plan'], ['plan', 'Plan · 13 steps'], ['setup', 'Setup · 7 steps'], ['execute', 'Execute by archetype'], ['autonomy', 'Autonomy and context'], ['optimize', 'Optimize']]} />

      {tab === 'journey' && (
        <div className="pm-grid3">
          {d.stages.map((s, i) => {
            const c = d.checks[s.code]; const n = c.filter((x) => x.done).length
            return (
              <section key={s.code} className={`panel pm-stage ${n === c.length ? 'complete' : ''}`}>
                <div className="pm-stage-top"><span className="pm-num">{i + 1}</span><b>{s.name}</b><small>{n}/{c.length}</small></div>
                <Checks stage={s.code} />
                {s.code === 'readiness' && <button className="btn ghost small" onClick={() => onNavigate('readiness')}>Open the scorecard →</button>}
                {s.code === 'primer' && <button className="btn ghost small" onClick={() => onNavigate('playbook')}>Read the primer →</button>}
                {['plan', 'setup', 'execute', 'optimize'].includes(s.code) && <button className="btn ghost small" onClick={() => setTab(s.code)}>Open {s.name.toLowerCase()} →</button>}
              </section>
            )
          })}
        </div>
      )}

      {tab === 'onboard' && (
        <>
          <section className="panel"><h4>Nine phases, kickoff to transition</h4>
            <div className="pm-phases">{d.onboarding.map((o, i) => (
              <div key={o.phase} className="pm-phase"><span className="pm-num">{i + 1}</span><b>{o.phase}</b><small className="muted">{o.timeline}</small><span>{o.activities}</span><em>→ {o.output}</em><small>{o.owner}</small></div>
            ))}</div>
          </section>
          <section className="panel"><h4>Program metadata (FlyHigh)</h4><Table cols={['Parameter', 'FlyHigh', 'Guidance']} rows={d.program} keys={['parameter', 'value', (r) => <span className="muted small">{r.guidance}</span>]} /></section>
        </>
      )}

      {tab === 'plan' && (
        <>
          <section className="panel"><h4>Thirteen planning steps</h4>
            <Table cols={['#', 'Step', 'Inputs', 'Activity', 'Tools and templates', 'Outputs']} rows={d.plan.map((r, i) => ({ ...r, n: i + 1 }))} keys={['n', (r) => <b>{r.step}</b>, 'inputs', 'activity', 'tools', 'outputs']} />
          </section>
          <section className="panel"><h4>Plan exit checks</h4><Checks stage="plan" /></section>
        </>
      )}

      {tab === 'setup' && (
        <>
          <section className="panel"><h4>Seven setup steps</h4>
            <Table cols={['#', 'Step', 'Inputs', 'Activity', 'Outputs']} rows={d.setup.map((r, i) => ({ ...r, n: i + 1 }))} keys={['n', (r) => <b>{r.step}</b>, 'inputs', 'activity', 'outputs']} />
          </section>
          <div className="two">
            <section className="panel"><h4>Harness readiness</h4>{d.harness.readiness.map(([t, x]) => <div key={t} className="shared-row"><b>{t}</b><span className="muted">{x}</span></div>)}</section>
            <section className="panel"><h4>Setup exit checks</h4><Checks stage="setup" /></section>
          </div>
        </>
      )}

      {tab === 'execute' && (
        <>
          <div className="pm-tracks">
            {d.archetypes.map((x) => <button key={x.key} className={`pm-track ${x.key === arch ? 'on' : ''}`} onClick={() => setArch(x.key)}><b>{x.title}</b><small>{x.lc}</small></button>)}
          </div>
          <section className="panel"><p>{a.intro}</p><p className="pm-flow">{a.method}</p></section>
          {a.phases.map((ph, i) => (
            <section key={ph.name} className="panel"><h4>{i + 1}. {ph.name}</h4>
              <Table cols={['Role', 'Activity', 'Agent or skill', 'Snowflake and other tools', 'Human involvement']} rows={ph.rows}
                keys={['role', 'activity', (r) => (r.agent ? <SkillRefs text={r.agent} onNavigate={onNavigate} /> : <span className="muted">—</span>), 'tools', (r) => <span className="pm-human">{r.human}</span>]} />
            </section>
          ))}
          <section className="panel"><h4>Execute exit checks</h4><Checks stage="execute" /></section>
        </>
      )}

      {tab === 'autonomy' && (
        <>
          <section className="panel"><h4>Autonomy by use case</h4><p className="muted small">Human-led → AI-assisted → agentic workflow → autonomous execution. Autonomy rises only where lineage, reconciliation evidence, access controls and rollback support it. Production writes, masking rules and go / no-go stay with people.</p>
            <Table cols={['Activity', 'Use case', 'Mode', 'Autonomy', 'Human role']} rows={d.autonomy} keys={['activity', 'use_case', 'mode', 'autonomy', 'human']} /></section>
          <section className="panel"><h4>Minimum context before each wave</h4>
            <Table cols={['Area', 'Required context', 'Availability', 'Action']} rows={d.context} keys={['area', 'required', (r) => <Rag s={/missing/i.test(r.availability) ? 'red' : /partial/i.test(r.availability) ? 'amber' : 'green'}>{r.availability}</Rag>, 'action']} /></section>
          <section className="panel"><h4>AI-native ways of working</h4>{d.ways.map((w) => <div key={w.area} className="shared-row"><b>{w.area}</b><span className="muted">{w.practice}</span></div>)}</section>
        </>
      )}

      {tab === 'optimize' && (
        <div className="two">
          <section className="panel"><h4>Measures that close the loop</h4><Table cols={['Measure', 'Target', 'Where']} rows={d.optimize} keys={['measure', 'target', 'where']} />
            <button className="btn ghost" style={{ marginTop: 10 }} onClick={() => onNavigate('kpis')}>Open the KPI scorecard →</button></section>
          <section className="panel"><h4>Optimize exit checks</h4><Checks stage="optimize" /></section>
        </div>
      )}
    </div>
  )
}

function SkillRefs({ text, onNavigate }) {
  const parts = String(text).split(/(\/[a-z][a-z-]+)/g)
  return <span>{parts.map((p, i) => (p.startsWith('/') ? <a key={i} className="link mono" onClick={() => onNavigate('skills', p.slice(1))}>{p}</a> : p))}</span>
}

/* ---------------------------------------------------------------- Estimator */
const SMC = ['S', 'M', 'C']
export function Estimator() {
  const [d, , reload] = useLoad('/api/pmo/estimator')
  const [e, setE] = useState(null)
  const [r, setR] = useState(null)
  const [name, setName] = useState('')
  const t = useRef(null)
  useEffect(() => { if (d && !e) { setE(JSON.parse(JSON.stringify(d.config.defaults))); setR(d.result) } }, [d]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!e) return
    clearTimeout(t.current)
    t.current = setTimeout(() => api.post('/api/pmo/estimator', { params: e }).then(setR), 250)
  }, [e])
  if (!d || !e || !r) return <div className="page">Loading…</div>
  const cfg = d.config
  const setN = (path, v) => setE((o) => { const n = JSON.parse(JSON.stringify(o)); let x = n; path.slice(0, -1).forEach((k) => { x = x[k] }); x[path.at(-1)] = Math.max(0, Number(v) || 0); return n })
  const num = (path) => <input type="number" min="0" className="pm-num-in" value={path.reduce((x, k) => x[k], e)} onChange={(ev) => setN(path, ev.target.value)} />
  const save = async () => { if (!name.trim()) return; await api.post('/api/pmo/estimator', { params: e, save_as: name }); setName(''); reload() }
  const load = async (id) => { const s = await api.get(`/api/pmo/estimator/${id}`); setE({ ...cfg.defaults, ...s.params }) }
  const maxAct = Math.max(...Object.values(r.by_activity), 1)
  return (
    <div className="page">
      <Head eyebrow="Program office · Unit-effort model" title="Size the build, then let the pilot prove the speed-up"
        lede="Objects by complexity, AI frameworks and discovery components, with the pilot at full effort and later waves at the archetype's speed-up. Program management, cut-over and hypercare are loaded by role in the resource plan.">
        <span className="spill on"><b>{r.total_pd.toLocaleString()}</b> person-days</span><span className="spill"><b>{r.person_months}</b> person-months</span><span className="spill"><b>{r.avg_fte}</b> avg FTE</span>
      </Head>
      <div className="pm-est">
        <section className="panel">
          <h4>Inputs</h4>
          <table className="tbl pm-in">
            <thead><tr><th>Objects</th><th>Simple</th><th>Medium ×2</th><th>Complex ×4</th><th>Base</th></tr></thead>
            <tbody>
              {['ETL', 'DW', 'BI'].map((c) => <tr key={c}><td><b>{c}</b><small className="muted"> {cfg.labels[c]}</small></td>{SMC.map((x) => <td key={x}>{num([c, x])}</td>)}<td className="muted">{cfg.base[c]} PD</td></tr>)}
              <tr><td><b>AI frameworks</b><small className="muted"> build or adapt + validation</small></td>{SMC.map((x) => <td key={x}>{num(['fw', x])}</td>)}<td className="muted small">6/15/25 + 3/5/8</td></tr>
              <tr><td><b>Discovery</b><small className="muted"> sources or report groups</small></td>{SMC.map((x) => <td key={x}>{num(['disc', x])}</td>)}<td className="muted small">10/20/30</td></tr>
            </tbody>
          </table>
          <div className="form-grid pm-form">
            <label className="field"><span>Share in pilot wave (%)</span>{num(['pilot'])}</label>
            <label className="field"><span>Wave speed-up after the pilot</span>
              <select value={e.speed} onChange={(ev) => setE((o) => ({ ...o, speed: Number(ev.target.value) }))}>{cfg.speeds.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field"><span>Delivery months</span>{num(['months'])}</label>
          </div>
          <h5>Score a framework's complexity</h5>
          <div className="pm-fs">{[['a', 'Agents ×2'], ['sa', 'Sub-agents ×1.5'], ['sk', 'Skills ×1'], ['t', 'Tools ×0.5'], ['f', 'Function calls ×0.5']].map(([k, l]) => <label key={k} className="field"><span>{l}</span>{num(['fs', k])}</label>)}</div>
          <p className="small"><b>{r.framework_score.points} points · {r.framework_score.class}</b> <span className="muted">(simple ≤ 20, medium ≤ 36, else complex)</span></p>
        </section>
        <aside>
          <section className="panel">
            <h4>Result</h4>
            <div className="pm-stats big"><div><b>{r.total_pd.toLocaleString()}</b><small>person-days</small></div><div><b>{r.person_months}</b><small>person-months</small></div><div><b>{r.avg_fte}</b><small>avg FTE over {e.months} mo</small></div></div>
            <h5>Object effort by activity</h5>
            {Object.entries(r.by_activity).map(([k, v]) => <div key={k} className="pm-dim"><div><span>{k}</span><b>{v.toLocaleString()} PD</b></div><i><em className={k === 'Build' ? 'p' : k === 'SIT' ? 's' : 'g'} style={{ width: `${(100 * v) / maxAct}%` }} /></i></div>)}
            <table className="tbl" style={{ marginTop: 10 }}>
              <thead><tr><th>Component</th><th>At pilot effort</th><th>With speed-up</th></tr></thead>
              <tbody>
                {Object.entries(r.components).map(([c, v]) => <tr key={c}><td>{c}</td><td>{v.full.toLocaleString()}</td><td>{v.with_speedup.toLocaleString()}</td></tr>)}
                <tr><td>AI frameworks</td><td>{r.frameworks_pd}</td><td>{r.frameworks_pd}</td></tr>
                <tr><td>Discovery and design</td><td>{r.discovery_pd}</td><td>{r.discovery_pd}</td></tr>
                <tr><td><b>Total</b></td><td><b>{r.without_speedup_pd.toLocaleString()}</b></td><td><b>{r.total_pd.toLocaleString()}</b></td></tr>
              </tbody>
            </table>
            <p className="muted small">{r.note}</p>
          </section>
          <section className="panel">
            <h4>Scenarios</h4>
            <div className="toolbar"><input className="search" placeholder="Scenario name" value={name} onChange={(ev) => setName(ev.target.value)} /><button className="btn primary" onClick={save} disabled={!name.trim()}>Save</button>
              <button className="btn ghost" onClick={() => setE(JSON.parse(JSON.stringify(cfg.defaults)))}>Reset</button></div>
            {d.scenarios.map((s) => <button key={s.id} className="list-item" onClick={() => load(s.id)}><b>{s.name}</b><small>{Number(s.total_pd).toLocaleString()} PD · {s.avg_fte} FTE · {s.created_by}</small></button>)}
            {!d.scenarios.length && <span className="muted small">No saved scenarios yet.</span>}
          </section>
        </aside>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- Use cases */
const LV = ['High', 'Med', 'Low']
const AUTOS = ['Agentic (Execute)', 'Agentic (Orchestrate)', 'Agentic (Recommend)', 'Manual (human)']
const LANE_TONE = { 'Pilot wave': 'g', 'Next wave': 's', 'Assist only': 'a', 'Human gate': 'r' }
export function UseCases({ onNavigate }) {
  const [d, setD] = useLoad('/api/pmo/usecases')
  const [arch, setArch] = useState('all')
  const [sort, setSort] = useState('flow')
  const rows = useMemo(() => {
    if (!d) return []
    const f = d.items.filter((u) => arch === 'all' || u.archetype === arch)
    return sort === 'score' ? [...f].sort((a, b) => b.score - a.score) : f
  }, [d, arch, sort])
  if (!d) return <div className="page">Loading…</div>
  const edit = async (u, k, v) => {
    const n = await api.put(`/api/pmo/usecases/${u.id}`, { [k]: v })
    setD((o) => ({ ...o, items: o.items.map((x) => (x.id === u.id ? n : x)) }))
  }
  const lanes = rows.reduce((m, u) => ({ ...m, [u.lane]: (m[u.lane] || 0) + 1 }), {})
  const title = (k) => d.archetypes.find((a) => a.key === k)?.title || k
  return (
    <div className="page">
      <Head eyebrow="Program office · AI use-case identification and prioritization" title="Decide where agents work first, and where people stay in charge"
        lede="Rate each lifecycle activity on six criteria. The weighted score sets a lane: pilot wave, next wave or assist only. Manual or high-risk work stays behind a human gate.">
        {Object.entries(lanes).map(([k, v]) => <span key={k} className={`spill pm-lane-${LANE_TONE[k]}`}><b>{v}</b> {k}</span>)}
      </Head>
      <div className="pm-grid6">{d.criteria.map((c) => <div key={c.code} className="pm-crit"><b>{c.name}</b><small>{c.question}</small></div>)}</div>
      <p className="muted small">Weights: {Object.entries(d.weights).map(([k, v]) => `${k} ${v}`).join(' · ')}. High = 3, medium = 2, low = 1 (complexity and risk score inversely).</p>
      <section className="panel">
        <div className="toolbar">
          <div className="tabs">{[['all', 'All archetypes'], ...d.archetypes.map((a) => [a.key, a.title])].map(([k, l]) => <button key={k} className={arch === k ? 'on' : ''} onClick={() => setArch(k)}>{l}</button>)}</div>
          <span style={{ flex: 1 }} />
          <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="flow">Lifecycle order</option><option value="score">Highest score first</option></select>
          <button className="btn ghost" onClick={() => onNavigate('skills', 'pmo-usecase-prioritizer')}>Run the prioritizer skill</button>
        </div>
        <div className="md-table"><table className="tbl pm-uc">
          <thead><tr><th>Archetype · stage</th><th>Activity</th><th>Value</th><th>Repeat.</th><th>Complexity</th><th>Risk</th><th>Automation</th><th>Score</th><th>Lane</th><th>Prerequisites</th></tr></thead>
          <tbody>{rows.map((u) => (
            <tr key={u.id}>
              <td className="small"><b>{title(u.archetype)}</b><br /><span className="muted">{u.stage}</span></td>
              <td>{u.activity}</td>
              {['value', 'rep', 'comp', 'risk'].map((k) => <td key={k}><select className={`pm-lv ${u[k]}`} value={u[k] === 'Medium' ? 'Med' : u[k]} onChange={(e) => edit(u, k, e.target.value)}>{LV.map((x) => <option key={x}>{x}</option>)}</select></td>)}
              <td><select value={u.automation} onChange={(e) => edit(u, 'automation', e.target.value)}>{[...new Set([u.automation, ...AUTOS])].map((x) => <option key={x}>{x}</option>)}</select></td>
              <td><b>{u.score}</b></td>
              <td><span className={`pm-rag ${LANE_TONE[u.lane]}`}>{u.lane}</span></td>
              <td className="muted small">{u.prereq}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </section>
      <section className="panel"><h4>Persona-level impact targets (to prove in the pilot)</h4>
        <div className="pm-grid3">{d.impact.map((x) => <div key={x.persona} className="pm-impact"><b>{x.figure}</b><span>{x.label}</span><small className="muted">{x.persona} · {x.area}</small></div>)}</div>
      </section>
    </div>
  )
}

/* ---------------------------------------------------------------- KPI scorecard */
export function Kpis({ onNavigate }) {
  const [d, setD] = useLoad('/api/pmo/kpis')
  const [ed, setEd] = useState(null)
  if (!d) return <div className="page">Loading…</div>
  const save = async (k, data) => {
    const n = await api.put(`/api/pmo/kpis/${k.id}`, { actual: data.actual ?? '', status: data.status || 'na', note: data.note ?? '' })
    setD((o) => {
      const categories = o.categories.map((c) => ({ ...c, metrics: c.metrics.map((m) => (m.id === n.id ? n : m)) }))
      const all = categories.flatMap((c) => c.metrics)
      return { ...o, categories, counts: Object.fromEntries(['green', 'amber', 'red', 'na'].map((s) => [s, all.filter((m) => m.status === s).length])) }
    })
  }
  return (
    <div className="page">
      <Head eyebrow="Program office · Measurement framework and KPI scorecard" title="Trusted numbers and legacy retired on date" lede={d.principle}>
        <span className="spill pm-lane-g"><b>{d.counts.green}</b> green</span><span className="spill pm-lane-a"><b>{d.counts.amber}</b> amber</span><span className="spill pm-lane-r"><b>{d.counts.red}</b> red</span><span className="spill"><b>{d.counts.na}</b> not set</span>
        <button className="btn ghost" onClick={() => onNavigate('skills', 'pmo-steering-pack')}>Build the steering pack</button>
      </Head>
      <div className="pm-grid6">{d.dims.map((x) => <div key={x.dim} className="pm-crit"><b>{x.dim}</b><small>{x.question}</small><ul>{x.measures.map((m) => <li key={m}>{m}</li>)}</ul></div>)}</div>
      <p className="muted small">{d.method}</p>
      {d.categories.map((c) => (
        <section key={c.category} className="panel">
          <h4>{c.category}</h4>
          <div className="md-table"><table className="tbl">
            <thead><tr><th>Metric</th><th>What it tells us</th><th>Source</th><th>Capture</th><th>Cadence</th><th>Target</th><th>Actual</th><th>Status</th><th /></tr></thead>
            <tbody>{c.metrics.map((k) => (
              <tr key={k.id}>
                <td><b>{k.name}</b></td><td className="small">{k.what}</td><td className="small muted">{k.source}</td>
                <td><Chip tone={k.capture === 'AUTO' ? 'snow' : k.capture === 'HYBRID' ? 'purple' : 'default'}>{k.capture}</Chip></td>
                <td className="small">{k.cadence}</td><td><b>{k.target}</b></td>
                <td>{k.actual || <span className="muted">—</span>}{k.note && <div className="muted small">{k.note}</div>}</td>
                <td><Rag s={k.status} /></td>
                <td><button className="icon-btn" title="Update" onClick={() => setEd(k)}>✎</button></td>
              </tr>
            ))}</tbody>
          </table></div>
        </section>
      ))}
      {ed && <Editor title={`Update · ${ed.name}`} initial={ed} onClose={() => setEd(null)} onSave={(data) => save(ed, data)}
        fields={[{ key: 'actual', label: `Actual (target ${ed.target})` }, { key: 'status', label: 'Status', type: 'select', options: ['green', 'amber', 'red', 'na'] }, { key: 'note', label: 'Note', type: 'textarea' }]} />}
    </div>
  )
}

/* ---------------------------------------------------------------- Governance and RAID */
const KINDS = ['Risk', 'Assumption', 'Issue', 'Dependency', 'Decision']
export function Governance({ onNavigate }) {
  const [d, setD, reload] = useLoad('/api/pmo/governance')
  const [tab, setTab] = useState('raid')
  const [kind, setKind] = useState('')
  const [ed, setEd] = useState(null)
  if (!d) return <div className="page">Loading…</div>
  const g = d.governance; const rai = d.rai
  const open = d.raid.filter((r) => r.status !== 'Closed')
  const fields = [
    { key: 'kind', label: 'Type', type: 'select', options: KINDS }, { key: 'title', label: 'Title', required: true },
    { key: 'detail', label: 'Detail or mitigation', type: 'textarea' }, { key: 'owner', label: 'Owner' }, { key: 'due', label: 'Due' },
    { key: 'severity', label: 'Severity', type: 'select', options: ['High', 'Medium', 'Low'] }, { key: 'status', label: 'Status', type: 'select', options: ['Open', 'Mitigating', 'Closed'] },
  ]
  const saveRaid = async (data) => {
    const body = { kind: data.kind || 'Risk', title: data.title, detail: data.detail, owner: data.owner, due: data.due, severity: data.severity || 'Medium', status: data.status || 'Open' }
    if (data.id) await api.put(`/api/pmo/raid/${data.id}`, body); else await api.post('/api/pmo/raid', body)
    reload()
  }
  return (
    <div className="page">
      <Head eyebrow="Program office · Governance, Responsible AI and RAID" title="Humans own the gates; evidence shows they can"
        lede={rai.principle}>
        <span className="spill"><b>{open.length}</b> open RAID</span><span className="spill pm-lane-r"><b>{open.filter((r) => r.severity === 'High').length}</b> high</span>
        <button className="btn ghost" onClick={() => onNavigate('skills', 'pmo-steering-pack')}>Build the steering pack</button>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['raid', 'RAID log'], ['model', 'Operating model and cadence'], ['rai', 'Responsible AI'], ['guard', 'Guardrails'], ['gates', `Gate log (${d.gates.length})`]]} />

      {tab === 'raid' && (
        <section className="panel">
          <div className="toolbar">
            <div className="tabs">{[['', 'All'], ...KINDS.map((k) => [k, k])].map(([k, l]) => <button key={l} className={kind === k ? 'on' : ''} onClick={() => setKind(k)}>{l}</button>)}</div>
            <span style={{ flex: 1 }} />
            <button className="btn primary" onClick={() => setEd({ kind: kind || 'Risk', severity: 'Medium', status: 'Open' })}>+ Add item</button>
          </div>
          <div className="md-table"><table className="tbl">
            <thead><tr><th>Type</th><th>Title</th><th>Detail or mitigation</th><th>Owner</th><th>Due</th><th>Severity</th><th>Status</th><th /></tr></thead>
            <tbody>{d.raid.filter((r) => !kind || r.kind === kind).map((r) => (
              <tr key={r.id} className={r.status === 'Closed' ? 'pm-closed' : ''}>
                <td><Chip tone={r.kind === 'Risk' ? 'purple' : r.kind === 'Issue' ? 'default' : 'snow'}>{r.kind}</Chip></td>
                <td><b>{r.title}</b>{r.origin !== 'seed' && <span className="origin">{r.origin === 'skill' ? 'Skill' : 'Curated'}</span>}</td>
                <td className="small">{r.detail}</td><td className="small">{r.owner}</td><td className="small">{r.due}</td>
                <td><Rag s={r.severity === 'High' ? 'red' : r.severity === 'Medium' ? 'amber' : 'green'}>{r.severity}</Rag></td>
                <td className="small">{r.status}</td>
                <td><button className="icon-btn" onClick={() => setEd(r)}>✎</button></td>
              </tr>
            ))}</tbody>
          </table></div>
        </section>
      )}

      {tab === 'model' && (
        <>
          <section className="panel"><h4>Three tiers of accountability</h4>
            <div className="pm-grid3">{g.tiers.map((t) => <div key={t.tier} className="pm-tier"><b>{t.tier}</b><span className="muted">{t.role}</span></div>)}</div>
            <p className="small" style={{ marginTop: 10 }}><b>Escalation chain:</b> {g.chain}</p>
          </section>
          <div className="two">
            <section className="panel"><h4>Governance cadence</h4><Table cols={['Cadence', 'Forum', 'Who']} rows={g.cadence} keys={[(r) => <b>{r.cadence}</b>, 'forum', 'who']} /></section>
            <section className="panel"><h4>Decision areas</h4><Table cols={['Area', 'Key decisions and controls', 'Owner']} rows={g.areas} keys={[(r) => <b>{r.area}</b>, 'controls', 'owner']} /></section>
          </div>
        </>
      )}

      {tab === 'rai' && (
        <>
          <section className="panel"><h4>Responsible AI across the lifecycle</h4>
            <div className="pm-grid4">{rai.lifecycle.map((s, i) => <div key={s.stage} className="pm-lane"><b>{i + 1}. {s.stage}</b>{s.controls.map((c) => <div key={c}><span>{c}</span></div>)}</div>)}</div>
          </section>
          <section className="panel"><h4>Eight pillars: where it breaks, how we fix it</h4><Table cols={['Pillar', 'Where problems occur', 'How the framework resolves it']} rows={rai.pillars} keys={[(r) => <b>{r.pillar}</b>, 'risk', 'control']} /></section>
          <section className="panel"><h4>Agent-lifecycle risks and controls</h4><Table cols={['Risk', 'Control', 'Stage', 'Standard']} rows={rai.risks} keys={[(r) => <b>{r.risk}</b>, 'control', 'stage', (r) => <span className="muted small">{r.standard}</span>]} />
            <p className="muted small">Standards: {rai.standards}</p></section>
        </>
      )}

      {tab === 'guard' && (
        <div className="two">
          <section className="panel"><h4>Harness guardrails</h4>{d.guardrails.map(([t, k, x]) => <div key={t} className="shared-row"><b>{t} <Chip tone="snow">{k}</Chip></b><span className="muted">{x}</span></div>)}</section>
          <section className="panel"><h4>Harness readiness</h4>{d.harness_readiness.map(([t, x]) => <div key={t} className="shared-row"><b>{t}</b><span className="muted">{x}</span></div>)}</section>
        </div>
      )}

      {tab === 'gates' && (
        <section className="panel">
          {d.gates.length ? <Table cols={['When', 'Gate', 'Stage', 'Approver', 'Decision', 'Conditions', 'Recorded by']} rows={d.gates}
            keys={[(r) => new Date(r.decided_at).toLocaleString(), 'gate_code', (r) => r.stage_name || r.stage_code, 'approver', 'decision', 'conditions', 'recorded_by']} />
            : <Empty>No gate decisions recorded yet. They are recorded from the pursuit orchestrator skill and appear here for steering.</Empty>}
        </section>
      )}

      {ed && <Editor title={ed.id ? `Edit ${ed.kind.toLowerCase()}` : 'Add a RAID item'} initial={ed} fields={fields} onClose={() => setEd(null)} onSave={saveRaid}
        onDelete={ed.id ? async () => { await api.del(`/api/pmo/raid/${ed.id}`); reload() } : undefined} />}
    </div>
  )
}

/* ---------------------------------------------------------------- Team and RACI */
export function Team() {
  const [d] = useLoad('/api/pmo/team')
  const [tab, setTab] = useState('topology')
  const [rx, setRx] = useState(0)
  if (!d) return <div className="page">Loading…</div>
  const m = d.raci[rx]
  return (
    <div className="page">
      <Head eyebrow="Program office · Team formation and RACI" title="One AI-native core pod builds once; track pods reuse every wave"
        lede="Data roles do not disappear. A core pod builds the frameworks, track pods apply them per wave, and named humans own G1, G2 and G3.">
        <span className="spill"><b>~6</b> FTE core pod</span><span className="spill"><b>~3.5</b> FTE per track pod</span>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['topology', 'Topology'], ['size', 'Team by archetype'], ['roles', 'Role evolution'], ['raci', 'RACI matrices']]} />
      {tab === 'topology' && (
        <>
          <div className="pm-grid2">{d.topology.map((t, i) => <section key={t.principle} className="panel pm-practice"><span className="pm-num">{i + 1}</span><div><b>{t.principle}</b><p className="muted">{t.detail}</p></div></section>)}</div>
          <div className="two">
            <section className="panel"><h4>Central role</h4><p>{d.lead}</p></section>
            <section className="panel"><h4>Seed allocation</h4><p>{d.seed}</p></section>
          </div>
        </>
      )}
      {tab === 'size' && (
        <div className="pm-grid4">{d.archetypes.map((a) => (
          <section key={a.key} className="panel pm-team"><h2>{a.name}</h2><b className="pm-size">{a.size}</b>
            <table className="tbl"><tbody>{a.roles.map((r) => <tr key={r.role}><td>{r.role}</td><td><b>{r.fte}</b></td></tr>)}</tbody></table>
            <p className="muted small" style={{ marginTop: 8 }}><b>AI Native engineer:</b> {a.ai_native}</p></section>
        ))}</div>
      )}
      {tab === 'roles' && (
        <section className="panel"><Table cols={['Role', 'Traditional', 'AI-native', 'How the role contributes']} rows={d.roles}
          keys={[(r) => <b>{r.role}</b>, (r) => <span className="muted small">{r.traditional}</span>, 'ai_native', (r) => <span className="small">{r.contribution}</span>]} /></section>
      )}
      {tab === 'raci' && (
        <section className="panel">
          <div className="tabs" style={{ marginBottom: 10 }}>{d.raci.map((x, i) => <button key={x.title} className={rx === i ? 'on' : ''} onClick={() => setRx(i)}>{x.title}</button>)}</div>
          <div className="md-table"><table className="tbl pm-raci">
            <thead><tr><th>Activity</th>{m.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{m.rows.map((r) => (
              <tr key={r.activity}><td><b>{r.activity}</b>{r.detail && <div className="muted small">{r.detail}</div>}</td>
                {r.cells.map((c, i) => <td key={i}><span className={`pm-rc ${c.replace(/[^ARCI]/g, '')[0] || ''}`}>{c}</span></td>)}</tr>
            ))}</tbody>
          </table></div>
          <p className="muted small">R responsible · A accountable · C consulted · I informed. Agents are never accountable: every A is a named person.</p>
        </section>
      )}
    </div>
  )
}
