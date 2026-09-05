import { useState, useEffect, type ReactNode, useRef } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api, type Stock } from '../services/api';

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    api.getAllStocks().then(s => {
      if (active) setStocks(s);
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const sym = searchQuery.trim().toUpperCase();
    if (sym) {
      navigate(`/stock/${encodeURIComponent(sym)}`);
      setSearchQuery('');
      setShowResults(false);
    }
  };

  const matchingStocks = searchQuery.trim().length >= 1
    ? stocks.filter(s =>
        s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.company_name.toLowerCase().includes(searchQuery.toLowerCase())
      ).slice(0, 6)
    : [];

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
            <NavLink to="/" end className={({ isActive }) => isActive ? 'command-link is-active' : 'command-link'} aria-current={undefined}>Attention</NavLink>
            <NavLink to="/explore" className={({ isActive }) => isActive ? 'command-link is-active' : 'command-link'}>Explore</NavLink>
            <NavLink to="/profile" className={({ isActive }) => isActive ? 'command-link is-active' : 'command-link'}>Profile</NavLink>
          </nav>

          {/* Global Search — searches the whole catalog */}
          <div ref={searchRef} style={{ position: 'relative', flex: '1 1 180px', maxWidth: '240px' }}>
            <form onSubmit={handleSearchSubmit} role="search" aria-label="Search catalog">
              <label htmlFor="global-search" className="sr-only">Search all companies</label>
              <input
                id="global-search"
                type="search"
                placeholder="Search symbol or company…"
                value={searchQuery}
                onChange={e => { setSearchQuery(e.target.value); setShowResults(true); }}
                onFocus={() => setShowResults(true)}
                autoComplete="off"
                style={{
                  width: '100%',
                  padding: '7px 12px',
                  fontSize: '12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  color: '#0f172a',
                  boxSizing: 'border-box',
                }}
              />
            </form>
            {showResults && matchingStocks.length > 0 && (
              <ul
                role="listbox"
                aria-label="Search results"
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
                  margin: '4px 0 0',
                  padding: 0,
                  listStyle: 'none',
                  zIndex: 100,
                  maxHeight: '300px',
                  overflowY: 'auto',
                }}
              >
                {matchingStocks.map(stock => (
                  <li key={stock.symbol} role="option" aria-selected="false">
                    <button
                      type="button"
                      onClick={() => {
                        navigate(`/stock/${stock.symbol}`);
                        setSearchQuery('');
                        setShowResults(false);
                      }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 12px',
                        border: 0,
                        borderBottom: '1px solid #f1f5f9',
                        background: 'transparent',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '8px',
                      }}
                    >
                      <strong style={{ color: '#4f46e5', flexShrink: 0 }}>{stock.symbol}</strong>
                      <span style={{ color: '#64748b', fontSize: '11px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                        {stock.company_name}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

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
