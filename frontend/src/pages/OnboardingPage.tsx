import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  onboardingApi,
  type AttentionPriority,
  type MovementSensitivity,
  type TimeHorizonAnswer,
} from '../services/api';

interface Option<T extends string> {
  value: T;
  title: string;
  subtitle: string;
}

const Q1_OPTIONS: Option<AttentionPriority>[] = [
  { value: 'UPWARD_MOVEMENT', title: 'Strong upward movement', subtitle: 'Notice unusual market strength' },
  { value: 'DOWNSIDE_RISK', title: 'Unusual downside', subtitle: 'Surface instability quickly' },
  { value: 'BALANCED', title: 'Both equally', subtitle: 'Keep my attention balanced' },
];

const Q2_OPTIONS: Option<MovementSensitivity>[] = [
  { value: 'SELECTIVE', title: 'Only larger, unusual moves', subtitle: 'Keep the noise down' },
  { value: 'BALANCED', title: 'A balanced amount', subtitle: 'Moderate sensitivity' },
  { value: 'HIGH_MOVEMENT', title: 'Stronger movement, sooner', subtitle: 'I want to notice it early' },
];

const Q3_OPTIONS: Option<TimeHorizonAnswer>[] = [
  { value: 'SHORT_TERM', title: 'Days to weeks', subtitle: 'I check in often' },
  { value: 'LONG_TERM', title: 'Months or longer', subtitle: 'I check in occasionally' },
];

const LABELS: Record<string, string> = {
  MOMENTUM: 'Momentum focused',
  STABILITY: 'Stability focused',
  BALANCED: 'Balanced focus',
  CONSERVATIVE: 'Lower movement sensitivity',
  AGGRESSIVE: 'Higher movement sensitivity',
  SHORT_TERM: 'Short-term horizon',
  LONG_TERM: 'Long-term horizon',
};

type Step = 1 | 2 | 3 | 'result';

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>(1);
  const [attentionPriority, setAttentionPriority] = useState<AttentionPriority | null>(null);
  const [movementSensitivity, setMovementSensitivity] = useState<MovementSensitivity | null>(null);
  const [result, setResult] = useState<{ risk_profile: string; attention_style: string; time_horizon: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);

  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  const submit = async (finalHorizon: TimeHorizonAnswer) => {
    if (!attentionPriority || !movementSensitivity || inFlight.current) return;
    inFlight.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const res = await onboardingApi.submit({
        attention_priority: attentionPriority,
        movement_sensitivity: movementSensitivity,
        time_horizon: finalHorizon,
      });
      setResult(res);
      setStep('result');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  };

  const goToDashboard = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setSubmitting(true);
    try {
      await refreshUser();
      navigate('/');
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  };

  const renderQuestion = <T extends string>(
    questionNumber: number,
    title: string,
    options: Option<T>[],
    onSelect: (value: T) => void,
  ) => (
    <div className="w-full max-w-md">
      <div className="mb-8">
        <p className="text-sm text-slate-500 mb-4 font-medium tracking-wide uppercase">{questionNumber} of 3</p>
        <div className="flex gap-2 mb-8">
          {[1, 2, 3].map(n => (
            <div key={n} className={`h-1 flex-1 rounded-full ${n <= questionNumber ? 'bg-slate-900' : 'bg-slate-200'}`} />
          ))}
        </div>
        <h1 className="text-2xl font-bold text-slate-900 leading-tight">{title}</h1>
      </div>
      <div className="space-y-3">
        {options.map((opt) => (
          <button
            key={opt.value}
            disabled={submitting}
            onClick={() => onSelect(opt.value)}
            className="w-full text-left border border-slate-200 rounded-lg px-5 py-4 hover:border-slate-400 hover:bg-slate-50 transition-all duration-200 flex justify-between items-center gap-3 group disabled:opacity-50 disabled:cursor-wait"
          >
            <div>
              <p className="font-semibold text-slate-900 mb-1">{opt.title}</p>
              <p className="text-sm text-slate-600">{opt.subtitle}</p>
            </div>
            <div className="w-5 h-5 shrink-0 rounded-full border border-slate-300 group-hover:border-slate-500 flex items-center justify-center">
               <div className="w-2.5 h-2.5 rounded-full bg-slate-900 opacity-0 group-hover:opacity-10 transition-opacity" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 py-10">
      {step === 1 &&
        renderQuestion(1, 'What usually deserves your attention first?', Q1_OPTIONS, (v) => {
          setAttentionPriority(v);
          setStep(2);
        })}

      {step === 2 &&
        renderQuestion(2, 'How much market movement do you want surfaced?', Q2_OPTIONS, (v) => {
          setMovementSensitivity(v);
          setStep(3);
        })}

      {step === 3 &&
        renderQuestion(3, 'What horizon matters most when you follow a stock?', Q3_OPTIONS, (v) => {
          submit(v);
        })}

      {step === 3 && submitting && (
        <p role="status" className="w-full max-w-md text-sm text-gray-500 mt-4">Saving your attention profile...</p>
      )}

      {error && <p role="alert" className="w-full max-w-md text-sm text-red-600 mt-4">{error}</p>}

      {step === 'result' && result && (
        <div className="w-full max-w-md text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-8">Your starting attention profile</h1>
          <div className="border border-slate-200 rounded-lg p-6 space-y-4 text-left mb-8 shadow-sm bg-white">
            <p className="text-slate-900 font-medium flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-slate-900"></span>
              {LABELS[result.attention_style]}
            </p>
            <p className="text-slate-900 font-medium flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-slate-900"></span>
              {LABELS[result.risk_profile]}
            </p>
            <p className="text-slate-900 font-medium flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-slate-900"></span>
              {LABELS[result.time_horizon]}
            </p>
          </div>
          <p className="text-sm text-slate-600 mb-8 leading-relaxed">
            This gives Smart Watchlist a starting point.<br/>
            Your preferences affect priority — never market facts.
          </p>
          <button
            onClick={goToDashboard}
            disabled={submitting}
            className="w-full bg-slate-900 text-white rounded-lg py-3 text-sm font-semibold hover:bg-slate-800 transition-colors shadow-sm"
          >
            {submitting ? 'Opening watchlist...' : 'Start watching'}
          </button>
        </div>
      )}
    </div>
  );
}
