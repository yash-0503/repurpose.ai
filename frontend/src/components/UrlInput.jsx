import { useState } from 'react';
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
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const validateYouTubeUrl = (url) => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)/;
    return regex.test(url);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
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
      
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label className="input-label">YouTube Video URL</label>
          <input
            type="text"
            className="input-field"
            placeholder="https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        <OutputFormatSelector
          selectedFormat={outputFormat}
          onFormatChange={onOutputFormatChange}
        />

        <StyleSelector
          selectedStyleId={selectedStyleId}
          onStyleSelect={onStyleIdChange}
          customStyle={styleText}
          onCustomStyleChange={onStyleChange}
        />

        {error && (
          <div className="error-message">
            <span className="error-icon">⚠</span>
            <span className="error-text">{error}</span>
          </div>
        )}

        <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1.5rem' }}>
          <span>Generate Content</span>
          <span>→</span>
        </button>
      </form>
    </div>
  );
}
