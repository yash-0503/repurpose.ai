import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { createStyle } from '../api/repurpose';

export default function StyleSelector({
  styleMode,
  onStyleModeChange,
  selectedStyleId,
  onStyleSelect,
  customStyle,
  onCustomStyleChange,
  disabled = false,
}) {
  const { user, token, styles, defaultStyleId, loading: authLoading, refetchUserData, addStyle } = useAuth();
  const [showCustom, setShowCustom] = useState(false);
  const [styleName, setStyleName] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const hasAutoSelected = useRef(false);

  useEffect(() => {
    if (!user || authLoading || hasAutoSelected.current) return;

    if (styles.length > 0) {
      const preferred = styles.find((s) => s.id === defaultStyleId) || styles[0];
      onStyleModeChange('saved');
      onStyleSelect(preferred.id);
    } else {
      onStyleModeChange('none');
      onStyleSelect(null);
    }

    hasAutoSelected.current = true;
  }, [user, authLoading, styles, defaultStyleId, onStyleModeChange, onStyleSelect]);

  const handleModeChange = (newMode) => {
    if (disabled) return;
    setSaveError('');
    setSaveSuccess(false);
    onStyleModeChange(newMode);

    if (newMode === 'none') {
      onStyleSelect(null);
      onCustomStyleChange('');
      setStyleName('');
    } else if (newMode === 'saved') {
      onCustomStyleChange('');
      setStyleName('');
      if (styles.length > 0) {
        const preferred =
          styles.find((s) => s.id === selectedStyleId) ||
          styles.find((s) => s.id === defaultStyleId) ||
          styles[0];
        onStyleSelect(preferred.id);
      }
    } else if (newMode === 'custom') {
      onStyleSelect(null);
    }
  };

  const handleSavedStyleSelect = (styleId) => {
    if (disabled) return;
    onStyleSelect(styleId);
  };

  const handleSaveStyle = async () => {
    const name = styleName.trim();
    const sample = customStyle.trim();

    if (!token || !name || sample.length < 50) return;

    setSaving(true);
    setSaveError('');
    setSaveSuccess(false);

    try {
      const saved = await createStyle(token, name, sample);
      addStyle(saved);
      await refetchUserData();
      onStyleModeChange('saved');
      onStyleSelect(saved.id);
      onCustomStyleChange('');
      setStyleName('');
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setSaveError(err.message || 'Failed to save style');
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return (
      <div className={`collapsible ${showCustom ? 'open' : ''}`} style={{ opacity: disabled ? 0.5 : 1 }}>
        <div
          className="collapsible-header"
          onClick={() => !disabled && setShowCustom(!showCustom)}
          style={{ pointerEvents: disabled ? 'none' : 'auto' }}
        >
          <div className="collapsible-title">
            <span className="collapsible-icon">✍</span>
            <span>Custom Writing Style (Optional)</span>
          </div>
          <span className="collapsible-arrow">▼</span>
        </div>
        <div className="collapsible-content">
          <p className="style-hint">
            Paste a sample of your writing to match the style. Log in to save styles for reuse.
          </p>
          <textarea
            className="input-field"
            placeholder="Paste a sample of your writing here..."
            value={customStyle}
            onChange={(e) => onCustomStyleChange(e.target.value)}
            disabled={disabled}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="style-selector" style={{ opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
      <label className="input-label">Writing Style</label>

      <div className="style-options">
        <label className="style-option">
          <input
            type="radio"
            name="styleMode"
            checked={styleMode === 'none'}
            onChange={() => handleModeChange('none')}
            disabled={disabled}
          />
          <div className="style-option-content">
            <span className="style-option-label">📝 Default</span>
            <span className="style-option-desc">Professional, easy to read — no custom style</span>
          </div>
        </label>

        <label className={`style-option ${styles.length === 0 ? 'disabled' : ''}`}>
          <input
            type="radio"
            name="styleMode"
            checked={styleMode === 'saved'}
            onChange={() => handleModeChange('saved')}
            disabled={disabled || styles.length === 0}
          />
          <div className="style-option-content">
            <span className="style-option-label">✨ Your Saved Styles</span>
            <span className="style-option-desc">
              {styles.length > 0
                ? `${styles.length} saved style${styles.length === 1 ? '' : 's'} — pick one below`
                : 'Save a style first to use this option'}
            </span>
          </div>
        </label>

        <label className="style-option">
          <input
            type="radio"
            name="styleMode"
            checked={styleMode === 'custom'}
            onChange={() => handleModeChange('custom')}
            disabled={disabled}
          />
          <div className="style-option-content">
            <span className="style-option-label">✍️ Enter New Style</span>
            <span className="style-option-desc">Name it, paste sample text, and save</span>
          </div>
        </label>
      </div>

      {styleMode === 'saved' && (
        <div className="style-saved-list">
          {styles.length === 0 ? (
            <p className="style-hint">No saved styles yet. Use "Enter New Style" to create one.</p>
          ) : (
            <>
              <p className="style-saved-list-label">Select a style to use:</p>
              {styles.map((style) => (
                <label
                  key={style.id}
                  className={`style-option style-saved-item ${selectedStyleId === style.id ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="savedStyle"
                    checked={selectedStyleId === style.id}
                    onChange={() => handleSavedStyleSelect(style.id)}
                    disabled={disabled}
                  />
                  <div className="style-option-content">
                    <span className="style-option-label">{style.name}</span>
                    <span className="style-option-desc">
                      {style.style_guide.length} chars · Saved {new Date(style.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </label>
              ))}
            </>
          )}
        </div>
      )}

      {styleMode === 'custom' && (
        <div className="custom-style-input">
          <p className="style-hint">
            Give your style a name and paste a writing sample. It will be saved as-is and used when you generate content.
          </p>
          <div className="input-group" style={{ marginBottom: '0.75rem' }}>
            <label className="input-label">Style Name</label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Casual Blog, LinkedIn Voice, Technical..."
              value={styleName}
              onChange={(e) => {
                setStyleName(e.target.value);
                setSaveError('');
                setSaveSuccess(false);
              }}
              disabled={disabled || saving}
              maxLength={100}
            />
          </div>
          <textarea
            className="input-field"
            placeholder="Paste a sample of your writing here (at least 50 characters)..."
            value={customStyle}
            onChange={(e) => {
              onCustomStyleChange(e.target.value);
              setSaveError('');
              setSaveSuccess(false);
            }}
            disabled={disabled || saving}
          />
          {customStyle.trim().length > 0 && customStyle.trim().length < 50 && (
            <p className="style-hint" style={{ color: 'var(--error)' }}>
              Please enter at least 50 characters.
            </p>
          )}
          {!styleName.trim() && customStyle.trim().length >= 50 && (
            <p className="style-hint" style={{ color: 'var(--error)' }}>
              Please enter a name for your style.
            </p>
          )}
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginTop: '0.75rem' }}
            onClick={handleSaveStyle}
            disabled={disabled || saving || !styleName.trim() || customStyle.trim().length < 50}
          >
            {saving ? 'Saving...' : 'Save Style'}
          </button>
          {saveError && (
            <p className="style-hint" style={{ color: 'var(--error)', marginTop: '0.5rem' }}>
              {saveError}
            </p>
          )}
          {saveSuccess && (
            <p className="style-hint" style={{ color: 'var(--success, #22c55e)', marginTop: '0.5rem' }}>
              Style saved and selected! Ready to use when you generate content.
            </p>
          )}
        </div>
      )}

      {authLoading && <p className="style-loading">Loading your styles...</p>}

      {!authLoading && styles.length === 0 && styleMode !== 'custom' && (
        <p className="style-hint first-time">
          💡 First time? Choose "Enter New Style", give it a name, paste a sample, and click Save Style.
        </p>
      )}
    </div>
  );
}
