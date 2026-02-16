import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
  useUser
} from '@clerk/clerk-react';
import { useEffect, useMemo, useState } from 'preact/hooks';

import { authedRequest, getApiBaseUrl } from './lib/api';

const BILLING_PORTAL_URL = (import.meta.env.VITE_CLERK_BILLING_PORTAL_URL || '').trim();
const PROJECT_STATUSES = ['idea', 'building', 'live', 'paused'];

function formatCurrency(value) {
  const numeric = Number(value || 0);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(numeric);
}

function inferPlanFromFeatures(features) {
  const normalized = new Set((features || []).map((item) => String(item).toLowerCase()));
  if (normalized.has('enterprise')) {
    return 'enterprise';
  }
  if (normalized.has('pro') || normalized.has('premium') || normalized.has('growth')) {
    return 'pro';
  }
  return 'free';
}

function MetricCard({ label, value, note }) {
  return (
    <article className="metric-card">
      <p className="metric-label">{label}</p>
      <h3>{value}</h3>
      <p className="metric-note">{note}</p>
    </article>
  );
}

function MarketingShell() {
  return (
    <main className="shell">
      <header className="hero">
        <div className="hero-chip">Django + Supabase + Clerk + Preact</div>
        <h1>Launch recurring revenue products with less glue code.</h1>
        <p>
          Auth and billing are delegated to Clerk. Data lives in Supabase Postgres. Django owns ORM and APIs.
          Preact ships a fast interface for operators and customers.
        </p>
        <div className="hero-actions">
          <SignUpButton mode="modal">
            <button type="button" className="button button-primary">Start Building</button>
          </SignUpButton>
          <SignInButton mode="modal">
            <button type="button" className="button button-secondary">Sign In</button>
          </SignInButton>
        </div>
      </header>

      <section className="panel grid-three">
        <article>
          <h3>Fast stack ownership</h3>
          <p>Django migrations define truth. Supabase hosts and scales Postgres. No split-brain schema management.</p>
        </article>
        <article>
          <h3>Monetization ready</h3>
          <p>Use Clerk entitlements to unlock paid features and plan-specific workflows from day one.</p>
        </article>
        <article>
          <h3>Operator dashboard</h3>
          <p>Track offers, revenue hypotheses, and launch pipelines without extra admin tooling.</p>
        </article>
      </section>

      <section className="panel">
        <h2>What ships in this starter</h2>
        <ul className="check-grid">
          <li>Clerk JWT auth against Django REST endpoints</li>
          <li>Webhook-driven profile sync from Clerk into Django models</li>
          <li>User-scoped project CRUD with predictable API contracts</li>
          <li>Plan and feature visibility for billing-aware UI states</li>
          <li>Preact dashboard connected to real backend data</li>
        </ul>
      </section>
    </main>
  );
}

