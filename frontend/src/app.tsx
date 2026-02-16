import {
  PricingTable,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
  useUser
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
  toggleThemeSignal
} from './lib/signals';

const BILLING_PORTAL_URL = (import.meta.env.VITE_CLERK_BILLING_PORTAL_URL || '').trim();
const ENABLE_DEV_MANUAL_CHECKOUT =
  (import.meta.env.VITE_ENABLE_DEV_MANUAL_CHECKOUT || '').trim().toLowerCase() === 'true';
const CHECKLIST_STORAGE_KEY = 'ds-launch-checklist-complete';

type Id = number | string;
type NavigateFn = (nextPath: string) => void;
type CheckoutStateValue = 'success' | 'cancel';
type PlanTier = 'free' | 'pro' | 'enterprise';
type GetTokenFn = ReturnType<typeof useAuth>['getToken'];

interface CopyCard {
  title: string;
  body?: string;
  points: string[];
}

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
  onChecklistStateChange: (complete: boolean) => void;
}

interface SignedAppProps {
  pathname: string;
  onNavigate: NavigateFn;
  themeLabel: string;
  onToggleTheme: () => void;
}

interface ScreenIntroProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

interface LivingTutorialProps {
  whatThisDoes: string;
  howToTest: string[];
  expectedResult: string;
}

