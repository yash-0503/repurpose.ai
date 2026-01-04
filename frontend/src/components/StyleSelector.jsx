import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getStyles } from '../api/repurpose';

export default function StyleSelector({ 
  selectedStyleId, 
  onStyleSelect, 
  customStyle, 
  onCustomStyleChange 
}) {
  const { user, token } = useAuth();
  const [styles, setStyles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('default'); // 'your_style', 'default', 'custom'
  const [showCustom, setShowCustom] = useState(false);

  // Find user's personal analyzed style (first one or one named "My Style")
  const userStyle = styles.find(s => s.name === 'My Style') || styles[0];

  useEffect(() => {
    async function loadStyles() {
      if (!user || !token) return;
      
      setLoading(true);
      try {
        const data = await getStyles(token);
        setStyles(data);
        // If user has a style, default to using it
        if (data.length > 0) {
          setMode('your_style');
          const myStyle = data.find(s => s.name === 'My Style') || data[0];
          onStyleSelect(myStyle.id);
        }
      } catch (err) {
        console.error('Failed to load styles:', err);
      } finally {
        setLoading(false);
      }
    }
    loadStyles();
  }, [user, token]);

  const handleModeChange = (newMode) => {
    setMode(newMode);
    if (newMode === 'default') {
      onStyleSelect(null);
      onCustomStyleChange('');
    } else if (newMode === 'your_style' && userStyle) {
      onStyleSelect(userStyle.id);
      onCustomStyleChange('');
    } else if (newMode === 'custom') {
      onStyleSelect(null);
    }
  };

  // If not logged in, show simple custom style input
  if (!user) {
    return (
      <div className={`collapsible ${showCustom ? 'open' : ''}`}>
        <div 
          className="collapsible-header"
          onClick={() => setShowCustom(!showCustom)}
        >
          <div className="collapsible-title">
            <span className="collapsible-icon">✍</span>
            <span>Custom Writing Style (Optional)</span>
          </div>
          <span className="collapsible-arrow">▼</span>
        </div>
        <div className="collapsible-content">
          <p className="style-hint">
            Paste a sample of your writing to match the style. We'll analyze it and generate the blog in your voice.
          </p>
          <textarea
            className="input-field"
            placeholder="Paste a sample of your writing here (at least 100 characters)..."
            value={customStyle}
            onChange={(e) => onCustomStyleChange(e.target.value)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="style-selector">
      <label className="input-label">Writing Style</label>
      
      <div className="style-options">
        {/* Option 1: Your analyzed style */}
        {userStyle && (
          <label className="style-option">
            <input 
              type="radio" 
              name="styleMode" 
              checked={mode === 'your_style'}
              onChange={() => handleModeChange('your_style')}
            />
            <div className="style-option-content">
              <span className="style-option-label">✨ Your Style</span>
              <span className="style-option-desc">Use your analyzed writing style</span>
            </div>
          </label>
        )}

        {/* Option 2: Default/No style */}
        <label className="style-option">
          <input 
            type="radio" 
            name="styleMode" 
            checked={mode === 'default'}
            onChange={() => handleModeChange('default')}
          />
          <div className="style-option-content">
            <span className="style-option-label">📝 Default</span>
            <span className="style-option-desc">Professional, easy to read</span>
          </div>
        </label>

        {/* Option 3: Enter new/custom style */}
        <label className="style-option">
          <input 
            type="radio" 
            name="styleMode" 
            checked={mode === 'custom'}
            onChange={() => handleModeChange('custom')}
          />
          <div className="style-option-content">
            <span className="style-option-label">✍️ Enter New Style</span>
            <span className="style-option-desc">Paste sample text to analyze</span>
          </div>
        </label>
      </div>

      {mode === 'custom' && (
        <div className="custom-style-input">
          <p className="style-hint">
            Paste a sample of writing. We'll analyze it and save it as your style for future blogs.
          </p>
          <textarea
            className="input-field"
            placeholder="Paste a sample of your writing here (at least 100 characters)..."
            value={customStyle}
            onChange={(e) => onCustomStyleChange(e.target.value)}
          />
        </div>
      )}

      {loading && <p className="style-loading">Loading your styles...</p>}
      
      {!loading && !userStyle && user && (
        <p className="style-hint first-time">
          💡 First time? Enter a sample of your writing above and we'll save your style for future blogs!
        </p>
      )}
    </div>
  );
}
