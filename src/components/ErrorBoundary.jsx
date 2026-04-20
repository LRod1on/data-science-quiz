import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          color: '#fff',
          padding: '48px',
          fontSize: '28px',
          lineHeight: '1.5',
          fontFamily: 'inherit',
        }}>
          <div style={{ opacity: 0.6, marginBottom: '16px' }}>Что-то пошло не так</div>
          <div>{this.state.message}</div>
        </div>
      );
    }
    return this.props.children;
  }
}
