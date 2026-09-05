import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DEMO_PASSWORD = 'demo1234';

const DEMO_USERS = {
  momentum: {
    email: 'demo@smartwatchlist.dev',
    label: 'Momentum Investor',
    subtitle: 'Aggressive · Momentum · Short-term',
  },
  stability: {
    email: 'demo.stability@smartwatchlist.dev',
    label: 'Stability Investor',
    subtitle: 'Conservative · Stability · Long-term',
  },
};

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const [demoLoading, setDemoLoading] = useState<
    'momentum' | 'stability' | null
  >(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (submitting || demoLoading !== null) return;

    setError(null);
    setSubmitting(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Login failed'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDemoLogin = async (
    persona: 'momentum' | 'stability'
  ) => {
    if (submitting || demoLoading !== null) return;

    setError(null);
    setDemoLoading(persona);

    try {
      const demoUser = DEMO_USERS[persona];

      await login(
        demoUser.email,
        DEMO_PASSWORD
      );

      navigate('/');
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Demo login failed'
      );
    } finally {
      setDemoLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-white flex">
      {/* Left side - Product value proposition */}
      <div className="hidden lg:flex lg:w-1/2 bg-white flex-col justify-center px-16 xl:px-24 border-r border-slate-200">
        <div className="max-w-xl">
          <p className="text-xs font-bold tracking-[0.22em] uppercase text-indigo-600 mb-5">
            Smart Watchlist
          </p>

          <h1 className="text-4xl xl:text-5xl font-bold text-slate-950 leading-tight tracking-tight mb-6">
            See what changed.
            <br />
            Focus on what matters.
          </h1>

          <p className="text-lg xl:text-xl leading-8 text-slate-600 mb-10 max-w-lg">
            Smart Watchlist remembers what you last saw,
            measures what changed, and ranks market activity
            through your personal attention lens.
          </p>

          <div className="space-y-5">
            <div className="flex items-start gap-3 text-slate-700">
              <svg
                className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>

              <span>
                Tracks change since your last view
              </span>
            </div>

            <div className="flex items-start gap-3 text-slate-700">
              <svg
                className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>

              <span>
                Separates meaningful movement from market noise
              </span>
            </div>

            <div className="flex items-start gap-3 text-slate-700">
              <svg
                className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>

              <span>
                Explains why each stock deserves your attention
              </span>
            </div>
          </div>

          <div className="mt-14 pt-6 border-t border-slate-100">
            <p className="text-sm text-slate-500">
              Same market facts. Different investor lens.
            </p>
          </div>
        </div>
      </div>

      {/* Right side - Demo personas + manual login */}
      <div className="w-full lg:w-1/2 flex items-center justify-center px-6 sm:px-10 lg:px-12 py-12 lg:py-16 bg-slate-50">
        <div className="w-full max-w-md">
          {/* Mobile branding */}
          <div className="lg:hidden mb-10">
            <p className="text-xs font-bold tracking-[0.22em] uppercase text-indigo-600 mb-3">
              Smart Watchlist
            </p>

            <h1 className="text-3xl font-bold text-slate-950 tracking-tight">
              See what changed.
              <br />
              Focus on what matters.
            </h1>

            <p className="mt-4 text-slate-600">
              Market attention, personalized to how you invest.
            </p>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-950">
              Choose how to explore
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Compare how the same market activity can deserve
              different attention for different investors.
            </p>
          </div>

          {/* Demo persona buttons */}
          <div className="space-y-3">
            {/* Momentum Investor */}
            <button
              type="button"
              disabled={demoLoading !== null || submitting}
              onClick={() => handleDemoLogin('momentum')}
              className="
                w-full
                rounded-xl
                bg-slate-900
                px-5
                py-4
                text-left
                text-white
                transition
                hover:bg-slate-800
                focus:outline-none
                focus:ring-2
                focus:ring-indigo-500
                focus:ring-offset-2
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-base font-semibold">
                    {demoLoading === 'momentum'
                      ? 'Opening Momentum demo...'
                      : DEMO_USERS.momentum.label}
                  </div>

                  <div className="mt-1 text-sm text-slate-300">
                    {DEMO_USERS.momentum.subtitle}
                  </div>
                </div>

                <span
                  className="text-lg"
                  aria-hidden="true"
                >
                  →
                </span>
              </div>
            </button>

            {/* Stability Investor */}
            <button
              type="button"
              disabled={demoLoading !== null || submitting}
              onClick={() => handleDemoLogin('stability')}
              className="
                w-full
                rounded-xl
                border
                border-slate-300
                bg-white
                px-5
                py-4
                text-left
                text-slate-950
                transition
                hover:border-slate-400
                hover:bg-slate-50
                focus:outline-none
                focus:ring-2
                focus:ring-indigo-500
                focus:ring-offset-2
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-base font-semibold">
                    {demoLoading === 'stability'
                      ? 'Opening Stability demo...'
                      : DEMO_USERS.stability.label}
                  </div>

                  <div className="mt-1 text-sm text-slate-500">
                    {DEMO_USERS.stability.subtitle}
                  </div>
                </div>

                <span
                  className="text-lg"
                  aria-hidden="true"
                >
                  →
                </span>
              </div>
            </button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4 my-8">
            <div className="flex-1 h-px bg-slate-200" />

            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">
              Or sign in manually
            </span>

            <div className="flex-1 h-px bg-slate-200" />
          </div>

          {/* Manual login */}
          <form
            onSubmit={handleSubmit}
            noValidate
            className="space-y-4"
          >
            <div>
              <label
                htmlFor="login-email"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Email
              </label>

              <input
                type="email"
                id="login-email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) =>
                  setEmail(e.target.value)
                }
                className="
                  w-full
                  rounded-lg
                  border
                  border-slate-300
                  bg-white
                  px-3
                  py-2.5
                  text-sm
                  text-slate-950
                  outline-none
                  transition
                  placeholder:text-slate-400
                  focus:border-indigo-500
                  focus:ring-2
                  focus:ring-indigo-500/20
                "
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Password
              </label>

              <input
                type="password"
                id="login-password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) =>
                  setPassword(e.target.value)
                }
                className="
                  w-full
                  rounded-lg
                  border
                  border-slate-300
                  bg-white
                  px-3
                  py-2.5
                  text-sm
                  text-slate-950
                  outline-none
                  transition
                  placeholder:text-slate-400
                  focus:border-indigo-500
                  focus:ring-2
                  focus:ring-indigo-500/20
                "
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5"
              >
                <p className="text-sm font-medium text-red-700">
                  {error}
                </p>
              </div>
            )}

            {/* Black Sign In button */}
            <button
              type="submit"
              disabled={demoLoading !== null || submitting}
              className="
                w-full
                rounded-lg
                border
                border-slate-950
                bg-slate-950
                py-2.5
                text-sm
                font-semibold
                text-white
                shadow-sm
                transition
                hover:bg-slate-900
                hover:border-slate-900
                focus:outline-none
                focus:ring-2
                focus:ring-indigo-500
                focus:ring-offset-2
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >
              {submitting
                ? 'Signing in...'
                : 'Sign in'}
            </button>
          </form>

          <p className="text-sm text-slate-600 mt-8 text-center">
            No account?{' '}
            <Link
              to="/register"
              className="font-semibold text-indigo-600 hover:text-indigo-700 hover:underline"
            >
              Create an account
            </Link>
          </p>

          <p className="mt-8 text-center text-xs leading-5 text-slate-400">
            Demo personas use the same market data.
            Their attention rankings differ because their
            personal lenses differ.
          </p>
        </div>
      </div>
    </div>
  );
}