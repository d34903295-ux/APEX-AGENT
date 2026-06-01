import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[APEX] Dashboard render error:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 20000, background: '#020203',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <div style={{
            maxWidth: 480, width: '100%', padding: 24, borderRadius: 12,
            background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.35)',
            fontFamily: "'Fira Code', monospace", fontSize: 12, color: '#f87171',
          }}>
            <div style={{ color: '#EDEDEF', fontSize: 14, marginBottom: 12, fontWeight: 600 }}>
              Error al cargar el dashboard
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: '0 0 16px', lineHeight: 1.5 }}>
              {this.state.error?.message || String(this.state.error)}
            </pre>
            <button
              type="button"
              onClick={() => {
                try {
                  sessionStorage.removeItem('apex_api_key');
                  localStorage.removeItem('apex_ai_key');
                } catch {}
                window.location.reload();
              }}
              style={{
                padding: '10px 16px', background: 'rgba(0,209,255,0.12)',
                border: '1px solid rgba(0,209,255,0.4)', color: '#00D1FF',
                borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              Volver al login
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
