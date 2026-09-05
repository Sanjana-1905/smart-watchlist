import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { UserProfile } from '../types/market';
import { useAuth } from '../context/AuthContext';

type RiskProfile = 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
type AttentionStyle = 'STABILITY' | 'BALANCED' | 'MOMENTUM';
type TimeHorizon = 'SHORT_TERM' | 'LONG_TERM';

function ToggleGroup<T extends string>({
  label,
  description,
  options,
  value,
  onChange,
}: {
  label: string;
  description: string;
  options: { value: T; label: string; hint: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div style={{ marginBottom: '32px' }}>
      <p style={{ fontSize: '13px', fontWeight: 700, marginBottom: '4px', color: '#0f172a' }}>{label}</p>
      <p className="caption" style={{ marginBottom: '12px' }}>{description}</p>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {options.map(opt => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={value === opt.value}
            style={{
              padding: '10px 20px',
              borderRadius: '6px',
              border: '1px solid',
              borderColor: value === opt.value ? '#4f46e5' : '#e2e8f0',
              background: value === opt.value ? '#eef2ff' : '#ffffff',
              color: value === opt.value ? '#4f46e5' : '#334155',
              fontWeight: value === opt.value ? 700 : 400,
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            {opt.label}
            {value === opt.value && (
              <span style={{ display: 'block', fontSize: '10px', color: '#64748b', marginTop: '2px', fontWeight: 400 }}>
                {opt.hint}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  const [, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [riskProfile, setRiskProfile] = useState<RiskProfile>('BALANCED');
  const [attentionStyle, setAttentionStyle] = useState<AttentionStyle>('BALANCED');
  const [timeHorizon, setTimeHorizon] = useState<TimeHorizon>('LONG_TERM');

  useEffect(() => {
    let active = true;
    api.getProfile()
      .then(p => {
        if (active) {
          setProfile(p);
          setRiskProfile(p.risk_profile);
          setAttentionStyle(p.attention_style);
          setTimeHorizon(p.time_horizon);
        }
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load profile');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.updateProfile({ risk_profile: riskProfile, attention_style: attentionStyle, time_horizon: timeHorizon });
      setProfile(updated);
      setSuccess('Profile lens updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <main className="analysis-page"><p role="status" className="caption">Loading profile lens…</p></main>;

  return (
    <main className="analysis-page">
      <p className="eyebrow" style={{ color: '#4f46e5' }}>Personalization</p>
      <h1>Your Attention Lens</h1>
      <p className="muted" style={{ maxWidth: '600px', marginBottom: '40px' }}>
        These settings calibrate how Smart Watchlist weighs your personal relevance. They never alter market data or objective significance.
      </p>

      {error && <p role="alert" style={{ color: '#dc2626', marginBottom: '16px', borderLeft: '2px solid #dc2626', paddingLeft: '12px' }}>{error}</p>}
      {success && <p role="status" style={{ color: '#16a34a', marginBottom: '16px' }}>{success}</p>}

      <form onSubmit={handleSave} style={{ maxWidth: '600px' }}>
        <ToggleGroup<RiskProfile>
          label="Risk Posture"
          description="How you respond to market volatility."
          value={riskProfile}
          onChange={setRiskProfile}
          options={[
            { value: 'CONSERVATIVE', label: 'Conservative', hint: 'Prioritises stability' },
            { value: 'BALANCED', label: 'Balanced', hint: 'Moderate sensitivity' },
            { value: 'AGGRESSIVE', label: 'Aggressive', hint: 'Highlights large moves' },
          ]}
        />

        <ToggleGroup<AttentionStyle>
          label="What Matters Most"
          description="Your investment approach and attention style."
          value={attentionStyle}
          onChange={setAttentionStyle}
          options={[
            { value: 'STABILITY', label: 'Stability', hint: 'Valuation defense' },
            { value: 'BALANCED', label: 'Balanced', hint: 'Mixed approach' },
            { value: 'MOMENTUM', label: 'Momentum', hint: 'Trend continuation' },
          ]}
        />

        <ToggleGroup<TimeHorizon>
          label="Time Horizon"
          description="How you filter short vs long-term signals."
          value={timeHorizon}
          onChange={setTimeHorizon}
          options={[
            { value: 'SHORT_TERM', label: 'Short Term', hint: '< 3 months' },
            { value: 'LONG_TERM', label: 'Long Term', hint: '> 3 months' },
          ]}
        />

        <button
          type="submit"
          className="primary-action"
          disabled={saving}
          style={{ padding: '14px 32px', fontSize: '14px' }}
        >
          {saving ? 'Saving Lens…' : 'Save Profile Lens'}
        </button>
      </form>

      <section style={{ marginTop: '56px', borderTop: '1px solid #e2e8f0', paddingTop: '36px', maxWidth: '600px' }}>
        <p className="eyebrow" style={{ color: '#4f46e5', marginBottom: '12px' }}>Product Principle</p>
        <h2 style={{ fontSize: '20px', fontWeight: 600, letterSpacing: '-.02em', marginBottom: '16px', color: '#0f172a' }}>
          Your lens changes priority, not market facts.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '16px', alignItems: 'center', margin: '24px 0' }}>
          <div style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '8px' }}>Market Significance</p>
            <p className="caption" style={{ lineHeight: '1.6' }}>Price returns, volume anomaly, 20-day position. Identical for every user.</p>
          </div>
          <div style={{ fontSize: '24px', color: '#94a3b8', textAlign: 'center' }}>+</div>
          <div style={{ padding: '16px', border: '1px solid #4f46e5', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ color: '#4f46e5', marginBottom: '8px' }}>Your Relevance</p>
            <p className="caption" style={{ lineHeight: '1.6' }}>Your since-check movement and selected lens. Changes per user, per visit.</p>
          </div>
        </div>
        <p className="caption" style={{ lineHeight: '1.7' }}>
          Changing your profile lens may shift personal relevance scores and final attention rankings, but never affects historical prices, today's return, volume, or objective market significance.
        </p>
      </section>

      <section style={{ marginTop: '40px', borderTop: '1px solid #e2e8f0', paddingTop: '24px' }}>
        <p className="eyebrow" style={{ marginBottom: '8px' }}>Account</p>
        <p className="caption">Signed in as: <strong>{user?.display_name || user?.email}</strong></p>
      </section>
    </main>
  );
}
