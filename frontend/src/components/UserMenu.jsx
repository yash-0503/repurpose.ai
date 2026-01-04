import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function UserMenu({ onShowHistory }) {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  return (
    <div className="user-menu" ref={menuRef}>
      <button 
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        {user.avatar_url ? (
          <img src={user.avatar_url} alt={user.name} className="user-avatar" />
        ) : (
          <div className="user-avatar-placeholder">
            {user.name?.charAt(0) || user.email?.charAt(0)}
          </div>
        )}
        <span className="user-name">{user.name || user.email}</span>
        <span className="dropdown-arrow">▼</span>
      </button>

      {isOpen && (
        <div className="user-menu-dropdown">
          <div className="user-menu-header">
            <span className="user-email">{user.email}</span>
          </div>
          <div className="user-menu-divider" />
          <button 
            className="user-menu-item"
            onClick={() => {
              onShowHistory?.();
              setIsOpen(false);
            }}
          >
            <span>📚</span>
            <span>Content History</span>
          </button>
          <div className="user-menu-divider" />
          <button 
            className="user-menu-item"
            onClick={() => {
              logout();
              setIsOpen(false);
            }}
          >
            <span>🚪</span>
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}

