import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { getBlogs, deleteBlog } from '../api/repurpose';
import ReactMarkdown from 'react-markdown';

export default function BlogHistory({ onClose }) {
  const { token } = useAuth();
  const [blogs, setBlogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBlog, setSelectedBlog] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef(null);

  useEffect(() => {
    loadBlogs();
  }, [token]);

  async function loadBlogs() {
    if (!token) return;
    
    setLoading(true);
    try {
      const data = await getBlogs(token);
      setBlogs(data);
    } catch (err) {
      console.error('Failed to load blogs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(blogId, e) {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this blog?')) return;
    
    setDeleting(blogId);
    try {
      await deleteBlog(token, blogId);
      setBlogs(blogs.filter(b => b.id !== blogId));
      if (selectedBlog?.id === blogId) {
        setSelectedBlog(null);
      }
    } catch (err) {
      console.error('Failed to delete blog:', err);
    } finally {
      setDeleting(null);
    }
  }

  function getPlainText() {
    if (contentRef.current) {
      return contentRef.current.innerText || contentRef.current.textContent;
    }
    return selectedBlog?.content || '';
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(getPlainText());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  function handleDownload() {
    const plainText = getPlainText();
    const blob = new Blob([plainText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedBlog?.title || 'blog'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  return (
    <div className="blog-history-overlay">
      <div className="blog-history-modal">
        <div className="blog-history-header">
          <h2>Your Blog History</h2>
          <button className="btn btn-secondary btn-icon" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="blog-history-content">
          {loading ? (
            <div className="blog-history-loading">
              <div className="loading-spinner" />
              <p>Loading your blogs...</p>
            </div>
          ) : blogs.length === 0 ? (
            <div className="blog-history-empty">
              <span style={{ fontSize: '3rem' }}>📝</span>
              <p>No blogs yet!</p>
              <p className="text-muted">Generated blogs will appear here.</p>
            </div>
          ) : (
            <div className="blog-history-layout">
              <div className="blog-list">
                {blogs.map((blog) => (
                  <div 
                    key={blog.id} 
                    className={`blog-list-item ${selectedBlog?.id === blog.id ? 'active' : ''}`}
                    onClick={() => setSelectedBlog(blog)}
                  >
                    <div className="blog-list-item-content">
                      <h4>{blog.title || 'Untitled Blog'}</h4>
                      <span className="blog-date">{formatDate(blog.created_at)}</span>
                    </div>
                    <button 
                      className="btn-delete"
                      onClick={(e) => handleDelete(blog.id, e)}
                      disabled={deleting === blog.id}
                    >
                      {deleting === blog.id ? '...' : '🗑'}
                    </button>
                  </div>
                ))}
              </div>

              <div className="blog-preview">
                {selectedBlog ? (
                  <>
                    <div className="blog-preview-header">
                      <div className="blog-preview-title">
                        <h3>{selectedBlog.title || 'Untitled Blog'}</h3>
                        {selectedBlog.youtube_url && (
                          <a 
                            href={selectedBlog.youtube_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="youtube-link"
                          >
                            🔗 Source
                          </a>
                        )}
                      </div>
                      <div className="blog-preview-actions">
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
                    <div className="blog-preview-content" ref={contentRef}>
                      <ReactMarkdown>{selectedBlog.content}</ReactMarkdown>
                    </div>
                  </>
                ) : (
                  <div className="blog-preview-empty">
                    <p>Select a blog to preview</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
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
