import React, { useEffect, useState } from 'react';
import { BookOpen, Bot, ChevronDown, ExternalLink, FileText, History, MessageSquareText, RefreshCw, Search, ShieldAlert, Sparkles, Workflow } from 'lucide-react';
import { task1, json, explainError } from '../services/api';
import { Button, EmptyState, Field, Loading, Notice, StatusPill } from '../components/Primitives';

export default function KnowledgeChat() {
  const [question, setQuestion] = useState('How can I update my website settings?');
  const [topK, setTopK] = useState(6);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [escalations, setEscalations] = useState([]);
  const [showEscalations, setShowEscalations] = useState(false);
  const [ingestion, setIngestion] = useState(null);
  const [ingestionBusy, setIngestionBusy] = useState(false);

  async function ask(e) {
    e?.preventDefault(); if (!question.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try { setResult(await task1('/query', json('POST', { question: question.trim(), top_k: Number(topK) }))); }
    catch (err) { setError(explainError(err)); }
    finally { setLoading(false); }
  }
  async function loadEscalations() {
    setError(''); setShowEscalations(true);
    try { const data = await task1('/escalations?status=open&limit=100'); setEscalations(data?.items || []); }
    catch (err) { setError(explainError(err)); }
  }
  async function resolveEscalation(item) {
    const answer = window.prompt('Enter the expert-approved answer to index into the knowledge base:');
    if (!answer?.trim()) return;
    const sources = window.prompt('Source URLs (comma separated, optional):', '') || '';
    try {
      await task1(`/escalations/${encodeURIComponent(item.id)}/resolve`, json('POST', { answer: answer.trim(), sources: sources.split(',').map(x => x.trim()).filter(Boolean) }));
      await loadEscalations();
    } catch (err) { setError(explainError(err)); }
  }
  async function startIngestion() {
    setIngestionBusy(true); setError('');
    try { const data = await task1('/ingestion/run', { method: 'POST' }); setIngestion(data); }
    catch (err) { setError(explainError(err)); }
    finally { setIngestionBusy(false); }
  }
  async function refreshIngestion() {
    try { setIngestion(await task1('/ingestion/status')); } catch (err) { setError(explainError(err)); }
  }
  useEffect(() => { refreshIngestion(); }, []);
  const sources = Array.isArray(result?.sources) ? result.sources : [];
  return <div className="page-stack">
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark"><BookOpen size={14}/></span> TASK 01 / KNOWLEDGE BRAIN</div><h1>Knowledge <span className="gradient-text">Studio</span></h1><p>Ask grounded questions, inspect evidence, and manage human escalations.</p></div><div className="heading-actions"><Button variant="secondary" icon={History} onClick={loadEscalations}>Open escalations</Button><Button icon={RefreshCw} onClick={refreshIngestion}>Refresh status</Button></div></div>
    <Notice>{error}</Notice>
    <div className="metric-grid three">
      <div className="metric-card"><div className="metric-icon violet"><MessageSquareText size={18}/></div><div><span className="metric-label">Query endpoint</span><strong>POST /query</strong><small>Grounded answers + citations</small></div></div>
      <div className="metric-card"><div className="metric-icon cyan"><Workflow size={18}/></div><div><span className="metric-label">Ingestion</span><strong>{ingestion?.latest_job?.status || ingestion?.status || 'Ready to check'}</strong><small>{ingestion?.manifest_counts ? `${ingestion.manifest_counts.processed || 0} pages processed` : 'Sitemap sync status'}</small></div></div>
      <div className="metric-card"><div className="metric-icon amber"><ShieldAlert size={18}/></div><div><span className="metric-label">Human review</span><strong>{escalations.length || '—'} open</strong><small>Questions requiring expert support</small></div></div>
    </div>
    <div className="knowledge-layout">
      <section className="panel query-panel"><div className="panel-header"><div className="panel-title"><div className="panel-title-icon"><Sparkles size={18}/></div><div><h2>Ask the Knowledge Brain</h2><p>Answers should be supported by retrieved documentation.</p></div></div><span className="mini-label">RAG QUERY</span></div>
        <form onSubmit={ask} className="query-form"><Field label="Your question"><textarea className="textarea query-input" rows="4" maxLength={4000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about a feature, setting, integration, or troubleshooting step…" /></Field><div className="query-controls"><Field label="Evidence chunks"><select className="select" value={topK} onChange={e=>setTopK(e.target.value)}>{[3,4,5,6,8,10,12,16,20].map(n=><option key={n} value={n}>{n} chunks</option>)}</select></Field><Button type="submit" icon={Search} loading={loading}>Search knowledge</Button></div></form>
        {loading && <div className="result-loading"><Loading label="Retrieving evidence and generating an answer…"/><div className="loading-track"><span /></div></div>}
        {!loading && result && <div className="answer-card"><div className="answer-top"><div className="answer-label"><span className="answer-spark"><Bot size={16}/></span> GENERATED ANSWER</div><StatusPill status={result.status || 'unknown'}/></div><div className="answer-body">{result.answer || 'The API returned no answer text.'}</div>{result.needs_human && <div className="human-callout"><ShieldAlert size={18}/><div><strong>Human review required</strong><p>This response needs an expert to verify the facts before it is used.</p>{result.escalation_id && <code>{result.escalation_id}</code>}</div></div>}
          <div className="answer-meta">{result.model && <span>Model: <b>{result.model}</b></span>}{result.usage && <span>Usage: <b>{typeof result.usage === 'object' ? JSON.stringify(result.usage) : result.usage}</b></span>}{result.estimated_cost_usd != null && <span>Est. cost: <b>${Number(result.estimated_cost_usd).toFixed(5)}</b></span>}</div>
          <div className="sources-section"><div className="section-title"><span>Evidence sources</span><span className="count-badge">{sources.length}</span></div>{sources.length ? <div className="source-list">{sources.map((source,i)=>{const url=typeof source==='string'?source:source.url||source.source_url||source.link;const title=typeof source==='string'?source:source.title||source.name||source.url||`Source ${i+1}`;return <div className="source-item" key={i}><div className="source-icon"><FileText size={16}/></div><div className="source-copy"><strong>{title}</strong>{source.snippet && <p>{source.snippet}</p>}{source.relevance != null && <small>Relevance {Number(source.relevance).toFixed(2)}</small>}</div>{url && <a href={url} target="_blank" rel="noreferrer" className="source-link" title="Open source"><ExternalLink size={15}/></a>}</div>})}</div> : <EmptyState icon={FileText} title="No sources returned" body="This answer did not include source records. Review the API response before relying on it."/>}</div>
          <details className="raw-details"><summary>Inspect raw API response <ChevronDown size={15}/></summary><pre className="json-viewer">{JSON.stringify(result,null,2)}</pre></details>
        </div>}
        {!loading && !result && <div className="query-placeholder"><div className="orbital"><div className="orbital-core"><Sparkles size={25}/></div><span className="orbit orbit-one"/><span className="orbit orbit-two"/></div><h3>Answers with evidence, not guesswork.</h3><p>Ask a question to retrieve relevant knowledge and see the sources behind the answer.</p><div className="suggestion-row"><button onClick={()=>setQuestion('How do I configure a website feature?')}>Configuration help <span>↗</span></button><button onClick={()=>setQuestion('What should I do if a payment integration fails?')}>Troubleshooting <span>↗</span></button></div></div>}
      </section>
      <aside className="side-stack"><section className="panel side-panel"><div className="panel-header compact"><div><h3>Knowledge ingestion</h3><p>Keep indexed content fresh.</p></div><div className="mini-icon"><RefreshCw size={17}/></div></div><div className="ingestion-status"><span className="status-ring"><BookOpen size={18}/></span><div><strong>{ingestion?.latest_job?.status || ingestion?.status || 'Sitemap sync'}</strong><small>{ingestion?.latest_job?.job_id ? `Job ${ingestion.latest_job.job_id}` : 'Brilliant Directories help center'}</small></div></div>{ingestion?.manifest_counts && <div className="count-grid">{Object.entries(ingestion.manifest_counts).map(([key,value])=><div key={key}><strong>{value}</strong><span>{key}</span></div>)}</div>}<Button block icon={RefreshCw} loading={ingestionBusy} onClick={startIngestion}>Start full sync</Button><p className="tiny-note">This starts a background sitemap ingestion job. It may take time to complete.</p></section>
        <section className="panel side-panel"><div className="panel-header compact"><div><h3>Human escalation queue</h3><p>Unanswered or uncertain requests.</p></div><div className="mini-icon amber"><ShieldAlert size={17}/></div></div><div className="queue-number">{escalations.length}<span>open items loaded</span></div><Button variant="secondary" block onClick={loadEscalations}>View open escalations</Button></section>
      </aside>
    </div>
    {showEscalations && <section className="panel"><div className="panel-header"><div><h2>Open escalations</h2><p>Expert-approved answers are indexed before an escalation is resolved.</p></div><Button variant="ghost" onClick={()=>setShowEscalations(false)}>Close</Button></div>{escalations.length ? <div className="table-wrap"><table><thead><tr><th>Question</th><th>Reason</th><th>Status</th><th>Action</th></tr></thead><tbody>{escalations.map((item,i)=><tr key={item.id||i}><td><strong>{item.question}</strong><small>{item.id}</small></td><td>{item.reason||'Needs expert review'}</td><td><StatusPill status={item.status||'open'}/></td><td><Button size="small" onClick={()=>resolveEscalation(item)}>Resolve</Button></td></tr>)}</tbody></table></div> : <EmptyState icon={ShieldAlert} title="No open escalations found" body="The queue is empty, or the API returned no items."/>}</section>}
  </div>;
}
