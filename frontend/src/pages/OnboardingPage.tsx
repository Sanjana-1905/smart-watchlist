import { useState } from 'react';
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
  const [timeHorizon, setTimeHorizon] = useState<TimeHorizonAnswer | null>(null);
  const [result, setResult] = useState<{ risk_profile: string; attention_style: string; time_horizon: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  const submit = async (finalHorizon: TimeHorizonAnswer) => {
    if (!attentionPriority || !movementSensitivity) return;
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
      setSubmitting(false);
    }
  };

  const goToDashboard = async () => {
    await refreshUser();
    navigate('/');
  };

  const renderQuestion = <T extends string>(
    questionNumber: number,
    title: string,
    options: Option<T>[],
    onSelect: (value: T) => void,
  ) => (
    <div className="w-full max-w-md">
      <p className="text-sm text-gray-500 mb-2">{questionNumber} of 3</p>
      <h1 className="text-xl font-semibold text-gray-900 mb-8">{title}</h1>
      <div className="space-y-3">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onSelect(opt.value)}
            className="w-full text-left border border-gray-300 rounded-lg px-4 py-3 hover:border-gray-900 hover:bg-gray-50 transition"
          >
            <p className="font-medium text-gray-900">{opt.title}</p>
            <p className="text-sm text-gray-500">{opt.subtitle}</p>
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
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
          setTimeHorizon(v);
          submit(v);
        })}

      {step === 3 && submitting && (
        <p className="text-sm text-gray-500 mt-4">Saving your attention profile...</p>
      )}

      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

      {step === 'result' && result && (
        <div className="w-full max-w-md text-center">
          <h1 className="text-xl font-semibold text-gray-900 mb-6">Your attention profile</h1>
          <div className="border border-gray-200 rounded-lg p-6 space-y-2 text-left mb-6">
            <p className="text-gray-900 font-medium">{LABELS[result.attention_style]}</p>
            <p className="text-gray-900 font-medium">{LABELS[result.risk_profile]}</p>
            <p className="text-gray-900 font-medium">{LABELS[result.time_horizon]}</p>
          </div>
          <p className="text-xs text-gray-500 mb-6">
            We'll use this to prioritize what deserves your attention — never to change
            market facts or generate buy/sell recommendations. You can adjust it anytime
            from your preferences.
          </p>
          <button
            onClick={goToDashboard}
            className="w-full bg-gray-900 text-white rounded py-2 text-sm font-semibold hover:bg-gray-800"
          >
            Go to my watchlist
          </button>
        </div>
      )}
    </div>
  );
}
