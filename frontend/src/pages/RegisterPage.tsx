import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (submitting) return;

    setError(null);

    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setSubmitting(true);

    try {
      await register(
        email.trim(),
        password,
        displayName.trim() || undefined
      );

      navigate('/');
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Registration failed'
      );
    } finally {
      setSubmitting(false);
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
            Smart Watchlist remembers what you last saw, measures what changed,
            and ranks market activity through your personal attention lens.
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
              Start with the market. Build a watchlist that becomes personal over time.
            </p>
          </div>
        </div>
      </div>

      {/* Right side - Registration form */}
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
              Build your own attention lens around the companies you care about.
            </p>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-950">
              Create your account
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Start with an empty watchlist, explore the market, and choose
              exactly what you want Smart Watchlist to track.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            noValidate
            className="space-y-5"
          >
            <div>
              <label
                htmlFor="register-name"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Name{' '}
                <span className="font-normal text-slate-400">
                  (optional)
                </span>
              </label>

              <input
                type="text"
                id="register-name"
                autoComplete="name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={submitting}
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
                  disabled:cursor-not-allowed
                  disabled:bg-slate-100
                "
                placeholder="Jane Doe"
              />
            </div>

            <div>
              <label
                htmlFor="register-email"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Email
              </label>

              <input
                type="email"
                id="register-email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
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
                  disabled:cursor-not-allowed
                  disabled:bg-slate-100
                "
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="register-password"
                className="block text-sm font-medium text-slate-700 mb-1.5"
              >
                Password
              </label>

              <input
                type="password"
                id="register-password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
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
                  disabled:cursor-not-allowed
                  disabled:bg-slate-100
                "
                placeholder="At least 8 characters"
              />

              <p className="mt-1.5 text-xs text-slate-400">
                Minimum 8 characters.
              </p>
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

            <button
              type="submit"
              disabled={submitting}
              className="
                w-full
                rounded-lg
                bg-slate-950
                py-2.5
                text-sm
                font-semibold
                text-white
                shadow-sm
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
              {submitting
                ? 'Creating account...'
                : 'Create account'}
            </button>
          </form>

          <p className="text-sm text-slate-600 mt-8 text-center">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-indigo-600 hover:text-indigo-700 hover:underline"
            >
              Sign in
            </Link>
          </p>

          <p className="mt-8 text-center text-xs leading-5 text-slate-400">
            New accounts start with no preselected watchlist.
            You choose what to follow.
          </p>
        </div>
      </div>
    </div>
  );
}