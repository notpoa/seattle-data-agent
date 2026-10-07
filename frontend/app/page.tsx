'use client';
import { useRef, useState } from 'react';
import { emptySession, EventReader, reduceEvent, type Result } from '../lib/session';

function Chart({result}: {result: Result}) {
  if (result.truncated || !result.rows.length || (result.query.group_by?.length || 0) > 1 || (result.query.time_bucket && result.query.group_by?.length) || (!result.query.time_bucket && !result.query.group_by?.length)) return null;
  const data = result.rows.map(r => ({label: String(r.period ?? r[result.query.group_by?.[0] || ''] ?? 'Unknown'), value: Number(r.value)}));
  if (data.length < 2 || data.length > 36 || data.some(d => !Number.isFinite(d.value) || d.value < 0)) return null;
  const maximum = Math.max(...data.map(d => d.value), 1);
  return <figure><figcaption>{result.query.time_bucket ? 'Trend across returned periods' : 'Comparison of returned groups'}</figcaption>
    <div className="chart" role="img" aria-label={data.map(d => `${d.label}: ${d.value}`).join('; ')}>
      {data.map((d, i) => <div className="bar-column" key={i}><span className="bar-number">{d.value.toLocaleString()}</span><div className="bar-track"><div className="bar" style={{height: `${Math.max(1, d.value / maximum * 100)}%`}} /></div><span className="bar-label" title={d.label}>{result.query.time_bucket ? d.label.slice(0, 7) : d.label}</span></div>)}
    </div><p className="muted">Axis starts at zero. Missing periods are not zero; boundary periods may be incomplete.</p></figure>;
}

