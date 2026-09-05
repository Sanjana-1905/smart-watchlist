import type { ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#app-content">Skip to content</a>
      <header className="command-strip">
        <div className="command-strip-inner">
          <Link className="product-wordmark" to="/">
            <span className="lens-mark" aria-hidden="true"><span /></span>
            <span>Smart Watchlist<span className="product-caption">Market attention, made personal</span></span>
          </Link>
          <nav aria-label="Main navigation" className="command-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'command-link is-active' : 'command-link'}>Attention</NavLink>
            <NavLink to="/explore" className={({ isActive }) => isActive ? 'command-link is-active' : 'command-link'}>Explore</NavLink>
          </nav>
          <div className="command-account">
            <span className="account-name">{user?.display_name || user?.email || 'Account'}</span>
            <button type="button" className="command-logout" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>
      <div id="app-content" tabIndex={-1}>{children}</div>
    </div>
  );
}
