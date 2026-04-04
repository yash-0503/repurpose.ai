import { useState } from 'react';

const OUTPUT_FORMATS = {
  blog: {
    id: 'blog',
    icon: '📝',
    title: 'Full Blog',
    description: 'Detailed article with sections & headings',
    length: '1000-2000 words',
    subOptions: null
  },
  linkedin: {
    id: 'linkedin',
    icon: '💼',
    title: 'LinkedIn Post',
    description: 'Professional, story-driven, engaging',
    length: 'Customizable',
    subOptions: [
      { id: 'short', label: 'Short', desc: '100-200 words' },
      { id: 'medium', label: 'Medium', desc: '200-400 words' },
      { id: 'long', label: 'Long', desc: '500 words' }
    ]
  },
  twitter: {
    id: 'twitter',
    icon: '🐦',
    title: 'Twitter/X',
    description: 'Punchy, hook-driven content',
    length: 'Tweet or Thread',
    subOptions: [
      { id: 'single', label: 'Single Tweet', desc: '280 chars max' },
      { id: 'thread', label: 'Thread', desc: '5-10 connected tweets' }
    ]
  }
};

export default function OutputFormatSelector({ selectedFormat, onFormatChange, disabled = false }) {
  const [subOption, setSubOption] = useState('medium'); // Default for linkedin
  const [twitterOption, setTwitterOption] = useState('thread'); // Default for twitter

  const handleFormatSelect = (formatId) => {
    if (disabled) return;
    let option = null;
    if (formatId === 'linkedin') {
      option = subOption;
    } else if (formatId === 'twitter') {
      option = twitterOption;
    }
    onFormatChange({ format: formatId, option });
  };

  const handleSubOptionChange = (formatId, optionId) => {
    if (disabled) return;
    if (formatId === 'linkedin') {
      setSubOption(optionId);
      onFormatChange({ format: 'linkedin', option: optionId });
    } else if (formatId === 'twitter') {
      setTwitterOption(optionId);
      onFormatChange({ format: 'twitter', option: optionId });
    }
  };

  return (
    <div className="output-format-selector">
      <label className="input-label">Output Format</label>
      <p className="format-hint">Choose where you'll share this content</p>
      
      <div className="format-options" style={{ opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
        {Object.values(OUTPUT_FORMATS).map((format) => (
          <div key={format.id} className="format-option-wrapper">
            <div 
              className={`format-option ${selectedFormat?.format === format.id ? 'active' : ''}`}
              onClick={() => handleFormatSelect(format.id)}
            >
              <div className="format-icon">{format.icon}</div>
              <div className="format-info">
                <h4>{format.title}</h4>
                <p>{format.description}</p>
                <span className="format-length">{format.length}</span>
              </div>
              <div className="format-check">
                {selectedFormat?.format === format.id && '✓'}
              </div>
            </div>

            {/* Sub-options for LinkedIn */}
            {format.id === 'linkedin' && selectedFormat?.format === 'linkedin' && (
              <div className="format-sub-options">
                {format.subOptions.map((opt) => (
                  <label key={opt.id} className="sub-option">
                    <input
                      type="radio"
                      name="linkedin-length"
                      checked={subOption === opt.id}
                      onChange={() => handleSubOptionChange('linkedin', opt.id)}
                      disabled={disabled}
                    />
                    <span className="sub-option-label">{opt.label}</span>
                    <span className="sub-option-desc">{opt.desc}</span>
                  </label>
                ))}
              </div>
            )}

            {/* Sub-options for Twitter */}
            {format.id === 'twitter' && selectedFormat?.format === 'twitter' && (
              <div className="format-sub-options">
                {format.subOptions.map((opt) => (
                  <label key={opt.id} className="sub-option">
                    <input
                      type="radio"
                      name="twitter-type"
                      checked={twitterOption === opt.id}
                      onChange={() => handleSubOptionChange('twitter', opt.id)}
                      disabled={disabled}
                    />
                    <span className="sub-option-label">{opt.label}</span>
                    <span className="sub-option-desc">{opt.desc}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

