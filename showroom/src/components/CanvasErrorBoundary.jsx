import { Component } from 'react';

// [AGENT NOTE]: ErrorBoundary around the Canvas — ensures the 2D UI
// (ProductSelector) stays mounted even if the 3D scene crashes.

export default class CanvasErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[Engine] Canvas crashed:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: '12px',
          color: '#9e9a94',
          fontFamily: 'Outfit, sans-serif',
        }}>
          <div style={{ fontSize: '2.5rem' }}>🍞</div>
          <div style={{ fontSize: '0.9rem' }}>
            3D scene unavailable
          </div>
          <div style={{ fontSize: '0.72rem', opacity: 0.6, maxWidth: 260, textAlign: 'center' }}>
            {this.state.error?.message ?? 'Add GLB files to /public/models/ to load products.'}
          </div>
          <button
            style={{
              marginTop: 8,
              padding: '8px 16px',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 8,
              background: 'rgba(255,255,255,0.06)',
              color: '#f0ede8',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '0.8rem',
            }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
