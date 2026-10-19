import React from 'react';
export default function JsonViewer({ data }) {
  return <pre className="json-viewer">{JSON.stringify(data, null, 2)}</pre>;
}
