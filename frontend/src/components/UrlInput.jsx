import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import StyleSelector from './StyleSelector';
import OutputFormatSelector from './OutputFormatSelector';

export default function UrlInput({ 
  onSubmit, 
  styleText, 
  onStyleChange, 
  selectedStyleId, 
  onStyleIdChange,
  outputFormat,
  onOutputFormatChange
}) {
  const { user } = useAuth();
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const validateYouTubeUrl = (url) => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)/;
    return regex.test(url);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    if (!user) {
      setError('Please log in to generate content');
      return;
    }
    
    if (!url.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }
    
    if (!validateYouTubeUrl(url)) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    if (!outputFormat?.format) {
      setError('Please select an output format');
      return;
    }
    
    onSubmit(url, styleText, selectedStyleId, outputFormat);
  };

  return (
    <div className="card">
      <h2 className="card-title">Transform Video to Content</h2>
      <p className="card-subtitle">
        Paste a YouTube URL and we'll repurpose it for your platform
      </p>
      
      {!user && (
        <div className="auth-prompt" style={{
          backgroundColor: 'var(--surface-secondary)',
          padding: '1.5rem',
          borderRadius: '12px',
          marginBottom: '1.5rem',
          textAlign: 'center',
          border: '1px solid var(--border)'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>🔒</div>
          <h3 style={{ 
            fontSize: '1.25rem', 
            fontWeight: '600', 
            marginBottom: '0.5rem',
            color: 'var(--text-primary)'
          }}>
            Login Required
          </h3>
          <p style={{ 
            color: 'var(--text-secondary)', 
            marginBottom: '0',
            fontSize: '0.95rem'
          }}>
            Sign in with Google using the button in the top right to start generating content
          </p>
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label className="input-label">YouTube Video URL</label>
          <input
            type="text"
            className="input-field"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={!user}
          />
        </div>

        <OutputFormatSelector
          selectedFormat={outputFormat}
          onFormatChange={onOutputFormatChange}
          disabled={!user}
        />

        <StyleSelector
          selectedStyleId={selectedStyleId}
          onStyleSelect={onStyleIdChange}
          customStyle={styleText}
          onCustomStyleChange={onStyleChange}
          disabled={!user}
        />

        {error && (
          <div className="error-message">
            <span className="error-icon">⚠</span>
            <span className="error-text">{error}</span>
          </div>
        )}

        <button 
          type="submit" 
          className="btn btn-primary" 
          style={{ width: '100%', marginTop: '1.5rem' }}
          disabled={!user}
        >
          <span>Generate Content</span>
          <span>→</span>
        </button>
      </form>
    </div>
  );
}