function formatCurrencyFromCents(cents: number, currency = 'USD'): string {
  const numeric = Number(cents || 0) / 100;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
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

function NavLink({ to, currentPath, onNavigate, children }: NavLinkProps): ReactElement {
  const active = currentPath === to;

  return (
    <a
      href={to}
      className={`site-link ${active ? 'site-link-active' : ''}`}
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
    <header className="site-header panel">
      <div className="site-brand-shell" onClick={() => onNavigate(signedIn ? '/app' : '/')}>
        <div className="site-brand-mark">DS</div>
        <div className="site-brand-text">
          <strong className="site-brand">DjangoStarter</strong>
          <span className="site-brand-subtitle">Launch stack for AI and creator SaaS</span>
        </div>
      </div>
      <nav className="site-nav" aria-label="Primary">
        <NavLink to={signedIn ? '/app' : '/'} currentPath={pathname} onNavigate={onNavigate}>
          {signedIn ? 'Dashboard' : 'Home'}
        </NavLink>
        {signedIn ? (
          <>
            <NavLink to="/products" currentPath={pathname} onNavigate={onNavigate}>Offers</NavLink>
            <NavLink to="/pricing" currentPath={pathname} onNavigate={onNavigate}>Pricing</NavLink>
            {expandedNav ? (
              <>
                <NavLink to="/account/purchases" currentPath={pathname} onNavigate={onNavigate}>Purchases</NavLink>
                <NavLink to="/account/downloads" currentPath={pathname} onNavigate={onNavigate}>Downloads</NavLink>
                <NavLink to="/account/subscriptions" currentPath={pathname} onNavigate={onNavigate}>Subscriptions</NavLink>
                <NavLink to="/account/bookings" currentPath={pathname} onNavigate={onNavigate}>Bookings</NavLink>
              </>
            ) : null}
          </>
        ) : null}
      </nav>
      <div className="site-actions">
        <button type="button" className="button button-ghost theme-toggle" onClick={onToggleTheme}>
          {themeLabel}
        </button>
        {signedIn ? (
          <UserButton afterSignOutUrl="/" />
        ) : (
          <>
            <SignInButton mode="modal">
              <button type="button" className="button button-secondary">Sign In</button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button type="button" className="button button-primary">Start Free</button>
            </SignUpButton>
          </>
        )}
      </div>
    </header>
  );
}

function ScreenIntro({ eyebrow, title, description, actions }: ScreenIntroProps): ReactElement {
  return (
    <header className="screen-header">
      <p className="screen-eyebrow">{eyebrow}</p>
      <h1 className="screen-title">{title}</h1>
      <p className="screen-lead">{description}</p>
      {actions ? <div className="screen-actions">{actions}</div> : null}
    </header>
  );
}

function LivingTutorial({ whatThisDoes, howToTest, expectedResult }: LivingTutorialProps): ReactElement {
  return (
    <article className="tutorial-shell">
      <p className="eyebrow">Living Tutorial</p>
      <div className="tutorial-grid">
        <section className="tutorial-card">
          <h3>What this does</h3>
          <p>{whatThisDoes}</p>
        </section>
        <section className="tutorial-card">
          <h3>How to test now</h3>
          <ol className="tutorial-list">
            {howToTest.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </section>
        <section className="tutorial-card">
          <h3>Expected result</h3>
          <p>{expectedResult}</p>
        </section>
      </div>
    </article>
  );
}

function MarketingHome(): ReactElement {
  useSignals();

  const jumpToSection = (sectionId: string) => {
    const section = window.document.getElementById(sectionId);
    if (!section) {
      return;
    }
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const proofStats = [
    {
      label: 'Ideal Customer',
      value: 'Technical founder with first paid offer',
      note: 'One person shipping one monetized workflow with strict payment truth.'
    },
    {
      label: 'Core Promise',
      value: 'From idea to trusted checkout fast',
      note: 'You get billing, fulfillment, and account surfaces without writing platform glue.'
    },
    {
      label: 'Primary Outcome',
      value: 'Launch one working revenue loop in 7 days',
      note: 'Then optimize headline, offer packaging, and conversion.'
    }
  ];

  const contrastCards: CopyCard[] = [
    {
      title: 'Typical starter failure mode',
      body: 'Teams ship UI quickly, then burn weeks patching payment and access drift.',
      points: [
        'Client shows paid before server confirms payment',
        'Fulfillment logic branches in too many places',
        'Account pages feel empty and support-heavy after checkout'
      ]
    },
    {
      title: 'DjangoStarter mission path',
      body: 'You launch the first paid loop on rails, then iterate where revenue actually moves.',
      points: [
        'Order status changes from verified Clerk events',
        'Entitlements and fulfillment run server-side only',
        'Buyers instantly see purchases, subscriptions, and downloads'
      ]
    }
  ];

  const launchPath = [
    {
      title: 'Step 1: Position one paid offer',
      body: 'Pick one painful problem, one target buyer, and one concrete promised result.'
    },
    {
      title: 'Step 2: Configure catalog and price',
      body: 'Create one product and one active price in seller endpoints. Keep it simple.'
    },
    {
      title: 'Step 3: Validate payment truth',
      body: 'Run order create and webhook confirmation. Ensure paid state is server-verified.'
    },
    {
      title: 'Step 4: Validate fulfillment',
      body: 'Confirm download grants, subscriptions, entitlements, or bookings appear after payment.'
    },
    {
      title: 'Step 5: Tighten conversion copy',
      body: 'Once the loop works, improve messaging and CTAs without touching payment contracts.'
    }
  ];

  const shippedSurfaces: CopyCard[] = [
    {
      title: 'Core Commerce APIs',
      points: ['Catalog and pricing models', 'Order creation and confirmation paths', 'Subscription and entitlement lifecycle']
    },
    {
      title: 'Buyer Account Surfaces',
      points: ['/account/purchases', '/account/downloads', '/account/subscriptions and /account/bookings']
    },
    {
      title: 'Seller and Ops Controls',
      points: ['Seller product and price endpoints', 'Webhook receiver with signature verification', 'Deploy checks and backend test coverage']
    },
    {
      title: 'Developer Workflow',
      points: ['React 19 + Django + DRF base', 'Clerk auth and billing integration', 'Local and production safety flags']
    }
  ];

  return (
    <>
      <header className="panel reset-hero">
        <div className="reset-hero-grid">
          <div className="reset-hero-main">
            <p className="reset-kicker">One Offer. One Buyer. One Revenue Loop.</p>
            <h1 className="reset-title">Launch a trustworthy paid SaaS flow without rebuilding platform plumbing.</h1>
            <p className="reset-subtitle">
              This starter is built for technical founders launching their first paid AI workflow product.
              It gives you a strict backend payment contract plus account surfaces that actually work after checkout.
            </p>
            <div className="reset-actions">
              <SignUpButton mode="modal">
                <button type="button" className="button button-primary">Start Your First Revenue Loop</button>
              </SignUpButton>
              <button type="button" className="button button-secondary" onClick={() => jumpToSection('mission-path')}>
                See Mission Path
              </button>
              <button type="button" className="button button-secondary" onClick={() => jumpToSection('first-week')}>
                See First Week Plan
              </button>
            </div>
            <div className="reset-pill-row">
              <span>ICP: Technical Founder</span>
              <span>Offer: One Paid Workflow</span>
              <span>Django + DRF</span>
              <span>React 19</span>
              <span>Webhook Verified Orders</span>
            </div>
          </div>

          <aside className="reset-hero-aside">
            <p className="eyebrow">Why this feels different</p>
            <h3>The default path is launch-first, not framework-first.</h3>
            <ul className="check-grid">
              <li>Start with one buyer outcome instead of broad feature lists</li>
              <li>Keep payment and access truth on the server from day one</li>
              <li>Use account routes as a living QA and onboarding surface</li>
            </ul>
          </aside>
        </div>

        <div className="reset-stat-grid">
          {proofStats.map((stat) => (
            <article className="reset-stat-card" key={stat.label}>
              <p className="reset-stat-label">{stat.label}</p>
              <h3>{stat.value}</h3>
              <p className="reset-stat-note">{stat.note}</p>
            </article>
          ))}
        </div>
      </header>

      <section className="panel reset-section" id="mission-path">
        <p className="eyebrow">Mission Path</p>
        <h2>Fix the one thing that kills most MVP launches: unreliable revenue state.</h2>
        <div className="reset-two-up">
          {contrastCards.map((card) => (
            <article className="reset-card" key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
              <ul className="check-grid">
                {card.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="panel reset-section" id="first-week">
        <p className="eyebrow">First Week Plan</p>
        <h2>Follow this sequence and you get a working paid loop without seeded data.</h2>
        <ol className="reset-path">
          {launchPath.map((item, index) => (
            <li className="reset-path-item" key={item.title}>
              <span className="reset-path-index">{index + 1}</span>
              <div className="reset-path-body">
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="reset-actions">
          <button type="button" className="button button-secondary" onClick={() => jumpToSection('included-surfaces')}>
            See Included Surfaces
          </button>
        </div>
      </section>

      <section className="panel reset-section" id="included-surfaces">
        <p className="eyebrow">Included Surfaces</p>
        <h2>Everything needed for a strict revenue loop is already wired.</h2>
        <div className="landing-capability-grid">
          {shippedSurfaces.map((group) => (
            <article className="reset-card" key={group.title}>
              <h3>{group.title}</h3>
              <ul className="check-grid">
                {group.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="panel signal-lab">
        <p className="eyebrow">React 19 + Signals Example</p>
        <h2>The template also includes a live state example for fast frontend experimentation.</h2>
        <p className="helper-text">
          One signal updates the launch count, derived double, and momentum state across the UI.
        </p>
        <div className="feature-list">
          <span className="feature-tag">Launch Count: {launchCounterSignal.value}</span>
          <span className="feature-tag">Double: {launchCounterDoubleSignal.value}</span>
          <span className="feature-tag">Momentum: {launchCounterMomentumSignal.value}</span>
        </div>
        <div className="hero-actions">
          <button type="button" className="button button-primary" onClick={incrementLaunchCounterSignal}>
            Push Signal
          </button>
          <button type="button" className="button button-secondary" onClick={resetLaunchCounterSignal}>
            Reset
          </button>
        </div>
      </section>

      <section className="panel landing-final">
        <div>
          <p className="eyebrow">Bottom Line</p>
          <h2>If your first paid loop is not trustworthy, nothing else matters.</h2>
          <p className="helper-text">
            Use this starter to get payment truth, fulfillment, and customer account behavior correct first.
          </p>
        </div>
        <div className="landing-final-actions">
          <SignUpButton mode="modal">
            <button type="button" className="button button-primary">Start Free and Launch</button>
          </SignUpButton>
          <SignInButton mode="modal">
            <button type="button" className="button button-secondary">Sign In</button>
          </SignInButton>
        </div>
        <ul className="check-grid">
          <li>No hardcoded frontend pricing assumptions</li>
          <li>No production payment confirmation shortcuts</li>
          <li>No deploy without tests and build passing</li>
        </ul>
      </section>
    </>
  );
}

function PricingPage({ signedIn }: PricingPageProps): ReactElement {
  return (
    <section className="screen">
      <ScreenIntro
        eyebrow="Pricing"
        title="Live billing plans from Clerk"
        description="Configure plans in Clerk Billing and this page renders the latest catalog in real time."
      />
      <LivingTutorial
        whatThisDoes="Renders your live Clerk pricing table so customers can select plans and start checkout."
        howToTest={[
          'Open Clerk Billing and create at least one plan',
          'Refresh this page and confirm the plan appears',
          'Use the plan CTA and confirm checkout opens'
        ]}
        expectedResult="Plans render from Clerk config, not hardcoded frontend values."
      />
      <div className="surface-card pricing-shell">
        <PricingTable />
      </div>
      {signedIn ? (
        <p className="helper-text">Signed in customers can manage active plans from subscriptions.</p>
      ) : (
        <p className="helper-text">Sign in to subscribe and manage your billing profile.</p>
      )}
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
    <section className="screen">
      <ScreenIntro
        eyebrow="Catalog"
        title="Offers ready to buy"
        description="Choose a digital product or service offer. Clerk handles payment while the app handles fulfillment."
      />
      <LivingTutorial
        whatThisDoes="Lists published offers from your product catalog API and routes buyers into product detail checkout flows."
        howToTest={[
          'Create one product with an active price using seller endpoints',
          'Refresh this page and verify the product card appears with price',
          'Open the offer and continue into checkout'
        ]}
        expectedResult="Catalog displays only published offers and current active price data."
      />
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading catalog...</p> : null}
      {!loading && products.length === 0 ? (
        <article className="surface-card">
          <h3 className="surface-title">No published products yet</h3>
          <p className="surface-copy">
            Create your first product and active price from seller endpoints, then return here to validate catalog rendering.
          </p>
          <div className="screen-actions">
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/pricing')}>
              Open Pricing Surface
            </button>
            <button type="button" className="button button-primary" onClick={() => onNavigate('/app')}>
              Open Launch Checklist
            </button>
          </div>
        </article>
      ) : null}

      <div className="cards-grid cards-grid-3">
        {products.map((product) => (
          <article key={product.id} className="surface-card">
            <div className="surface-head">
              <span className={`pill pill-${product.product_type}`}>{product.product_type}</span>
              {product.active_price ? (
                <strong className="price-inline">
                  {formatCurrencyFromCents(product.active_price.amount_cents, product.active_price.currency)}
                </strong>
              ) : (
                <strong className="price-inline">Unpriced</strong>
              )}
            </div>
            <h3 className="surface-title">{product.name}</h3>
            <p className="surface-copy">{product.tagline || product.description || 'No description yet.'}</p>
            <button
              type="button"
              className="button button-secondary"
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
          body: { price_id: priceId, quantity: 1 }
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
          'Checkout URL missing for this price. Configure Clerk checkout metadata or enable VITE_ENABLE_DEV_MANUAL_CHECKOUT for local simulation only.'
        );
      }

      await authedRequest<unknown, { provider: string; external_id: string }>(
        getToken,
        `/account/orders/${publicId}/confirm/`,
        {
          method: 'POST',
          body: {
            provider: 'manual',
            external_id: `manual_${Date.now()}`
          }
        }
      );

      setSuccess('Purchase completed. Your fulfillment has been created.');
      onNavigate('/checkout/success');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not complete purchase flow.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <section className="screen">
        <ScreenIntro
          eyebrow="Offer"
          title="Loading offer"
          description="We are fetching product details, pricing, and fulfillment metadata."
        />
      </section>
    );
  }

  if (!product) {
    return (
      <section className="screen">
        <ScreenIntro
          eyebrow="Offer"
          title="Offer not found"
          description="This product route does not map to a published offer."
        />
      </section>
    );
  }

  return (
    <section className="screen">
      <ScreenIntro
        eyebrow="Offer Detail"
        title={product.name}
        description={product.description || product.tagline || 'No description yet.'}
        actions={(
          <>
            <span className={`pill pill-${product.product_type}`}>{product.product_type}</span>
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/products')}>
              Back to Catalog
            </button>
          </>
        )}
      />
      <LivingTutorial
        whatThisDoes="Shows offer pricing options and sends buyers into secure order creation and checkout."
        howToTest={[
          'Confirm at least one price exists for this product',
          'Click Buy Now and verify order create succeeds',
          'Complete payment and confirm redirect to checkout success'
        ]}
        expectedResult="Order starts pending, payment confirms server-side, and fulfillment appears in account routes."
      />

      {error ? <p className="warning-text">{error}</p> : null}
      {success ? <p className="success-text">{success}</p> : null}

      {!product.prices?.length ? (
        <article className="surface-card">
          <h3 className="surface-title">No price attached to this offer</h3>
          <p className="surface-copy">
            Add at least one active price through seller APIs, then return to validate purchase flow.
          </p>
          <div className="screen-actions">
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
            <button type="button" className="button button-primary" onClick={() => onNavigate('/app')}>
              Back to Checklist
            </button>
          </div>
        </article>
      ) : (
        <div className="cards-grid cards-grid-2">
          {(product.prices || []).map((price) => (
            <article className="surface-card" key={price.id}>
              <div className="surface-head">
                <h3 className="surface-title">{price.name || price.billing_period}</h3>
                <span className="plan-price">{formatCurrencyFromCents(price.amount_cents, price.currency)}</span>
              </div>
              <p className="plan-audience">Billed {price.billing_period.replace('_', ' ')}</p>
              <button
                type="button"
                className="button button-primary"
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
        <article className="surface-card">
          <h2 className="surface-title">Included assets</h2>
          <ul className="check-grid">
            {product.assets.map((asset) => (
              <li key={asset.id}>{asset.title}</li>
            ))}
          </ul>
        </article>
      ) : null}

      {product.service_offer ? (
        <article className="surface-card">
          <h2 className="surface-title">Service delivery</h2>
          <ul className="check-grid">
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
    <section className="screen">
      <ScreenIntro
        eyebrow="Account"
        title="Purchases"
        description="Track order status, totals, and purchased item counts."
      />
      <LivingTutorial
        whatThisDoes="Displays every order tied to the signed-in account with payment state and totals."
        howToTest={[
          'Complete a checkout from any offer',
          'Return here after webhook confirmation',
          'Verify order status changes from pending to paid or fulfilled'
        ]}
        expectedResult="Orders reflect server-side payment truth, not optimistic frontend assumptions."
      />
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading purchases...</p> : null}
      {!loading && orders.length === 0 ? (
        <article className="surface-card">
          <h3 className="surface-title">No purchases yet</h3>
          <p className="surface-copy">
            Start from catalog, run one checkout, then come back to validate paid order state.
          </p>
          <div className="screen-actions">
            <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
              Browse Offers
            </button>
          </div>
        </article>
      ) : null}

      <div className="cards-grid cards-grid-2">
        {orders.map((order) => (
          <article key={order.public_id} className="surface-card">
            <div className="surface-head">
              <h3 className="surface-title">Order {String(order.public_id).slice(0, 8)}</h3>
              <span className={`pill pill-${order.status}`}>{order.status}</span>
            </div>
            <p className="surface-copy">Total: {formatCurrencyFromCents(order.total_cents, order.currency)}</p>
            <p className="surface-copy">{order.items?.length || 0} item(s)</p>
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
    <section className="screen">
      <ScreenIntro
        eyebrow="Account"
        title="Subscriptions"
        description="See all recurring plans and subscription status in one place."
      />
      <LivingTutorial
        whatThisDoes="Shows recurring subscription records and current billing state for this customer."
        howToTest={[
          'Subscribe to a recurring plan from pricing or an offer',
          'Return here and confirm subscription appears with status',
          'Open Clerk details and verify plan metadata matches'
        ]}
        expectedResult="Subscription status and plan amount remain consistent across app and Clerk."
      />
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading subscriptions...</p> : null}
      {!loading && subscriptions.length === 0 ? (
        <article className="surface-card">
          <h3 className="surface-title">No active subscriptions found</h3>
          <p className="surface-copy">
            Add a recurring plan and run one subscription checkout to validate this page.
          </p>
          <button type="button" className="button button-primary" onClick={() => onNavigate('/pricing')}>
            Open Pricing
          </button>
        </article>
      ) : null}

      <div className="cards-grid cards-grid-2">
        {subscriptions.map((subscription) => (
          <article key={subscription.id} className="surface-card">
            <div className="surface-head">
              <h3 className="surface-title">{subscription.product_name || 'Subscription'}</h3>
              <span className={`pill pill-${subscription.status}`}>{subscription.status}</span>
            </div>
            <p className="surface-copy">
              {subscription.price_summary
                ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                : 'No linked local price'}
            </p>
          </article>
        ))}
      </div>

      <SignedIn>
        <div className="surface-card">
          <h3 className="surface-title">Manage in Clerk</h3>
          <p className="surface-copy">Open Clerk subscription details for invoices and payment methods.</p>
          <SubscriptionDetailsButton>
            <button type="button" className="button button-secondary">Open Subscription Details</button>
          </SubscriptionDetailsButton>
        </div>
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
        method: 'POST'
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
    <section className="screen">
      <ScreenIntro
        eyebrow="Account"
        title="Downloads"
        description="Generate secure download links and track grant usage."
      />
      <LivingTutorial
        whatThisDoes="Lists digital delivery grants and creates temporary access links per granted asset."
        howToTest={[
          'Buy a digital product with attached asset',
          'Return here and confirm grant shows as ready',
          'Request link and verify usage count updates'
        ]}
        expectedResult="Only eligible grants can generate access links and counts increment correctly."
      />
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading downloadable assets...</p> : null}
      {!loading && grants.length === 0 ? (
        <article className="surface-card">
          <h3 className="surface-title">No digital deliveries yet</h3>
          <p className="surface-copy">
            Fulfillment grants are created after paid digital orders. Run one checkout first.
          </p>
          <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
            Browse Offers
          </button>
        </article>
      ) : null}

      <div className="cards-grid cards-grid-2">
        {grants.map((grant) => (
          <article key={grant.token} className="surface-card">
            <div className="surface-head">
              <h3 className="surface-title">{grant.asset_title}</h3>
              <span className={`pill ${grant.can_download ? 'pill-live' : 'pill-paused'}`}>
                {grant.can_download ? 'ready' : 'locked'}
              </span>
            </div>
            <p className="surface-copy">{grant.product_name}</p>
            <p className="surface-copy">{grant.download_count}/{grant.max_downloads} downloads used</p>
            <button
              type="button"
              className="button button-primary"
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
    <section className="screen">
      <ScreenIntro
        eyebrow="Account"
        title="Bookings"
        description="Review service delivery requests and customer notes."
      />
      <LivingTutorial
        whatThisDoes="Tracks service bookings generated by fulfilled service offer purchases."
        howToTest={[
          'Create a service product and attach offer details',
          'Purchase the service offer and wait for fulfillment',
          'Confirm booking record appears with status and notes'
        ]}
        expectedResult="Every paid service order creates a booking record that can be managed operationally."
      />
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading booking requests...</p> : null}
      {!loading && bookings.length === 0 ? (
        <article className="surface-card">
          <h3 className="surface-title">No service bookings yet</h3>
          <p className="surface-copy">
            Service bookings appear after paid service fulfillment. Configure one service offer and test purchase.
          </p>
          <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
            Open Offers
          </button>
        </article>
      ) : null}

      <div className="cards-grid cards-grid-2">
        {bookings.map((booking) => (
          <article key={booking.id} className="surface-card">
            <div className="surface-head">
              <h3 className="surface-title">{booking.product_name || 'Service booking'}</h3>
              <span className={`pill pill-${booking.status}`}>{booking.status}</span>
            </div>
            <p className="surface-copy">{booking.customer_notes || 'No notes provided.'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function CheckoutState({ state, onNavigate }: CheckoutStateProps): ReactElement {
  const isSuccess = state === 'success';
  return (
    <section className={`screen ${isSuccess ? 'state-success' : 'state-cancel'}`}>
      <ScreenIntro
        eyebrow="Checkout"
        title={isSuccess ? 'Checkout Successful' : 'Checkout Canceled'}
        description={
          isSuccess
            ? 'Payment completed and fulfillment is now available in your account.'
          : 'No charge was made. Return to products and try checkout again.'
        }
      />
      <LivingTutorial
        whatThisDoes="Confirms final checkout outcome and sends users to the next high-value validation step."
        howToTest={[
          'Complete checkout once to hit success route',
          'Cancel checkout once to hit cancel route',
          'Follow CTA and confirm downstream pages reflect state correctly'
        ]}
        expectedResult="Users always have a clear next action after checkout, never a dead-end page."
      />
      <p className="helper-text">
        {isSuccess
          ? 'Payment completed. Your order fulfillment is available in purchases and downloads.'
          : 'No charge was made. You can return to product details and try again.'}
      </p>
      <div className="screen-actions">
        <button type="button" className="button button-primary" onClick={() => onNavigate('/account/purchases')}>
          View Purchases
        </button>
        <button type="button" className="button button-secondary" onClick={() => onNavigate('/products')}>
          Browse Products
        </button>
      </div>
    </section>
  );
}

function MetricCard({ label, value, note }: MetricCardProps): ReactElement {
  return (
    <article className="surface-card metric-card">
      <p className="metric-label">{label}</p>
      <h3 className="metric-value">{value}</h3>
      <p className="metric-note">{note}</p>
    </article>
  );
}

function AccountDashboard({ onNavigate, onChecklistStateChange }: DashboardProps): ReactElement {
  const { getToken, isLoaded, userId } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState<MeResponse | null>(null);
  const [billing, setBilling] = useState<BillingFeaturesResponse>({ enabled_features: [] });
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [downloads, setDownloads] = useState<DownloadGrant[]>([]);
  const [entitlements, setEntitlements] = useState<EntitlementRecord[]>([]);
  const [bookings, setBookings] = useState<BookingRecord[]>([]);
  const [catalogProducts, setCatalogProducts] = useState<ProductRecord[]>([]);
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
        catalogPayload
      ] = await Promise.all([
        authedRequest<MeResponse>(getToken, '/me/'),
        authedRequest<BillingFeaturesResponse>(getToken, '/billing/features/'),
        authedRequest<OrderRecord[]>(getToken, '/account/orders/'),
        authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/'),
        authedRequest<DownloadGrant[]>(getToken, '/account/downloads/'),
        authedRequest<EntitlementRecord[]>(getToken, '/account/entitlements/'),
        authedRequest<BookingRecord[]>(getToken, '/account/bookings/'),
        apiRequest<ProductRecord[]>('/products/').catch(() => [])
      ]);
      setMe(mePayload || null);
      setBilling(billingPayload || { enabled_features: [] });
      setOrders(Array.isArray(ordersPayload) ? ordersPayload : []);
      setSubscriptions(Array.isArray(subscriptionsPayload) ? subscriptionsPayload : []);
      setDownloads(Array.isArray(downloadsPayload) ? downloadsPayload : []);
      setEntitlements(Array.isArray(entitlementsPayload) ? entitlementsPayload : []);
      setBookings(Array.isArray(bookingsPayload) ? bookingsPayload : []);
      setCatalogProducts(Array.isArray(catalogPayload) ? catalogPayload : []);
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

  const paidOrders = useMemo(
    () => orders.filter((order) => ['paid', 'fulfilled'].includes(order.status)).length,
    [orders]
  );

  const activeSubscriptions = useMemo(
    () => subscriptions.filter((subscription) => ['active', 'trialing', 'past_due'].includes(subscription.status)),
    [subscriptions]
  );

  const readyDownloads = useMemo(
    () => downloads.filter((grant) => grant.can_download).length,
    [downloads]
  );

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

  const launchChecklist = [
    {
      key: 'offer',
      label: 'Publish one offer',
      route: '/products',
      done: publishedProducts > 0,
      hint: 'Create one product with a clear buyer outcome.'
    },
    {
      key: 'price',
      label: 'Attach one active price',
      route: '/pricing',
      done: pricedProducts > 0,
      hint: 'Every offer needs a live price to test conversion.'
    },
    {
      key: 'payment',
      label: 'Create one order attempt',
      route: '/account/purchases',
      done: orders.length > 0,
      hint: 'Start checkout from any offer and confirm an order record exists.'
    },
    {
      key: 'payment_confirm',
      label: 'Confirm paid status',
      route: '/account/purchases',
      done: paidOrders > 0,
      hint: 'Wait for webhook processing and verify order moves to paid or fulfilled.'
    },
    {
      key: 'fulfillment',
      label: 'Verify fulfillment output',
      route: '/account/downloads',
      done: readyDownloads > 0 || bookings.length > 0 || currentEntitlements > 0 || activeSubscriptions.length > 0,
      hint: 'Confirm downloads, bookings, subscriptions, or entitlements appear in account routes.'
    }
  ];

  const completedChecklistCount = launchChecklist.filter((step) => step.done).length;
  const checklistComplete = completedChecklistCount === launchChecklist.length;
  const nextChecklistStep = launchChecklist.find((step) => !step.done);

  useEffect(() => {
    onChecklistStateChange(checklistComplete);
  }, [checklistComplete, onChecklistStateChange]);

  const requestAccess = async (token: string): Promise<void> => {
    setAccessingToken(token);
    setError('');
    try {
      const payload = await authedRequest<DownloadAccessResponse>(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST'
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
      <section className="screen">
        <ScreenIntro
          eyebrow="Launch Console"
          title={`Ship the first paid loop, ${displayName}.`}
          description="This dashboard turns the template into an execution path so you always know the next highest-leverage action."
          actions={(
            <>
              {nextChecklistStep ? (
                <button type="button" className="button button-primary" onClick={() => onNavigate(nextChecklistStep.route)}>
                  Continue: {nextChecklistStep.label}
                </button>
              ) : (
                <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
                  Open Offers
                </button>
              )}
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/products')}>
                Offers
              </button>
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/pricing')}>
                Pricing
              </button>
              {BILLING_PORTAL_URL ? (
                <a className="button button-secondary" href={BILLING_PORTAL_URL} target="_blank" rel="noreferrer">
                  Manage Billing
                </a>
              ) : (
                <SubscriptionDetailsButton>
                  <button type="button" className="button button-secondary">Manage Billing</button>
                </SubscriptionDetailsButton>
              )}
            </>
          )}
        />
        <LivingTutorial
          whatThisDoes="Transforms setup into a strict launch checklist that reads real state from your APIs."
          howToTest={[
            'Complete checklist steps in order',
            'Refresh this page and confirm progress persists',
            'Verify focused nav expands only after full checklist completion'
          ]}
          expectedResult="Users get one clear next action until the first paid loop is fully validated."
        />
        <article className="launch-checklist-shell">
          <div className="section-head-inline">
            <h2>Launch checklist</h2>
            <p className="checklist-progress">{completedChecklistCount}/{launchChecklist.length} complete</p>
          </div>
          <p className="helper-text">
            {checklistComplete
              ? 'Checklist complete. Navigation is now fully unlocked.'
              : 'Navigation stays focused until this checklist is complete so setup does not sprawl.'}
          </p>
          <div className="launch-checklist-grid">
            {launchChecklist.map((step, index) => (
              <article className={`checklist-item ${step.done ? 'checklist-item-done' : ''}`} key={step.key}>
                <div className="surface-head">
                  <div className="checklist-index">{index + 1}</div>
                  <h3 className="surface-title">{step.label}</h3>
                  <span className={`pill ${step.done ? 'pill-live' : 'pill-paused'}`}>{step.done ? 'done' : 'next'}</span>
                </div>
                <p className="surface-copy">{step.hint}</p>
                <button type="button" className="button button-secondary" onClick={() => onNavigate(step.route)}>
                  {step.done ? 'Review' : 'Do this now'}
                </button>
              </article>
            ))}
          </div>
        </article>
        <div className="cards-grid cards-grid-3">
          <MetricCard label="Plan" value={planTier.toUpperCase()} note={`${enabledFeatures.length} features enabled`} />
          <MetricCard label="Published Offers" value={String(publishedProducts)} note={`${pricedProducts} with active price`} />
          <MetricCard label="Paid Orders" value={String(paidOrders)} note={`${orders.length} total purchases`} />
          <MetricCard label="Active Subs" value={String(activeSubscriptions.length)} note={`${subscriptions.length} total subscriptions`} />
          <MetricCard label="Ready Downloads" value={String(readyDownloads)} note={`${downloads.length} total deliveries`} />
          <MetricCard label="Feature Access" value={String(currentEntitlements)} note="Current entitlements" />
          <MetricCard label="Open Requests" value={String(openServiceRequests)} note="Service bookings in progress" />
        </div>
      </section>

      {error ? <section className="screen warning-panel"><p>{error}</p></section> : null}

      <section className="screen">
        <header className="section-head">
          <h2>Recent activity</h2>
          <p className="helper-text">Quick view of purchases and downloadable assets.</p>
        </header>
        <div className="cards-grid cards-grid-2">
          <article className="surface-card stack-sm">
            <div className="section-head-inline">
              <h3 className="surface-title">Recent purchases</h3>
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/purchases')}>
                Open Purchases
              </button>
            </div>
            {loading ? <p className="helper-text">Loading purchases...</p> : null}
            {!loading && orders.length === 0 ? <p className="helper-text">No purchases yet.</p> : null}
            <div className="stack-sm">
              {orders.slice(0, 5).map((order) => (
                <article className="mini-card" key={order.public_id}>
                  <div className="surface-head">
                    <h4 className="surface-title">Order {String(order.public_id).slice(0, 8)}</h4>
                    <span className={`pill pill-${order.status}`}>{order.status}</span>
                  </div>
                  <p className="surface-copy">Total: {formatCurrencyFromCents(order.total_cents, order.currency)}</p>
                  <p className="surface-copy">{order.items?.length || 0} item(s)</p>
                </article>
              ))}
            </div>
            {!loading && orders.length === 0 ? (
              <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
                Run first checkout
              </button>
            ) : null}
          </article>

          <article className="surface-card stack-sm">
            <div className="section-head-inline">
              <h3 className="surface-title">Digital deliveries</h3>
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/downloads')}>
                Open Downloads
              </button>
            </div>
            {loading ? <p className="helper-text">Loading downloads...</p> : null}
            {!loading && downloads.length === 0 ? <p className="helper-text">No digital deliveries available yet.</p> : null}
            <div className="stack-sm">
              {downloads.slice(0, 5).map((grant) => (
                <article className="mini-card" key={grant.token}>
                  <div className="surface-head">
                    <h4 className="surface-title">{grant.asset_title}</h4>
                    <span className={`pill ${grant.can_download ? 'pill-live' : 'pill-paused'}`}>
                      {grant.can_download ? 'ready' : 'locked'}
                    </span>
                  </div>
                  <p className="surface-copy">{grant.product_name}</p>
                  <p className="surface-copy">{grant.download_count}/{grant.max_downloads} downloads used</p>
                  <button
                    type="button"
                    className="button button-primary"
                    disabled={!grant.can_download || accessingToken === grant.token}
                    onClick={() => requestAccess(grant.token)}
                  >
                    {accessingToken === grant.token ? 'Preparing...' : 'Download'}
                  </button>
                </article>
              ))}
            </div>
            {!loading && downloads.length === 0 ? (
              <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
                Buy a digital offer
              </button>
            ) : null}
          </article>
        </div>
      </section>

      <section className="screen">
        <header className="section-head">
          <h2>Subscriptions, access, and service delivery</h2>
          <p className="helper-text">Monitor recurring revenue, feature access, and booking pipeline.</p>
        </header>
        <div className="cards-grid cards-grid-2">
          <article className="surface-card stack-sm">
            <div className="section-head-inline">
              <h3 className="surface-title">Subscriptions and access</h3>
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/subscriptions')}>
                Open Subscriptions
              </button>
            </div>
            {loading ? <p className="helper-text">Loading subscriptions...</p> : null}
            {!loading && activeSubscriptions.length === 0 ? <p className="helper-text">No active subscriptions found.</p> : null}
            <div className="stack-sm">
              {activeSubscriptions.slice(0, 4).map((subscription) => (
                <article className="mini-card" key={subscription.id}>
                  <div className="surface-head">
                    <h4 className="surface-title">{subscription.product_name || 'Subscription'}</h4>
                    <span className={`pill pill-${subscription.status}`}>{subscription.status}</span>
                  </div>
                  <p className="surface-copy">
                    {subscription.price_summary
                      ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                      : 'No linked local price'}
                  </p>
                </article>
              ))}
            </div>
            <h4 className="surface-title">Current feature access</h4>
            {entitlements.filter((entitlement) => entitlement.is_current).length === 0 ? (
              <p className="helper-text">No active entitlements yet.</p>
            ) : (
              <div className="feature-list">
                {entitlements
                  .filter((entitlement) => entitlement.is_current)
                  .slice(0, 8)
                  .map((entitlement) => (
                    <span className="feature-tag" key={entitlement.id}>
                      {entitlement.feature_key}
                    </span>
                ))}
              </div>
            )}
            {!loading && activeSubscriptions.length === 0 ? (
              <button type="button" className="button button-primary" onClick={() => onNavigate('/pricing')}>
                Start a subscription test
              </button>
            ) : null}
          </article>

          <article className="surface-card stack-sm">
            <div className="section-head-inline">
              <h3 className="surface-title">Service bookings</h3>
              <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/bookings')}>
                Open Bookings
              </button>
            </div>
            {loading ? <p className="helper-text">Loading booking requests...</p> : null}
            {!loading && bookings.length === 0 ? <p className="helper-text">No booking requests yet.</p> : null}
            <div className="stack-sm">
              {bookings.slice(0, 4).map((booking) => (
                <article className="mini-card" key={booking.id}>
                  <div className="surface-head">
                    <h4 className="surface-title">{booking.product_name || 'Service booking'}</h4>
                    <span className={`pill pill-${booking.status}`}>{booking.status}</span>
                  </div>
                  <p className="surface-copy">{booking.customer_notes || 'No notes provided.'}</p>
                </article>
              ))}
            </div>
            {!loading && bookings.length === 0 ? (
              <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
                Configure service offer
              </button>
            ) : null}
          </article>
        </div>
      </section>

      <section className="screen">
        <article className="surface-card stack-sm">
          <h2 className="surface-title">Developer context</h2>
          <p className="helper-text">API base: <code>{apiBase}</code></p>
          <p className="helper-text">Data refresh: {refreshing ? 'updating now' : 'automatic on page load and downloads'}</p>
          <p className="helper-text">Use account routes for full details and auditability.</p>
          {user ? (
            <p className="helper-text">Signed in as {user.primaryEmailAddress?.emailAddress || user.username || user.id}</p>
          ) : null}
        </article>
      </section>
    </>
  );
}

function SignedOutApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const hiddenCatalogPath = pathname === '/pricing' || pathname === '/products' || pathname.startsWith('/products/');
  const normalizedPath = hiddenCatalogPath ? '/' : pathname;
  const content = hiddenCatalogPath ? (
    <>
      <section className="screen warning-panel">
        <ScreenIntro
          eyebrow="Template Preview"
          title="Catalog and pricing are disabled while signed out"
          description="This starter ships without seeded products or plans. Sign in to configure offers, then validate checkout and fulfillment from account routes."
        />
      </section>
      <MarketingHome />
    </>
  ) : (
    <MarketingHome />
  );

  return (
    <main className="shell">
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
  const [checklistComplete, setChecklistComplete] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    const cached = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
    return cached === 'true';
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(CHECKLIST_STORAGE_KEY, checklistComplete ? 'true' : 'false');
  }, [checklistComplete]);

  let content: ReactNode = <AccountDashboard onNavigate={onNavigate} onChecklistStateChange={setChecklistComplete} />;

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
      <section className="screen">
        <ScreenIntro
          eyebrow="404"
          title="Page not found"
          description="This route is not available in the current app map."
          actions={(
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/app')}>
              Back to Dashboard
            </button>
          )}
        />
      </section>
    );
  }

  return (
    <main className="shell">
      <Header
        pathname={pathname}
        onNavigate={onNavigate}
        signedIn
        expandedNav={checklistComplete}
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
