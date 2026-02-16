import {
  PricingTable,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
  useUser,
} from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useSignalEffect } from '@preact/signals-react';
import { useSignals } from '@preact/signals-react/runtime';
import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from 'react';

import { apiRequest, authedRequest, getApiBaseUrl } from './lib/api';
import {
  THEME_STORAGE_KEY,
  incrementLaunchCounterSignal,
  launchCounterDoubleSignal,
  launchCounterMomentumSignal,
  launchCounterSignal,
  nextThemeLabelSignal,
  resetLaunchCounterSignal,
  themeSignal,
  toggleThemeSignal,
} from './lib/signals';

const BILLING_PORTAL_URL = (import.meta.env.VITE_CLERK_BILLING_PORTAL_URL || '').trim();
const ENABLE_DEV_MANUAL_CHECKOUT =
  (import.meta.env.VITE_ENABLE_DEV_MANUAL_CHECKOUT || '').trim().toLowerCase() === 'true';
const PREFLIGHT_EMAIL_STORAGE_KEY = 'ds-preflight-email-test';

type Id = number | string;
type NavigateFn = (nextPath: string) => void;
type CheckoutStateValue = 'success' | 'cancel';
type PlanTier = 'free' | 'pro' | 'enterprise';
type GetTokenFn = ReturnType<typeof useAuth>['getToken'];

interface ActivePrice {
  amount_cents: number;
  currency: string;
}

interface ProductPrice {
  id: Id;
  name?: string | null;
  billing_period: string;
  amount_cents: number;
  currency: string;
}

interface ProductAsset {
  id: Id;
  title: string;
}

interface ServiceOffer {
  session_minutes: number;
  delivery_days: number;
  revision_count: number;
}

interface ProductRecord {
  id: Id;
  slug: string;
  name: string;
  product_type: string;
  tagline?: string | null;
  description?: string | null;
  active_price?: ActivePrice | null;
  prices?: ProductPrice[];
  assets?: ProductAsset[];
  service_offer?: ServiceOffer | null;
}

interface OrderRecord {
  public_id: string;
  status: string;
  total_cents: number;
  currency: string;
  items?: unknown[];
}

interface OrderCreateResponse {
  checkout?: {
    checkout_url?: string | null;
  } | null;
  order?: {
    public_id?: string | null;
  } | null;
}

interface PriceSummary {
  amount_cents: number;
  currency: string;
  billing_period: string;
}

interface SubscriptionRecord {
  id: Id;
  product_name?: string | null;
  status: string;
  price_summary?: PriceSummary | null;
}

interface DownloadGrant {
  token: string;
  asset_title: string;
  can_download: boolean;
  product_name: string;
  download_count: number;
  max_downloads: number;
}

interface DownloadAccessResponse {
  download_url?: string | null;
}

interface BookingRecord {
  id: Id;
  product_name?: string | null;
  status: string;
  customer_notes?: string | null;
}

interface EntitlementRecord {
  id: Id;
  feature_key: string;
  is_current: boolean;
}

interface MeResponse {
  customer_account?: {
    full_name?: string | null;
    metadata?: Record<string, unknown> | null;
  } | null;
  profile?: {
    plan_tier?: string | null;
    first_name?: string | null;
  } | null;
  billing_features?: string[] | null;
}

interface BillingFeaturesResponse {
  enabled_features: string[];
}

interface AiProviderRecord {
  key: string;
  label: string;
  kind: string;
  enabled: boolean;
  base_url: string;
  model_hint?: string | null;
  docs_url: string;
  env_vars: string[];
}

interface AiUsageBucketRecord {
  key: string;
  label: string;
  used: number;
  limit: number | null;
  unit: string;
  reset_window: string;
  percent_used: number | null;
  near_limit: boolean;
}

interface AiUsageSummaryResponse {
  period: string;
  plan_tier: string;
  buckets: AiUsageBucketRecord[];
  notes: string[];
}

interface NavLinkProps {
  to: string;
  currentPath: string;
  onNavigate: NavigateFn;
  children: ReactNode;
}

interface HeaderProps {
  pathname: string;
  onNavigate: NavigateFn;
  signedIn: boolean;
  expandedNav: boolean;
  themeLabel: string;
  onToggleTheme: () => void;
}

interface PricingPageProps {
  signedIn: boolean;
}

interface ProductCatalogProps {
  onNavigate: NavigateFn;
}

interface ProductDetailProps {
  slug: string;
  signedIn: boolean;
  onNavigate: NavigateFn;
  getToken: GetTokenFn;
}

interface TokenProps {
  getToken: GetTokenFn;
}

interface TokenNavigateProps extends TokenProps {
  onNavigate: NavigateFn;
}

interface CheckoutStateProps {
  state: CheckoutStateValue;
  onNavigate: NavigateFn;
}

interface MetricCardProps {
  label: string;
  value: string;
  note: string;
}

interface NavigateProps {
  onNavigate: NavigateFn;
}

interface DashboardProps extends NavigateProps {
  getToken: GetTokenFn;
}

interface PreflightEmailResponse {
  sent: boolean;
  detail: string;
  recipient_email?: string;
  sent_at?: string;
}

interface SignedAppProps {
  pathname: string;
  onNavigate: NavigateFn;
  themeLabel: string;
  onToggleTheme: () => void;
}

interface PageIntroProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

interface TutorialBlockProps {
  whatThisDoes: string;
  howToTest: string[];
  expectedResult: string;
}

function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

const buttonBase =
  'inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:cursor-not-allowed disabled:opacity-60';
const buttonPrimary =
  `${buttonBase} bg-slate-950 text-white shadow-sm hover:bg-slate-800 dark:bg-cyan-400 dark:text-slate-950 dark:hover:bg-cyan-300`;
const buttonSecondary =
  `${buttonBase} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800`;
const buttonGhost =
  `${buttonBase} border border-transparent bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800`;
const sectionClass =
  'rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl shadow-slate-900/5 backdrop-blur dark:border-slate-700 dark:bg-slate-900/80';
const cardClass =
  'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900';

function formatCurrencyFromCents(cents: number, currency = 'USD'): string {
  const numeric = Number(cents || 0) / 100;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(numeric);
}

function inferPlanFromFeatures(features: ReadonlyArray<string | null | undefined> | null | undefined): PlanTier {
  const normalized = new Set((features || []).map((item) => String(item).toLowerCase()));
  if (normalized.has('enterprise')) {
    return 'enterprise';
  }
  if (normalized.has('pro') || normalized.has('premium') || normalized.has('growth')) {
    return 'pro';
  }
  return 'free';
}

function isPlanTier(value: string | null | undefined): value is PlanTier {
  return value === 'free' || value === 'pro' || value === 'enterprise';
}

function usePathname(): { pathname: string; navigate: NavigateFn } {
  const [pathname, setPathname] = useState<string>(() => window.location.pathname || '/');

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname || '/');
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = (nextPath: string) => {
    if (!nextPath || nextPath === pathname) {
      return;
    }
    window.history.pushState({}, '', nextPath);
    setPathname(nextPath);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return { pathname, navigate };
}

