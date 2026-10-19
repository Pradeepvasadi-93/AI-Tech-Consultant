const TASK1_KEY = import.meta.env.VITE_TASK1_API_KEY || '';

export async function api(path, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) };
  if (TASK1_KEY && path.startsWith('/api/task1/')) headers['X-API-Key'] = TASK1_KEY;
  let response;
  try {
    response = await fetch(path, { ...options, headers, signal: options.signal });
  } catch (error) {
    throw new Error(`Cannot connect to ${path.split('/').slice(0, 3).join('/')}. Confirm that the backend is running. (${error.message})`);
  }
  const raw = await response.text();
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch { data = raw; }
  if (!response.ok) {
    const detail = typeof data === 'string' ? data : data?.detail?.message || data?.detail || data?.message || JSON.stringify(data);
    throw new Error(`${response.status} ${response.statusText}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
  }
  return data;
}

export const task1 = (path, options) => api(`/api/task1${path}`, options);
export const task2 = (path, options) => api(`/api/task2${path}`, options);
export const task3 = (path, options) => api(`/api/task3${path}`, options);
export const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
export const paths = {
  task2Emails: import.meta.env.VITE_TASK2_EMAILS_PATH || '/emails',
  task2Process: import.meta.env.VITE_TASK2_PROCESS_PATH || '/emails/process',
  task2ReviewSuffix: import.meta.env.VITE_TASK2_REVIEW_SUFFIX || '/review',
  task2FeedbackSuffix: import.meta.env.VITE_TASK2_FEEDBACK_SUFFIX || '/feedback',
  task2SendSuffix: import.meta.env.VITE_TASK2_SEND_SUFFIX || '/send'
};

export function explainError(error) {
  const message = error?.message || String(error);
  if (message.includes('401')) return `${message}. Task 1 may require VITE_TASK1_API_KEY in frontend/.env.`;
  if (message.includes('404')) return `${message}. Check the route path in the API's /docs page.`;
  return message;
}
