import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function BlogOutput({ content, onReset, outputType = 'Blog' }) {
  const [copied, setCopied] = useState(false);
  const contentRef = useRef(null);
  const [plainText, setPlainText] = useState('');

  // Extract plain text from rendered markdown
  useEffect(() => {
    if (contentRef.current) {
      setPlainText(contentRef.current.innerText || contentRef.current.textContent);
    }
  }, [content]);

  const handleCopy = async () => {
    try {
      // Copy the plain text version (no markdown syntax)
      await navigator.clipboard.writeText(plainText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    // Download as plain text file
    const blob = new Blob([plainText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `repurpose-${outputType.toLowerCase().replace(/\s+/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card blog-output">
      <div className="blog-header">
        <div>
          <h2 className="card-title">Your {outputType} is Ready!</h2>
          <p className="card-subtitle" style={{ marginBottom: 0 }}>
            Here's your AI-generated content
          </p>
        </div>
        <div className="blog-actions">
          <button 
            className="btn btn-secondary btn-icon" 
            onClick={handleCopy}
            title="Copy as plain text"
          >
            {copied ? '✓' : '📋'}
          </button>
          <button 
            className="btn btn-secondary btn-icon" 
            onClick={handleDownload}
            title="Download as TXT"
          >
            ⬇
          </button>
        </div>
      </div>

      <div className="blog-content" ref={contentRef}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>

      <div className="new-generation">
        <button className="btn btn-primary" onClick={onReset}>
          <span>↺</span>
          <span>Generate Another</span>
        </button>
      </div>

      {copied && (
        <div className="toast success">
          <span>✓</span>
          <span>Copied to clipboard!</span>
        </div>
      )}
    </div>
  );
}