function statusPillClasses(status: string): string {
  const normalized = (status || '').toLowerCase();
  if (['paid', 'fulfilled', 'active', 'trialing', 'ready', 'confirmed', 'completed', 'digital'].includes(normalized)) {
    return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';
  }
  if (['pending_payment', 'requested', 'service', 'past_due', 'incomplete'].includes(normalized)) {
    return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
  }
  if (['canceled', 'refunded', 'paused', 'locked'].includes(normalized)) {
    return 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
  }
  return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300';
}

function StatusPill({ value }: { value: string }): ReactElement {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em]',
        statusPillClasses(value)
      )}
    >
      {value}
    </span>
  );
}

function NavLink({ to, currentPath, onNavigate, children }: NavLinkProps): ReactElement {
  const active = currentPath === to;
  return (
    <a
      href={to}
      className={cn(
        'rounded-lg px-3 py-2 text-sm font-medium transition',
        active
          ? 'bg-slate-950 text-white dark:bg-cyan-400 dark:text-slate-950'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
      )}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(to);
      }}
    >
      {children}
    </a>
  );
}

function Header({ pathname, onNavigate, signedIn, expandedNav, themeLabel, onToggleTheme }: HeaderProps): ReactElement {
  return (
    <header className="sticky top-4 z-30 rounded-2xl border border-slate-200 bg-white/90 px-4 py-4 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-slate-700 dark:bg-slate-900/85 sm:px-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <button
          type="button"
          className="flex items-center gap-3 text-left"
          onClick={() => onNavigate(signedIn ? '/app' : '/')}
        >
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-slate-950 text-sm font-bold text-white dark:bg-cyan-400 dark:text-slate-950">
            DS
          </span>
          <span>
            <span className="block text-base font-bold text-slate-900 dark:text-slate-100">DjangoStarter</span>
            <span className="block text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              Cashflow-first SaaS starter for creators
            </span>
          </span>
        </button>

        <nav className="flex flex-wrap items-center gap-1">
          <NavLink to={signedIn ? '/app' : '/'} currentPath={pathname} onNavigate={onNavigate}>
            {signedIn ? 'Dashboard' : 'Home'}
          </NavLink>
          {signedIn ? <NavLink to="/products" currentPath={pathname} onNavigate={onNavigate}>Offers</NavLink> : null}
          {signedIn ? <NavLink to="/pricing" currentPath={pathname} onNavigate={onNavigate}>Pricing</NavLink> : null}
          {signedIn && expandedNav ? (
            <>
              <NavLink to="/account/purchases" currentPath={pathname} onNavigate={onNavigate}>Purchases</NavLink>
              <NavLink to="/account/downloads" currentPath={pathname} onNavigate={onNavigate}>Downloads</NavLink>
              <NavLink to="/account/subscriptions" currentPath={pathname} onNavigate={onNavigate}>Subscriptions</NavLink>
              <NavLink to="/account/bookings" currentPath={pathname} onNavigate={onNavigate}>Bookings</NavLink>
            </>
          ) : null}
        </nav>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={buttonGhost} onClick={onToggleTheme}>
            {themeLabel}
          </button>
          {signedIn ? (
            <UserButton afterSignOutUrl="/" />
          ) : (
            <>
              <SignInButton mode="modal">
                <button type="button" className={buttonSecondary}>Sign In</button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button type="button" className={buttonPrimary}>Start Free</button>
              </SignUpButton>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function PageIntro({ eyebrow, title, description, actions }: PageIntroProps): ReactElement {
  return (
    <header className="space-y-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700 dark:text-cyan-300">{eyebrow}</p>
      <h1 className="max-w-4xl text-3xl font-black tracking-tight text-slate-900 dark:text-white sm:text-4xl">
        {title}
      </h1>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-300 sm:text-base">{description}</p>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

function TutorialBlock({ whatThisDoes, howToTest, expectedResult }: TutorialBlockProps): ReactElement {
  return (
    <article className="rounded-2xl border border-cyan-200/70 bg-cyan-50/70 p-4 dark:border-cyan-800/70 dark:bg-cyan-950/20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700 dark:text-cyan-300">
        Living Tutorial
      </p>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">What this does</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">{whatThisDoes}</p>
        </section>
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">How to test</h3>
          <ol className="list-decimal space-y-1 pl-4 text-sm text-slate-600 dark:text-slate-300">
            {howToTest.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </section>
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Expected result</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">{expectedResult}</p>
        </section>
      </div>
    </article>
  );
}

function StatCard({ label, value, note }: { label: string; value: string; note: string }): ReactElement {
  return (
    <article className={cardClass}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{label}</p>
      <h3 className="mt-2 text-2xl font-black tracking-tight text-slate-900 dark:text-white">{value}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{note}</p>
    </article>
  );
}

function MarketingHome(): ReactElement {
  useSignals();

  const jumpTo = (sectionId: string): void => {
    const section = window.document.getElementById(sectionId);
    if (!section) {
      return;
    }
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const stackCards = [
    {
      title: 'Django owns the schema and migrations',
      body: 'Models and migrations stay in Django. Supabase is your Postgres control plane, not a second schema owner.',
      points: [
        'ORM and migrations stay predictable for AI agents',
        'Server contracts remain explicit and testable',
        'No drift between code and database structure',
      ],
    },
    {
      title: 'Supabase adds operator speed',
      body: 'Use Supabase for database operations, realtime channels, and admin visibility while Django remains source of truth.',
      points: [
        'Realtime events available for product UX',
        'Fast table inspection without custom dashboards',
        'Works with self-hosted Supabase on your own infra',
      ],
    },
    {
      title: 'Clerk and Resend cover external edges',
      body: 'Only auth and billing leave your stack through Clerk. Resend handles lifecycle email when you need campaign or status sends.',
      points: [
        'Webhook-first payment confirmation',
        'Reliable auth without rebuilding identity stack',
        'Transactional and marketing email on demand',
      ],
    },
  ];

  const aiPlans = [
    {
      title: 'Digital Product',
      outcome: 'Sell templates, packs, and assets with webhook-verified fulfillment.',
      steps: ['One-time price', 'Asset grants', 'Download access tracking'],
    },
    {
      title: 'Subscription + usage',
      outcome: 'Ship AI chat, image, or video usage limits with monthly resets.',
      steps: ['Recurring plan', 'Entitlement keys', 'Token and generation quotas'],
    },
    {
      title: 'Service + automation',
      outcome: 'Bundle advisory, implementation, or done-for-you workflows.',
      steps: ['Service offer', 'Booking records', 'Lifecycle notifications'],
    },
  ];

  const launchMath = [
    { label: 'Starter offer', value: '$79', note: 'Low-friction one-time product to validate demand.' },
    { label: 'Monthly AI plan', value: '$29', note: 'Recurring revenue with token or generation limits.' },
    { label: '30 customers', value: '$2,370+', note: 'Example month-one gross before fees and support costs.' },
  ];

  return (
    <>
      <section className={cn(sectionClass, 'overflow-hidden bg-gradient-to-br from-cyan-50 via-white to-emerald-50 dark:from-slate-900 dark:via-slate-900 dark:to-cyan-950/20')}>
        <div className="grid gap-8 lg:grid-cols-[1.3fr,0.9fr] lg:items-start">
          <div className="space-y-5">
            <p className="inline-flex rounded-full border border-cyan-200 bg-cyan-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-800 dark:border-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200">
              Revenue-first creator stack
            </p>
            <h1 className="max-w-3xl text-4xl font-black tracking-tight text-slate-900 dark:text-white sm:text-5xl">
              Creators do not need more boilerplate. They need cash flow.
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-300">
              DjangoStarter helps Python creators launch offers that get paid and fulfilled correctly.
              Build fast with Django + DRF, run self-hosted on Coolify, keep Supabase as your data control plane,
              and keep payment truth on verified Clerk webhooks.
            </p>
            <div className="flex flex-wrap gap-2">
              <SignUpButton mode="modal">
                <button type="button" className={buttonPrimary}>Start Free</button>
              </SignUpButton>
              <button type="button" className={buttonSecondary} onClick={() => jumpTo('tutorials')}>
                See Revenue Tutorials
              </button>
              <button type="button" className={buttonSecondary} onClick={() => jumpTo('self-hosted')}>
                Why This Stack
              </button>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">Self-hosted first</span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">AI-agent ready</span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">Webhook-secure checkout</span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">Modular scaffolding</span>
            </div>
          </div>

          <aside className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">What this means in practice</h2>
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-600 dark:text-slate-300">
              <li>Checkout events can not spoof paid state from the browser</li>
              <li>Downloads, subscriptions, and bookings unlock after verified payment</li>
              <li>Your app ships with account pages users can trust</li>
              <li>Your agent can extend features without breaking the revenue loop</li>
            </ul>
            <div className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">Signal sandbox</p>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-white px-2 py-1 dark:bg-slate-900">Launch Count: {launchCounterSignal.value}</span>
                <span className="rounded-full bg-white px-2 py-1 dark:bg-slate-900">Double: {launchCounterDoubleSignal.value}</span>
                <span className="rounded-full bg-white px-2 py-1 capitalize dark:bg-slate-900">Momentum: {launchCounterMomentumSignal.value}</span>
              </div>
              <div className="flex gap-2">
                <button type="button" className={buttonSecondary} onClick={incrementLaunchCounterSignal}>Push</button>
                <button type="button" className={buttonGhost} onClick={resetLaunchCounterSignal}>Reset</button>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section id="self-hosted" className={sectionClass}>
        <PageIntro
          eyebrow="Self-hosted architecture"
          title="Django is source of truth. Supabase is your control plane."
          description="This template is designed for low-cost ownership. Run app and Supabase on Coolify. Keep external dependencies limited to Clerk and Resend."
        />
        <div className="grid gap-4 lg:grid-cols-3">
          {stackCards.map((card) => (
            <article key={card.title} className={cardClass}>
              <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">{card.title}</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{card.body}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
                {card.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section id="tutorials" className={sectionClass}>
        <PageIntro
          eyebrow="Revenue tutorials"
          title="Three starter loops: digital product, subscription usage, and services."
          description="The starter ships scaffolding for e-commerce and subscriptions. Extend it for AI chat, image generation, video generation, or any token-based feature."
        />
        <div className="grid gap-4 lg:grid-cols-3">
          {aiPlans.map((plan) => (
            <article key={plan.title} className={cardClass}>
              <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">{plan.title}</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{plan.outcome}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
                {plan.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className={sectionClass}>
        <PageIntro
          eyebrow="Money math"
          title="Use simple economics first, then optimize conversion and retention."
          description="These numbers are examples to help planning. Real results depend on traffic quality, offer fit, onboarding, and retention."
        />
        <div className="grid gap-4 sm:grid-cols-3">
          {launchMath.map((item) => (
            <StatCard key={item.label} label={item.label} value={item.value} note={item.note} />
          ))}
        </div>
      </section>

      <section className={cn(sectionClass, 'border-cyan-200 dark:border-cyan-800')}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700 dark:text-cyan-300">Bottom line</p>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-900 dark:text-white sm:text-3xl">
              Build one trusted paid loop first. Then scale content and channels.
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
              This starter is for builders who want control, speed, and clear monetization paths without buying another fragile boilerplate.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <SignUpButton mode="modal">
              <button type="button" className={buttonPrimary}>Start Free</button>
            </SignUpButton>
            <SignInButton mode="modal">
              <button type="button" className={buttonSecondary}>Sign In</button>
            </SignInButton>
          </div>
        </div>
      </section>
    </>
  );
}

function PricingPage({ signedIn }: PricingPageProps): ReactElement {
  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Pricing"
        title="Live plans from Clerk Billing"
        description="No hardcoded frontend prices. Configure plans in Clerk and this page updates immediately."
      />
      <TutorialBlock
        whatThisDoes="Renders your active Clerk plans so buyers can start subscription checkout without manual frontend edits."
        howToTest={[
          'Create a plan in Clerk Billing',
          'Refresh this page and confirm it appears',
          'Run checkout and confirm webhook updates subscriptions',
        ]}
        expectedResult="Pricing is source-of-truth from Clerk and account subscription data stays in sync."
      />
      <div className={cardClass}>
        <PricingTable />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {signedIn
          ? 'Signed in users can manage plans from subscriptions and billing portal.'
          : 'Sign in first to subscribe and test billing flow.'}
      </p>
    </section>
  );
}

function ProductCatalog({ onNavigate }: ProductCatalogProps): ReactElement {
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isActive = true;
    setLoading(true);
    setError('');

    apiRequest<ProductRecord[]>('/products/')
      .then((payload) => {
        if (!isActive) {
          return;
        }
        setProducts(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!isActive) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load catalog.');
      })
      .finally(() => {
        if (isActive) {
          setLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Offers"
        title="Buyable offers with production checkout paths"
        description="Publish digital or service products, attach prices, and route buyers into secure order creation."
      />
      <TutorialBlock
        whatThisDoes="Shows published catalog entries and current active prices from backend APIs."
        howToTest={[
          'Create a product and active price in seller APIs',
          'Refresh and open the product detail page',
          'Start checkout to create a pending order',
        ]}
        expectedResult="Catalog cards always reflect backend data and payment flow stays server-led."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading catalog...</p> : null}

      {!loading && products.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No published products yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Create one product and one active price, then return to validate conversion flow.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
            <button type="button" className={buttonPrimary} onClick={() => onNavigate('/app')}>
              Open Preflight Dashboard
            </button>
          </div>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        {products.map((product) => (
          <article key={product.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <StatusPill value={product.product_type} />
              <p className="text-sm font-semibold text-slate-900 dark:text-white">
                {product.active_price
                  ? formatCurrencyFromCents(product.active_price.amount_cents, product.active_price.currency)
                  : 'Unpriced'}
              </p>
            </div>
            <h3 className="mt-3 text-xl font-bold tracking-tight text-slate-900 dark:text-white">{product.name}</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {product.tagline || product.description || 'No description yet.'}
            </p>
            <button
              type="button"
              className={cn(buttonSecondary, 'mt-4 w-full')}
              onClick={() => onNavigate(`/products/${product.slug}`)}
            >
              View Offer
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function ProductDetail({ slug, signedIn, onNavigate, getToken }: ProductDetailProps): ReactElement {
  const [product, setProduct] = useState<ProductRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!slug) {
      setProduct(null);
      return;
    }

    let isActive = true;
    setLoading(true);
    setError('');

    apiRequest<ProductRecord>(`/products/${slug}/`)
      .then((payload) => {
        if (!isActive) {
          return;
        }
        setProduct(payload || null);
      })
      .catch((requestError) => {
        if (!isActive) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load product.');
      })
      .finally(() => {
        if (isActive) {
          setLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [slug]);

  const handleBuy = async (priceId: Id): Promise<void> => {
    if (!signedIn) {
      onNavigate('/pricing');
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const orderResponse = await authedRequest<OrderCreateResponse, { price_id: Id; quantity: number }>(
        getToken,
        '/account/orders/create/',
        {
          method: 'POST',
          body: { price_id: priceId, quantity: 1 },
        }
      );

      const checkoutUrl = orderResponse?.checkout?.checkout_url || '';
      const publicId = orderResponse?.order?.public_id;

      if (!publicId) {
        throw new Error('Order did not return a valid id.');
      }

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
        return;
      }

      if (!ENABLE_DEV_MANUAL_CHECKOUT) {
        throw new Error(
          'Checkout URL missing for this price. Configure Clerk checkout metadata or use local manual mode only in development.'
        );
      }

      await authedRequest<unknown, { provider: string; external_id: string }>(
        getToken,
        `/account/orders/${publicId}/confirm/`,
        {
          method: 'POST',
          body: {
            provider: 'manual',
            external_id: `manual_${Date.now()}`,
          },
        }
      );

      setSuccess('Purchase completed. Fulfillment has been created.');
      onNavigate('/checkout/success');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not complete purchase flow.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <section className={sectionClass}>
        <PageIntro eyebrow="Offer" title="Loading offer" description="Fetching product details and pricing." />
      </section>
    );
  }

  if (!product) {
    return (
      <section className={sectionClass}>
        <PageIntro eyebrow="Offer" title="Offer not found" description="This route does not match a published product." />
      </section>
    );
  }

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Offer detail"
        title={product.name}
        description={product.description || product.tagline || 'No description yet.'}
        actions={(
          <>
            <StatusPill value={product.product_type} />
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
              Back to Offers
            </button>
          </>
        )}
      />

      <TutorialBlock
        whatThisDoes="Creates pending orders server-side and routes users into checkout without trusting client payment state."
        howToTest={[
          'Confirm at least one price exists on this product',
          'Click Buy and ensure pending order is created',
          'Finish checkout and confirm fulfillment in account pages',
        ]}
        expectedResult="Order status transitions happen server-side and fulfillment appears only after payment confirmation."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {success ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{success}</p> : null}

      {!product.prices?.length ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No price attached to this offer</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Add at least one active price through seller APIs, then return to validate checkout flow.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
            <button type="button" className={buttonPrimary} onClick={() => onNavigate('/app')}>
              Back to Preflight Dashboard
            </button>
          </div>
        </article>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {(product.prices || []).map((price) => (
            <article className={cardClass} key={price.id}>
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{price.name || price.billing_period}</h3>
                <p className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                  {formatCurrencyFromCents(price.amount_cents, price.currency)}
                </p>
              </div>
              <p className="mt-1 text-sm capitalize text-slate-600 dark:text-slate-300">
                Billed {price.billing_period.replace('_', ' ')}
              </p>
              <button
                type="button"
                className={cn(buttonPrimary, 'mt-4 w-full')}
                disabled={saving}
                onClick={() => handleBuy(price.id)}
              >
                {saving ? 'Processing...' : signedIn ? 'Buy Now' : 'Sign In to Buy'}
              </button>
            </article>
          ))}
        </div>
      )}

      {product.assets?.length ? (
        <article className={cardClass}>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Included assets</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            {product.assets.map((asset) => (
              <li key={asset.id}>{asset.title}</li>
            ))}
          </ul>
        </article>
      ) : null}

      {product.service_offer ? (
        <article className={cardClass}>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Service delivery details</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            <li>Session minutes: {product.service_offer.session_minutes}</li>
            <li>Delivery days: {product.service_offer.delivery_days}</li>
            <li>Revisions: {product.service_offer.revision_count}</li>
          </ul>
        </article>
      ) : null}
    </section>
  );
}

function PurchasesPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOrders = async (): Promise<void> => {
    setLoading(true);
    setError('');
    try {
      const payload = await authedRequest<OrderRecord[]>(getToken, '/account/orders/');
      setOrders(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load purchases.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Purchases"
        description="Track order status and verify payment transitions from pending to paid or fulfilled."
      />
      <TutorialBlock
        whatThisDoes="Displays every order for the signed-in account with server-side status and totals."
        howToTest={[
          'Complete checkout from any offer',
          'Return after webhook processing',
          'Confirm status reflects paid or fulfilled',
        ]}
        expectedResult="Order state is auditable and never relies on optimistic frontend state."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading purchases...</p> : null}

      {!loading && orders.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No purchases yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Run one checkout flow and return to validate payment transition.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Browse Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {orders.map((order) => (
          <article key={order.public_id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Order {String(order.public_id).slice(0, 8)}</h3>
              <StatusPill value={order.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Total: {formatCurrencyFromCents(order.total_cents, order.currency)}
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-300">{order.items?.length || 0} item(s)</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function SubscriptionsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/')
      .then((payload) => {
        if (!active) {
          return;
        }
        setSubscriptions(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load subscriptions.');
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Subscriptions"
        description="Monitor recurring plans and usage-ready billing tiers."
      />
      <TutorialBlock
        whatThisDoes="Shows recurring subscription records synced from checkout and webhook events."
        howToTest={[
          'Subscribe to a recurring plan',
          'Confirm status appears here',
          'Open Clerk details and verify metadata alignment',
        ]}
        expectedResult="Subscription state remains consistent between app records and Clerk billing data."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading subscriptions...</p> : null}

      {!loading && subscriptions.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No active subscriptions found</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Add one recurring plan and complete checkout to validate this surface.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/pricing')}>
            Open Pricing
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {subscriptions.map((subscription) => (
          <article key={subscription.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{subscription.product_name || 'Subscription'}</h3>
              <StatusPill value={subscription.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {subscription.price_summary
                ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                : 'No linked local price'}
            </p>
          </article>
        ))}
      </div>

      <SignedIn>
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Manage in Clerk</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Open subscription details for invoices and payment methods.
          </p>
          <SubscriptionDetailsButton>
            <button type="button" className={cn(buttonSecondary, 'mt-4')}>Open Subscription Details</button>
          </SubscriptionDetailsButton>
        </article>
      </SignedIn>
    </section>
  );
}

function DownloadsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [grants, setGrants] = useState<DownloadGrant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const loadGrants = async (): Promise<void> => {
    setLoading(true);
    setError('');
    try {
      const payload = await authedRequest<DownloadGrant[]>(getToken, '/account/downloads/');
      setGrants(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load downloads.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGrants();
  }, []);

  const requestAccess = async (token: string): Promise<void> => {
    setAccessingToken(token);
    setError('');

    try {
      const payload = await authedRequest<DownloadAccessResponse>(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST',
      });

      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      await loadGrants();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not generate download access.');
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Downloads"
        description="Generate signed download links and track grant usage."
      />
      <TutorialBlock
        whatThisDoes="Lists digital delivery grants and creates temporary access links per asset."
        howToTest={[
          'Buy a digital product with attached asset',
          'Confirm grant appears as ready',
          'Generate link and verify usage count increments',
        ]}
        expectedResult="Eligible grants produce secure links and usage counters remain accurate."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading downloads...</p> : null}

      {!loading && grants.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No digital deliveries yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Fulfillment grants appear after paid digital orders.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Browse Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {grants.map((grant) => (
          <article key={grant.token} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{grant.asset_title}</h3>
              <StatusPill value={grant.can_download ? 'ready' : 'locked'} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{grant.product_name}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {grant.download_count}/{grant.max_downloads} downloads used
            </p>
            <button
              type="button"
              className={cn(buttonPrimary, 'mt-4 w-full')}
              disabled={!grant.can_download || accessingToken === grant.token}
              onClick={() => requestAccess(grant.token)}
            >
              {accessingToken === grant.token ? 'Preparing...' : 'Get Download Link'}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function BookingsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [bookings, setBookings] = useState<BookingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest<BookingRecord[]>(getToken, '/account/bookings/')
      .then((payload) => {
        if (!active) {
          return;
        }
        setBookings(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load bookings.');
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Bookings"
        description="Review service delivery requests and customer notes."
      />
      <TutorialBlock
        whatThisDoes="Tracks service bookings created by fulfilled service purchases."
        howToTest={[
          'Create and publish a service offer',
          'Purchase service and wait for fulfillment',
          'Confirm booking appears with status and notes',
        ]}
        expectedResult="Paid service orders create operational booking records you can manage."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading bookings...</p> : null}

      {!loading && bookings.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No service bookings yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Service bookings appear after paid fulfillment.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Open Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {bookings.map((booking) => (
          <article key={booking.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{booking.product_name || 'Service booking'}</h3>
              <StatusPill value={booking.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{booking.customer_notes || 'No notes provided.'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function CheckoutState({ state, onNavigate }: CheckoutStateProps): ReactElement {
  const isSuccess = state === 'success';
  return (
    <section
      className={cn(
        sectionClass,
        'space-y-6',
        isSuccess
          ? 'border-emerald-300 bg-emerald-50/60 dark:border-emerald-700 dark:bg-emerald-900/10'
          : 'border-rose-300 bg-rose-50/60 dark:border-rose-700 dark:bg-rose-900/10'
      )}
    >
      <PageIntro
        eyebrow="Checkout"
        title={isSuccess ? 'Checkout Successful' : 'Checkout Canceled'}
        description={
          isSuccess
            ? 'Payment completed. Fulfillment is now available in your account routes.'
            : 'No charge was made. Return to offers and retry checkout when ready.'
        }
      />
      <TutorialBlock
        whatThisDoes="Confirms checkout outcome and routes users to the next high-value step."
        howToTest={[
          'Complete checkout once for success route',
          'Cancel checkout once for cancel route',
          'Follow CTA and verify downstream pages match state',
        ]}
        expectedResult="Users always land on a clear next action after checkout."
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" className={buttonPrimary} onClick={() => onNavigate('/account/purchases')}>
          View Purchases
        </button>
        <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
          Browse Offers
        </button>
      </div>
    </section>
  );
}

function MetricCard({ label, value, note }: MetricCardProps): ReactElement {
  return (
    <article className={cardClass}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{label}</p>
      <h3 className="mt-2 text-2xl font-black tracking-tight text-slate-900 dark:text-white">{value}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{note}</p>
    </article>
  );
}

function UsageBar({ bucket }: { bucket: AiUsageBucketRecord }): ReactElement {
  const percent = bucket.percent_used !== null ? Math.min(Math.max(bucket.percent_used, 0), 100) : null;

  return (
    <article className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-900 dark:text-white">{bucket.label}</p>
        <StatusPill value={bucket.near_limit ? 'near_limit' : 'healthy'} />
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-300">
        {bucket.used} / {bucket.limit ?? 'unlimited'} {bucket.unit} ({bucket.reset_window})
      </p>
      {percent !== null ? (
        <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className={cn('h-full rounded-full', bucket.near_limit ? 'bg-amber-500' : 'bg-emerald-500')}
            style={{ width: `${percent}%` }}
          />
        </div>
      ) : (
        <p className="text-xs text-slate-500 dark:text-slate-400">No cap configured</p>
      )}
    </article>
  );
}

function AccountDashboard({ onNavigate, getToken }: DashboardProps): ReactElement {
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState<MeResponse | null>(null);
  const [billing, setBilling] = useState<BillingFeaturesResponse>({ enabled_features: [] });
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [downloads, setDownloads] = useState<DownloadGrant[]>([]);
  const [entitlements, setEntitlements] = useState<EntitlementRecord[]>([]);
  const [bookings, setBookings] = useState<BookingRecord[]>([]);
  const [catalogProducts, setCatalogProducts] = useState<ProductRecord[]>([]);
  const [aiProviders, setAiProviders] = useState<AiProviderRecord[]>([]);
  const [aiUsage, setAiUsage] = useState<AiUsageSummaryResponse>({ period: 'current', plan_tier: 'free', buckets: [], notes: [] });
  const [supabaseProbe, setSupabaseProbe] = useState<{ checked: boolean; ok: boolean; detail: string }>({
    checked: false,
    ok: false,
    detail: 'Not tested yet.',
  });
  const [emailTestStatus, setEmailTestStatus] = useState<{
    sent: boolean;
    detail: string;
    recipientEmail: string;
    sentAt: string;
    running: boolean;
  }>(() => {
    if (typeof window === 'undefined') {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }

    const raw = window.localStorage.getItem(PREFLIGHT_EMAIL_STORAGE_KEY);
    if (!raw) {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }

    try {
      const parsed = JSON.parse(raw) as { recipient_email?: string; sent_at?: string };
      const sentAt = String(parsed.sent_at || '');
      return {
        sent: Boolean(sentAt),
        detail: sentAt ? `Last test email sent at ${new Date(sentAt).toLocaleString()}.` : 'Not tested yet.',
        recipientEmail: String(parsed.recipient_email || ''),
        sentAt,
        running: false,
      };
    } catch {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const apiBase = getApiBaseUrl();

  const loadDashboard = async ({ silent = false }: { silent?: boolean } = {}): Promise<void> => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');

    try {
      const [
        mePayload,
        billingPayload,
        ordersPayload,
        subscriptionsPayload,
        downloadsPayload,
        entitlementsPayload,
        bookingsPayload,
        catalogPayload,
        aiProvidersPayload,
        aiUsagePayload,
        supabaseProbePayload,
      ] = await Promise.all([
        authedRequest<MeResponse>(getToken, '/me/'),
        authedRequest<BillingFeaturesResponse>(getToken, '/billing/features/'),
        authedRequest<OrderRecord[]>(getToken, '/account/orders/'),
        authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/'),
        authedRequest<DownloadGrant[]>(getToken, '/account/downloads/'),
        authedRequest<EntitlementRecord[]>(getToken, '/account/entitlements/'),
        authedRequest<BookingRecord[]>(getToken, '/account/bookings/'),
        apiRequest<ProductRecord[]>('/products/').catch(() => []),
        authedRequest<AiProviderRecord[]>(getToken, '/ai/providers/').catch(() => []),
        authedRequest<AiUsageSummaryResponse>(getToken, '/ai/usage/summary/').catch(() => ({
          period: 'current',
          plan_tier: 'free',
          buckets: [],
          notes: [],
        })),
        authedRequest<{ profile?: unknown }>(getToken, '/supabase/profile/')
          .then((payload) => ({
            checked: true,
            ok: true,
            detail: payload?.profile
              ? 'Supabase profile probe succeeded.'
              : 'Supabase probe succeeded. No profile row found yet.',
          }))
          .catch((probeError) => ({
            checked: true,
            ok: false,
            detail: probeError instanceof Error ? probeError.message : 'Supabase probe failed.',
          })),
      ]);
      setMe(mePayload || null);
      setBilling(billingPayload || { enabled_features: [] });
      setOrders(Array.isArray(ordersPayload) ? ordersPayload : []);
      setSubscriptions(Array.isArray(subscriptionsPayload) ? subscriptionsPayload : []);
      setDownloads(Array.isArray(downloadsPayload) ? downloadsPayload : []);
      setEntitlements(Array.isArray(entitlementsPayload) ? entitlementsPayload : []);
      setBookings(Array.isArray(bookingsPayload) ? bookingsPayload : []);
      setCatalogProducts(Array.isArray(catalogPayload) ? catalogPayload : []);
      setAiProviders(Array.isArray(aiProvidersPayload) ? aiProvidersPayload : []);
      setAiUsage(aiUsagePayload || { period: 'current', plan_tier: 'free', buckets: [], notes: [] });
      setSupabaseProbe(
        supabaseProbePayload || {
          checked: false,
          ok: false,
          detail: 'Not tested yet.',
        }
      );

      const metadata = mePayload?.customer_account?.metadata;
      if (metadata && typeof metadata === 'object') {
        const sentAt = String((metadata as Record<string, unknown>).preflight_email_last_sent_at || '');
        const recipientEmail = String((metadata as Record<string, unknown>).preflight_email_last_recipient || '');
        if (sentAt) {
          const detail = `Last test email sent at ${new Date(sentAt).toLocaleString()}.`;
          setEmailTestStatus((previous) => ({
            ...previous,
            sent: true,
            detail,
            recipientEmail: recipientEmail || previous.recipientEmail,
            sentAt,
            running: false,
          }));
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(
              PREFLIGHT_EMAIL_STORAGE_KEY,
              JSON.stringify({
                recipient_email: recipientEmail,
                sent_at: sentAt,
              })
            );
          }
        }
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!isLoaded || !userId) {
      return;
    }
    loadDashboard();
  }, [isLoaded, userId]);

  const enabledFeatures: string[] = billing.enabled_features || me?.billing_features || [];
  const planTier = isPlanTier(me?.profile?.plan_tier) ? me.profile.plan_tier : inferPlanFromFeatures(enabledFeatures);
  const displayName =
    me?.customer_account?.full_name ||
    user?.firstName ||
    me?.profile?.first_name ||
    user?.primaryEmailAddress?.emailAddress ||
    user?.username ||
    user?.id ||
    'there';

  const paidOrders = useMemo(() => orders.filter((order) => ['paid', 'fulfilled'].includes(order.status)).length, [orders]);

  const activeSubscriptions = useMemo(
    () => subscriptions.filter((subscription) => ['active', 'trialing', 'past_due'].includes(subscription.status)),
    [subscriptions]
  );

  const readyDownloads = useMemo(() => downloads.filter((grant) => grant.can_download).length, [downloads]);

  const currentEntitlements = useMemo(
    () => entitlements.filter((entitlement) => entitlement.is_current).length,
    [entitlements]
  );

  const openServiceRequests = useMemo(
    () => bookings.filter((booking) => ['requested', 'confirmed'].includes(booking.status)).length,
    [bookings]
  );

  const publishedProducts = catalogProducts.length;
  const pricedProducts = useMemo(
    () => catalogProducts.filter((product) => Boolean(product.active_price || product.prices?.length)).length,
    [catalogProducts]
  );

  const configuredAiProviders = aiProviders.filter((provider) => provider.enabled).length;
  const bucketsNearLimit = aiUsage.buckets.filter((bucket) => bucket.near_limit).length;
  const subscriptionUsageReady = activeSubscriptions.length > 0 && aiUsage.buckets.length > 0;

  const sendPreflightEmailTest = async (): Promise<void> => {
    setEmailTestStatus((previous) => ({
      ...previous,
      running: true,
      detail: 'Sending test email...',
    }));
    setError('');
    try {
      const payload = await authedRequest<PreflightEmailResponse>(getToken, '/account/preflight/email-test/', {
        method: 'POST',
      });
      const sentAt = String(payload.sent_at || new Date().toISOString());
      const recipientEmail = String(payload.recipient_email || '');
      const detail = payload.detail || `Test email sent at ${new Date(sentAt).toLocaleString()}.`;
      setEmailTestStatus({
        sent: Boolean(payload.sent),
        detail,
        recipientEmail,
        sentAt,
        running: false,
      });
      if (typeof window !== 'undefined' && payload.sent) {
        window.localStorage.setItem(
          PREFLIGHT_EMAIL_STORAGE_KEY,
          JSON.stringify({
            recipient_email: recipientEmail,
            sent_at: sentAt,
          })
        );
      }
      await loadDashboard({ silent: true });
    } catch (requestError) {
      setEmailTestStatus((previous) => ({
        ...previous,
        sent: false,
        running: false,
        detail: requestError instanceof Error ? requestError.message : 'Could not send test email.',
      }));
    }
  };

  const preflightSteps: Array<{
    key: string;
    label: string;
    done: boolean;
    hint: string;
    actionLabel: string;
    route?: string;
    action?: () => void;
  }> = [
    {
      key: 'clerk_sync',
      label: 'Clerk auth and account sync',
      done: Boolean(me?.profile) && Boolean(me?.customer_account),
      hint: 'Sign in and verify `/api/me/` returns profile and customer account data.',
      actionLabel: 'Refresh check',
      action: () => {
        loadDashboard({ silent: true });
      },
    },
    {
      key: 'supabase_probe',
      label: 'Supabase bridge test',
      done: supabaseProbe.checked && supabaseProbe.ok,
      hint: supabaseProbe.detail,
      actionLabel: 'Run Supabase probe',
      action: () => {
        loadDashboard({ silent: true });
      },
    },
    {
      key: 'resend_email',
      label: 'Resend delivery test',
      done: emailTestStatus.sent,
      hint: emailTestStatus.sent
        ? `${emailTestStatus.detail}${emailTestStatus.recipientEmail ? ` Recipient: ${emailTestStatus.recipientEmail}.` : ''}`
        : emailTestStatus.detail || 'Send one test email before starting product work.',
      actionLabel: emailTestStatus.running ? 'Sending...' : 'Send test email',
      action: () => {
        if (!emailTestStatus.running) {
          void sendPreflightEmailTest();
        }
      },
    },
    {
      key: 'order_attempt',
      label: 'Order placement test',
      done: orders.length > 0,
      hint: 'Place one test order from `/products` and confirm it appears in purchases.',
      actionLabel: 'Run order test',
      route: '/products',
    },
    {
      key: 'webhook_payment',
      label: 'Webhook payment confirmation test',
      done: paidOrders > 0,
      hint: 'Complete checkout and verify order status changes to `paid` or `fulfilled`.',
      actionLabel: 'Review purchases',
      route: '/account/purchases',
    },
    {
      key: 'subscription_usage',
      label: 'Subscription and usage test',
      done: subscriptionUsageReady,
      hint: 'Run one recurring checkout and verify subscription plus usage buckets in `/app`.',
      actionLabel: 'Open subscriptions',
      route: '/account/subscriptions',
    },
  ];

  const completedPreflightCount = preflightSteps.filter((step) => step.done).length;
  const preflightComplete = completedPreflightCount === preflightSteps.length;
  const nextPreflightStep = preflightSteps.find((step) => !step.done);

  const requestAccess = async (token: string): Promise<void> => {
    setAccessingToken(token);
    setError('');
    try {
      const payload = await authedRequest<DownloadAccessResponse>(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST',
      });
      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      await loadDashboard({ silent: true });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not generate download access.');
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <>
      <section className={cn(sectionClass, 'space-y-6 bg-gradient-to-br from-slate-50 to-cyan-50 dark:from-slate-900 dark:to-slate-900')}>
        <PageIntro
          eyebrow="Before You Start"
          title={`Run preflight validation before building features, ${displayName}.`}
          description="Use this checklist to prove Clerk auth, Supabase connectivity, Resend delivery, order flow, webhook payment confirmation, and subscription usage behavior."
          actions={(
            <>
              {nextPreflightStep ? (
                <button
                  type="button"
                  className={buttonPrimary}
                  onClick={() => {
                    if (nextPreflightStep.action) {
                      nextPreflightStep.action();
                      return;
                    }
                    if (nextPreflightStep.route) {
                      onNavigate(nextPreflightStep.route);
                    }
                  }}
                >
                  Continue: {nextPreflightStep.label}
                </button>
              ) : (
                <button type="button" className={buttonPrimary} onClick={() => onNavigate('/products')}>
                  Open Offers
                </button>
              )}
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
                Offers
              </button>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
                Pricing
              </button>
              {BILLING_PORTAL_URL ? (
                <a className={buttonSecondary} href={BILLING_PORTAL_URL} target="_blank" rel="noreferrer">
                  Manage Billing
                </a>
              ) : (
                <SubscriptionDetailsButton>
                  <button type="button" className={buttonSecondary}>Manage Billing</button>
                </SubscriptionDetailsButton>
              )}
            </>
          )}
        />

        <TutorialBlock
          whatThisDoes="Turns integration setup into explicit preflight checks before product build work starts."
          howToTest={[
            'Run each preflight test from top to bottom',
            'Use refresh to re-check current integration status',
            'Keep notes on which step failed before debugging',
          ]}
          expectedResult="You can verify the full stack works before writing custom feature code."
        />

        <article className={cardClass}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Preflight validation</h2>
            <p className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {completedPreflightCount}/{preflightSteps.length} passing
            </p>
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            {preflightComplete
              ? 'All preflight checks passed. Start building your product-specific features.'
              : 'Resolve every failing check before starting custom product work.'}
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {preflightSteps.map((step, index) => (
              <article
                key={step.key}
                className={cn(
                  'rounded-xl border p-4',
                  step.done
                    ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20'
                    : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800'
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-900 text-xs font-semibold text-white dark:bg-cyan-400 dark:text-slate-950">
                      {index + 1}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{step.label}</h3>
                  </div>
                  <StatusPill value={step.done ? 'done' : 'next'} />
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{step.hint}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={step.key === 'resend_email' && emailTestStatus.running}
                    onClick={() => {
                      if (step.action) {
                        step.action();
                        return;
                      }
                      if (step.route) {
                        onNavigate(step.route);
                      }
                    }}
                  >
                    {step.actionLabel}
                  </button>
                  {step.route ? (
                    <button type="button" className={buttonGhost} onClick={() => onNavigate(step.route!)}>
                      Open route
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </article>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Preflight"
            value={`${completedPreflightCount}/${preflightSteps.length}`}
            note={preflightComplete ? 'All checks passing' : 'Checks still pending'}
          />
          <MetricCard
            label="Supabase Probe"
            value={supabaseProbe.ok ? 'PASS' : 'FAIL'}
            note={supabaseProbe.detail}
          />
          <MetricCard
            label="Resend Test"
            value={emailTestStatus.sent ? 'SENT' : 'PENDING'}
            note={emailTestStatus.sent ? emailTestStatus.detail : 'Send one preflight email'}
          />
          <MetricCard label="Plan" value={planTier.toUpperCase()} note={`${enabledFeatures.length} features enabled`} />
          <MetricCard label="Offers" value={String(publishedProducts)} note={`${pricedProducts} with active price`} />
          <MetricCard label="Paid Orders" value={String(paidOrders)} note={`${orders.length} total purchases`} />
          <MetricCard label="Active Subs" value={String(activeSubscriptions.length)} note={`${subscriptions.length} total subscriptions`} />
          <MetricCard label="Downloads" value={String(readyDownloads)} note={`${downloads.length} total deliveries`} />
          <MetricCard label="Entitlements" value={String(currentEntitlements)} note="Current access records" />
          <MetricCard label="Service Requests" value={String(openServiceRequests)} note="Bookings in progress" />
          <MetricCard
            label="AI Providers"
            value={String(configuredAiProviders)}
            note={`${bucketsNearLimit} usage bucket(s) near limit`}
          />
        </div>
      </section>

      {error ? (
        <section className={cn(sectionClass, 'border-rose-300 bg-rose-50/70 dark:border-rose-700 dark:bg-rose-900/20')}>
          <p className="text-sm font-medium text-rose-700 dark:text-rose-300">{error}</p>
        </section>
      ) : null}

      <section className={cn(sectionClass, 'space-y-6')}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Recent activity</h2>
          <button type="button" className={buttonSecondary} onClick={() => loadDashboard({ silent: true })}>
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recent purchases</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/purchases')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading purchases...</p> : null}
            {!loading && orders.length === 0 ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No purchases yet.</p> : null}
            <div className="mt-3 space-y-3">
              {orders.slice(0, 4).map((order) => (
                <article key={order.public_id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Order {String(order.public_id).slice(0, 8)}</h4>
                    <StatusPill value={order.status} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {formatCurrencyFromCents(order.total_cents, order.currency)}
                  </p>
                </article>
              ))}
            </div>
          </article>

          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Digital deliveries</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/downloads')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading downloads...</p> : null}
            {!loading && downloads.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No digital deliveries yet.</p>
            ) : null}
            <div className="mt-3 space-y-3">
              {downloads.slice(0, 4).map((grant) => (
                <article key={grant.token} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{grant.asset_title}</h4>
                    <StatusPill value={grant.can_download ? 'ready' : 'locked'} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{grant.product_name}</p>
                  <button
                    type="button"
                    className={cn(buttonPrimary, 'mt-2 w-full')}
                    disabled={!grant.can_download || accessingToken === grant.token}
                    onClick={() => requestAccess(grant.token)}
                  >
                    {accessingToken === grant.token ? 'Preparing...' : 'Download'}
                  </button>
                </article>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className={cn(sectionClass, 'space-y-6')}>
        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Subscriptions, access, and AI usage</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Subscription state</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/subscriptions')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading subscriptions...</p> : null}
            {!loading && activeSubscriptions.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No active subscriptions found.</p>
            ) : null}
            <div className="mt-3 space-y-3">
              {activeSubscriptions.slice(0, 4).map((subscription) => (
                <article key={subscription.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                      {subscription.product_name || 'Subscription'}
                    </h4>
                    <StatusPill value={subscription.status} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {subscription.price_summary
                      ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                      : 'No linked local price'}
                  </p>
                </article>
              ))}
            </div>
            <h4 className="mt-4 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">Current entitlements</h4>
            <div className="mt-2 flex flex-wrap gap-2">
              {entitlements
                .filter((entitlement) => entitlement.is_current)
                .slice(0, 8)
                .map((entitlement) => (
                  <span
                    className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    key={entitlement.id}
                  >
                    {entitlement.feature_key}
                  </span>
                ))}
              {entitlements.filter((entitlement) => entitlement.is_current).length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No active entitlements yet.</p>
              ) : null}
            </div>
          </article>

          <article className={cardClass}>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">AI provider and usage scaffold</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Built-in placeholders for OpenRouter and Ollama help you wire AI products with usage-aware subscription plans.
            </p>
            <div className="mt-3 space-y-2">
              {aiProviders.map((provider) => (
                <article key={provider.key} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{provider.label}</h4>
                      <p className="text-xs text-slate-600 dark:text-slate-300">{provider.base_url}</p>
                    </div>
                    <StatusPill value={provider.enabled ? 'configured' : 'disabled'} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{provider.env_vars.join(', ')}</p>
                </article>
              ))}
              {aiProviders.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No providers detected yet.</p>
              ) : null}
            </div>
            <div className="mt-3 space-y-2">
              {aiUsage.buckets.map((bucket) => (
                <UsageBar key={bucket.key} bucket={bucket} />
              ))}
              {aiUsage.buckets.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No usage buckets configured yet.</p>
              ) : null}
            </div>
            {aiUsage.notes.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-600 dark:text-slate-300">
                {aiUsage.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
          </article>
        </div>
      </section>

      <section className={cn(sectionClass, 'space-y-4')}>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Developer context</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          API base: <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">{apiBase}</code>
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Refresh status: {refreshing ? 'updating now' : 'automatic on load and download actions'}
        </p>
        {user ? (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Signed in as {user.primaryEmailAddress?.emailAddress || user.username || user.id}
          </p>
        ) : null}
      </section>
    </>
  );
}

function SignedOutApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const hiddenCatalogPath = pathname === '/pricing' || pathname === '/products' || pathname.startsWith('/products/');
  const normalizedPath = hiddenCatalogPath ? '/' : pathname;
  const content = hiddenCatalogPath ? (
    <>
      <section className={cn(sectionClass, 'border-amber-300 bg-amber-50/70 dark:border-amber-700 dark:bg-amber-900/20')}>
        <PageIntro
          eyebrow="Template preview"
          title="Catalog and pricing are locked while signed out"
          description="Sign in to configure offers and verify checkout plus fulfillment from account routes."
        />
      </section>
      <MarketingHome />
    </>
  ) : (
    <MarketingHome />
  );

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 pb-20 pt-6 sm:px-6 lg:px-8">
      <Header
        pathname={normalizedPath}
        onNavigate={onNavigate}
        signedIn={false}
        expandedNav={false}
        themeLabel={themeLabel}
        onToggleTheme={onToggleTheme}
      />
      {content}
    </main>
  );
}

function SignedInApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const { getToken } = useAuth();
  const isProductDetail = pathname.startsWith('/products/');
  const productSlug = isProductDetail ? pathname.replace('/products/', '') : '';
  let content: ReactNode = <AccountDashboard onNavigate={onNavigate} getToken={getToken} />;

  if (pathname === '/pricing') {
    content = <PricingPage signedIn />;
  } else if (pathname === '/products') {
    content = <ProductCatalog onNavigate={onNavigate} />;
  } else if (isProductDetail && productSlug) {
    content = <ProductDetail slug={productSlug} signedIn onNavigate={onNavigate} getToken={getToken} />;
  } else if (pathname === '/account/purchases') {
    content = <PurchasesPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/subscriptions') {
    content = <SubscriptionsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/downloads') {
    content = <DownloadsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/bookings') {
    content = <BookingsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/success') {
    content = <CheckoutState state="success" onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/cancel') {
    content = <CheckoutState state="cancel" onNavigate={onNavigate} />;
  } else if (pathname !== '/' && pathname !== '/app') {
    content = (
      <section className={sectionClass}>
        <PageIntro
          eyebrow="404"
          title="Page not found"
          description="This route is not part of the current app map."
          actions={
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/app')}>
              Back to Dashboard
            </button>
          }
        />
      </section>
    );
  }

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 pb-20 pt-6 sm:px-6 lg:px-8">
      <Header
        pathname={pathname}
        onNavigate={onNavigate}
        signedIn
        expandedNav
        themeLabel={themeLabel}
        onToggleTheme={onToggleTheme}
      />
      {content}
    </main>
  );
}

export function App(): ReactElement {
  useSignals();

  const { pathname, navigate } = usePathname();

  useSignalEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const themeValue = themeSignal.value;
    document.documentElement.classList.toggle('dark', themeValue === 'dark');
    document.documentElement.dataset.theme = themeValue;
    window.localStorage.setItem(THEME_STORAGE_KEY, themeValue);
  });

  const themeLabel = nextThemeLabelSignal.value;

  return (
    <>
      <SignedOut>
        <SignedOutApp
          pathname={pathname}
          onNavigate={navigate}
          themeLabel={themeLabel}
          onToggleTheme={toggleThemeSignal}
        />
      </SignedOut>
      <SignedIn>
        <SignedInApp
          pathname={pathname}
          onNavigate={navigate}
          themeLabel={themeLabel}
          onToggleTheme={toggleThemeSignal}
        />
      </SignedIn>
    </>
  );
}