function Table({result}: {result: Result}) {
  const columns = [...new Set(result.rows.flatMap(row => Object.keys(row)))];
  return <section className="result"><h3>{result.title}</h3><Chart result={result} />
    {result.rows.length ? <div className="table-scroll"><table><caption className="sr-only">Query results for {result.title}</caption><thead><tr>{columns.map(c => <th key={c} scope="col">{c.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{result.rows.map((row, i) => <tr key={i}>{columns.map(c => <td key={c}>{row[c] == null ? '—' : typeof row[c] === 'object' ? JSON.stringify(row[c]) : String(row[c])}</td>)}</tr>)}</tbody></table></div> : <p>No matching rows were returned.</p>}
    {result.warnings.map((w, i) => <p className="muted" key={i}>{w}</p>)}
    <p className="source"><a href={result.source_url} target="_blank" rel="noreferrer">View official source ↗</a><span>Retrieved {new Date(result.retrieved_at).toLocaleString()}</span></p>
    <details><summary>How this result was calculated</summary><pre>{JSON.stringify({query: result.query, parameters: result.parameters}, null, 2)}</pre></details>
  </section>;
}

export default function Home() {
  const [interest, setInterest] = useState('');
  const [question, setQuestion] = useState('');
  const [session, setSession] = useState(emptySession);
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setSession(emptySession()); setBusy(true);
    controller.current = new AbortController();
    let terminal = false;
    try {
      // Built website uses same-origin FastAPI. Separate Next dev server uses 8000.
      const base = process.env.NEXT_PUBLIC_API_URL || (window.location.port === '3000' ? 'http://127.0.0.1:8000' : '');
      const response = await fetch(`${base}/api/analyze`, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dataset_interest: interest.trim(), question: question.trim()}), signal: controller.current.signal});
      if (!response.ok) throw new Error(`The backend returned HTTP ${response.status}. Check that it is running and your inputs are valid.`);
      if (!response.body) throw new Error('The backend returned an empty response.');
      const reader = response.body.getReader(); const decoder = new TextDecoder(); const parser = new EventReader();
      const apply = (events: ReturnType<EventReader['push']>) => events.forEach(e => {
        terminal ||= e.type === 'answer' || e.type === 'error';
        setSession(s => reduceEvent(s, e));
      });
      while (true) {const {value, done} = await reader.read(); if (done) break; apply(parser.push(decoder.decode(value, {stream: true})));}
      apply(parser.push(decoder.decode())); apply(parser.finish());
      if (!terminal) throw new Error('The connection ended before analysis completed. Any tables shown are partial results.');
    } catch (error) {
      const message = error instanceof Error && error.name === 'AbortError' ? 'Request stopped. Any tables shown are partial results.' : error instanceof Error ? error.message : 'The backend could not be reached.';
      setSession(s => ({...s, error: message, progress: ''}));
    } finally {setBusy(false); controller.current = null;}
  }
  return <main>
    <header><a className="brand" href="/">SEATTLE <span>DATA AGENT</span></a><span className="badge">Official public data</span></header>
    <section className="intro"><p className="eyebrow">A question is a good place to start.</p><h1>What do you want to<br />learn about Seattle?</h1><p>Tell us the topic and what you want to find out.<br />We’ll look for the right datasets and check the data.</p></section>
    <form onSubmit={submit} className="question-card">
      <label htmlFor="interest"><span className="step">1</span> What data are you interested in?</label>
      <input id="interest" value={interest} onChange={e => setInterest(e.target.value)} placeholder="For example, SPD arrest reports or building permits" required minLength={2} maxLength={200} disabled={busy} />
      <label htmlFor="question"><span className="step">2</span> What do you want to learn from it?</label>
      <textarea id="question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="For example, how did monthly arrest-report counts change in 2025?" required minLength={5} maxLength={1500} disabled={busy} rows={3} />
      <div className="form-bottom"><p>Include a time period when comparing changes.</p><button type="submit" disabled={busy || interest.trim().length < 2 || question.trim().length < 5}>{busy ? 'Working…' : 'Explore the data →'}</button>{busy && <button type="button" className="secondary" onClick={() => controller.current?.abort()}>Stop</button>}</div>
    </form>
    <p className="scope">Counts, comparisons, rankings, and time trends. Cross-dataset correlations aren’t supported yet.</p>
    {busy && <p className="progress" role="status" aria-live="polite"><span className="spinner" />{session.progress || 'Starting your request…'}</p>}
    {session.error && <section className="notice" role="alert" aria-labelledby="analysis-error"><h2 id="analysis-error">Couldn’t complete the analysis</h2><p>{session.error}</p></section>}
    {session.answer && <section className="answer" aria-live="polite"><p className="eyebrow">{session.status === 'answered' ? 'What the data shows' : session.status === 'overview' ? 'About this dataset' : session.status === 'clarification' ? 'One more detail' : 'A limitation to know'}</p><p className="answer-text">{session.answer}</p></section>}
    {(session.selected.length > 0 || session.datasets.length > 0) && <section className="datasets"><h2>{session.selected.length ? 'Datasets inspected' : 'Datasets found'}</h2><div className="dataset-grid">{(session.selected.length ? session.selected : session.datasets).map(d => <article key={d.dataset_id}><h3>{d.title}</h3><p>{d.description}</p>{d.limitation && <p className="muted">{d.limitation}</p>}<a href={`https://data.seattle.gov/d/${d.dataset_id}`} target="_blank" rel="noreferrer">Official dataset ↗</a></article>)}</div></section>}
    {session.results.map((result, i) => <Table key={i} result={result} />)}
    {!!session.warnings.length && <details className="tool-notes"><summary>Data checks and tool warnings</summary>{session.warnings.map((w, i) => <p key={i}>{w}</p>)}</details>}
    {session.diagnostics && <details><summary>Request details</summary><p>Outcome: {session.diagnostics.reason}. Model steps: {session.diagnostics.model_steps}. Tool calls: {session.diagnostics.tool_calls}. Successful queries: {session.diagnostics.successful_queries}.</p><p>Last tool: {session.diagnostics.last_tool}</p>{session.diagnostics.last_tool_error && <p>Last tool error: {session.diagnostics.last_tool_error}</p>}</details>}
    <footer>Seattle Open Data · Sources stay attached to every result.<br /><span>Findings depend on dataset definitions and coverage.</span></footer>
  </main>;
}
