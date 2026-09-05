import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DEMO_EMAIL = 'demo@smartwatchlist.dev';
const DEMO_PASSWORD = 'demo1234';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting || demoLoading) return;
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDemoLogin = async () => {
    if (submitting || demoLoading) return;
    setError(null);
    setDemoLoading(true);
    try {
      await login(DEMO_EMAIL, DEMO_PASSWORD);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo login failed');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Left side - Value Prop */}
      <div className="hidden lg:flex lg:w-1/2 bg-white flex-col justify-center px-16 xl:px-24 border-r border-slate-200">
        <h1 className="text-3xl font-bold text-slate-900 leading-tight mb-4">
          Markets move.<br/>
          Your attention shouldn't have to chase them.
        </h1>
        <p className="text-lg text-slate-600 mb-10 max-w-md">
          Smart Watchlist remembers what you last saw and surfaces only what changed enough to matter.
        </p>
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-slate-700">
            <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            <span>Remembers your last view</span>
          </div>
          <div className="flex items-center gap-3 text-slate-700">
            <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            <span>Filters ordinary market noise</span>
          </div>
          <div className="flex items-center gap-3 text-slate-700">
            <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            <span>Explains every attention decision</span>
          </div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center px-8 sm:px-12 py-16">
        <div className="w-full max-w-sm">
          <div className="lg:hidden mb-12">
            <h1 className="text-2xl font-bold text-slate-900">Smart Watchlist</h1>
          </div>

          <h2 className="text-xl font-bold text-slate-900 mb-8">Sign in to your account</h2>

          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={demoLoading || submitting}
            className="w-full bg-slate-900 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-slate-800 disabled:opacity-50 transition-colors mb-6 shadow-sm"
          >
            {demoLoading ? 'Loading demo...' : 'Continue as Demo User →'}
          </button>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">or sign in manually</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                id="login-email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-shadow"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
              <input
                type="password"
                id="login-password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-shadow"
                placeholder="••••••••"
              />
            </div>

            {error && <p role="alert" className="text-sm text-red-600 font-medium">{error}</p>}

            <button
              type="submit"
              disabled={demoLoading || submitting}
              className="w-full border border-slate-300 text-slate-900 bg-white rounded-lg py-2.5 text-sm font-semibold hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-sm mt-2"
            >
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="text-sm text-slate-600 mt-8 text-center">
            No account?{' '}
            <Link to="/register" className="text-slate-900 font-semibold hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