function Dashboard() {
  const { getToken, isLoaded, userId } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState(null);
  const [projects, setProjects] = useState([]);
  const [billing, setBilling] = useState({ enabled_features: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '',
    summary: '',
    monthly_recurring_revenue: '0'
  });

  const apiBase = getApiBaseUrl();

  const loadDashboard = async () => {
    setLoading(true);
    setError('');

    try {
      const [mePayload, projectsPayload, billingPayload] = await Promise.all([
        authedRequest(getToken, '/me/'),
        authedRequest(getToken, '/projects/'),
        authedRequest(getToken, '/billing/features/')
      ]);
      setMe(mePayload || null);
      setProjects(Array.isArray(projectsPayload) ? projectsPayload : []);
      setBilling(billingPayload || { enabled_features: [] });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoaded || !userId) {
      return;
    }
    loadDashboard();
  }, [isLoaded, userId]);

  const enabledFeatures = billing.enabled_features || me?.billing_features || [];
  const planTier = me?.profile?.plan_tier || inferPlanFromFeatures(enabledFeatures);

  const totalMrr = useMemo(
    () => projects.reduce((sum, project) => sum + Number(project.monthly_recurring_revenue || 0), 0),
    [projects]
  );

  const liveProjects = useMemo(
    () => projects.filter((project) => project.status === 'live').length,
    [projects]
  );

  const updateStatus = async (projectId, nextStatus) => {
    setSaving(true);
    setError('');
    try {
      await authedRequest(getToken, `/projects/${projectId}/`, {
        method: 'PATCH',
        body: { status: nextStatus }
      });
      await loadDashboard();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update project status.');
    } finally {
      setSaving(false);
    }
  };

  const deleteProject = async (projectId) => {
    setSaving(true);
    setError('');
    try {
      await authedRequest(getToken, `/projects/${projectId}/`, { method: 'DELETE' });
      await loadDashboard();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not delete project.');
    } finally {
      setSaving(false);
    }
  };

  const createProject = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('Project name is required.');
      return;
    }

    setSaving(true);
    setError('');
    try {
      await authedRequest(getToken, '/projects/', {
        method: 'POST',
        body: {
          name: form.name,
          summary: form.summary,
          monthly_recurring_revenue: form.monthly_recurring_revenue || '0',
          status: 'idea'
        }
      });
      setForm({ name: '', summary: '', monthly_recurring_revenue: '0' });
      await loadDashboard();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not create project.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Operator Console</p>
          <h1>{user?.firstName ? `${user.firstName}'s Pipeline` : 'Pipeline Control'}</h1>
        </div>
        <div className="topbar-actions">
          {BILLING_PORTAL_URL ? (
            <a className="button button-secondary" href={BILLING_PORTAL_URL} target="_blank" rel="noreferrer">
              Manage Billing
            </a>
          ) : (
            <span className="helper-text">Set <code>VITE_CLERK_BILLING_PORTAL_URL</code> to expose billing portal link.</span>
          )}
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>

      {error ? <section className="panel warning-panel">{error}</section> : null}

      <section className="metrics-grid">
        <MetricCard label="Plan" value={planTier.toUpperCase()} note={`${enabledFeatures.length} features enabled`} />
        <MetricCard label="Portfolio MRR" value={formatCurrency(totalMrr)} note={`${projects.length} tracked projects`} />
        <MetricCard label="Live Projects" value={String(liveProjects)} note="Products with active customer delivery" />
      </section>

      <section className="panel split-grid">
        <article>
          <h2>Add new project</h2>
          <form className="project-form" onSubmit={createProject}>
            <label>
              Name
              <input
                type="text"
                value={form.name}
                onInput={(event) => setForm((state) => ({ ...state, name: event.currentTarget.value }))}
                placeholder="Profit Sprint"
              />
            </label>
            <label>
              Summary
              <textarea
                rows="3"
                value={form.summary}
                onInput={(event) => setForm((state) => ({ ...state, summary: event.currentTarget.value }))}
                placeholder="What this product does and why it wins"
              />
            </label>
            <label>
              Expected MRR (USD)
              <input
                type="number"
                min="0"
                step="1"
                value={form.monthly_recurring_revenue}
                onInput={(event) =>
                  setForm((state) => ({ ...state, monthly_recurring_revenue: event.currentTarget.value }))
                }
              />
            </label>
            <button type="submit" className="button button-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Create Project'}
            </button>
          </form>
        </article>

        <article>
          <h2>Execution queue</h2>
          {loading ? <p>Loading projects...</p> : null}
          {!loading && projects.length === 0 ? (
            <p>No projects yet. Add one and start validating demand this week.</p>
          ) : null}
          <div className="project-list">
            {projects.map((project) => (
              <article className="project-card" key={project.id}>
                <div className="project-heading">
                  <h3>{project.name}</h3>
                  <span className={`pill pill-${project.status}`}>{project.status}</span>
                </div>
                <p>{project.summary || 'No summary yet.'}</p>
                <p className="project-mrr">Target MRR: {formatCurrency(project.monthly_recurring_revenue)}</p>
                <div className="project-actions">
                  <select
                    value={project.status}
                    onChange={(event) => updateStatus(project.id, event.currentTarget.value)}
                    disabled={saving}
                  >
                    {PROJECT_STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="button button-ghost"
                    onClick={() => deleteProject(project.id)}
                    disabled={saving}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="panel split-grid">
        <article>
          <h2>Revenue workflow</h2>
          <ol className="sequence-list">
            <li>Define offer outcome and ICP pain in one sentence.</li>
            <li>Collect demand proof with waitlist or paid preorders.</li>
            <li>Build only activation path and billing-critical UX first.</li>
            <li>Run weekly pricing and onboarding experiments.</li>
          </ol>
        </article>
        <article>
          <h2>Enabled entitlements</h2>
          <div className="feature-list">
            {enabledFeatures.length ? (
              enabledFeatures.map((feature) => (
                <span className="feature-tag" key={feature}>
                  {feature}
                </span>
              ))
            ) : (
              <p>No paid entitlements found in JWT claims yet.</p>
            )}
          </div>
          <p className="helper-text">API: <code>{apiBase}</code></p>
        </article>
      </section>
    </main>
  );
}

export function App() {
  return (
    <>
      <SignedOut>
        <MarketingShell />
      </SignedOut>
      <SignedIn>
        <Dashboard />
      </SignedIn>
    </>
  );
}
