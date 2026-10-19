import React from 'react';
import { AlertCircle, CheckCircle2, LoaderCircle, Wifi, WifiOff } from 'lucide-react';

export function Button({ children, icon: Icon, variant = 'primary', loading = false, disabled = false, block = false, size = '', className = '', ...props }) {
  return <button className={`btn btn-${variant} ${block ? 'btn-block' : ''} ${size === 'small' ? 'btn-small' : ''} ${className}`} disabled={disabled || loading} {...props}>{loading ? <LoaderCircle className="spin" size={16} /> : Icon ? <Icon size={16} /> : null}{children}</button>;
}
export function StatusPill({ status = 'unknown' }) {
  const normalized = String(status).toLowerCase();
  const good = ['ok','healthy','answered','approved','resolved','success','sent','processed','ready'].includes(normalized);
  const bad = ['error','failed','needs_human','rejected','critical','unavailable'].includes(normalized);
  return <span className={`status-pill ${good ? 'is-good' : bad ? 'is-bad' : 'is-warn'}`}><span className="status-dot" />{String(status).replaceAll('_',' ')}</span>;
}
export function Notice({ type = 'error', children, onClose }) {
  if (!children) return null;
  const Icon = type === 'success' ? CheckCircle2 : AlertCircle;
  return <div className={`notice notice-${type}`}><Icon size={17} /><div>{children}</div>{onClose && <button className="icon-button" onClick={onClose} aria-label="Dismiss">×</button>}</div>;
}
export function ServiceDot({ state }) { return <span className={`service-dot ${state === 'ok' ? 'online' : state === 'checking' ? 'checking' : 'offline'}`} title={state} />; }
export function Field({ label, hint, children }) { return <label className="field"><span className="field-label">{label}</span>{children}{hint && <span className="field-hint">{hint}</span>}</label>; }
export function EmptyState({ icon: Icon, title, body, children }) { return <div className="empty-state">{Icon && <div className="empty-icon"><Icon size={23} /></div>}<h3>{title}</h3><p>{body}</p>{children}</div>; }
export function Loading({ label = 'Loading…' }) { return <div className="loading"><LoaderCircle className="spin" size={18} />{label}</div>; }
export function ConnectionTag({ online }) { return <span className={`connection-tag ${online ? 'online' : 'offline'}`}>{online ? <Wifi size={13} /> : <WifiOff size={13} />}{online ? 'Connected' : 'Unavailable'}</span>; }
