import {
  PricingTable,
  SignInButton,
  SignUpButton,
} from '@clerk/clerk-react';
import { useEffect, useState, type ReactElement } from 'react';

import type {
  CheckoutStateProps,
  Id,
  OrderCreateResponse,
  PricingPageProps,
  ProductCatalogProps,
  ProductDetailProps,
  ProductRecord,
} from '../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../shared/ui-utils';
import { PageIntro, StatusPill, StatCard, TutorialBlock } from '../../components/layout/app-shell';
import { apiRequest, authedRequest } from '../../lib/api';
import { useToast } from '../../components/feedback/toast';

const ENABLE_DEV_MANUAL_CHECKOUT =
  (import.meta.env.VITE_ENABLE_DEV_MANUAL_CHECKOUT || '').trim().toLowerCase() === 'true';

export function MarketingHome(): ReactElement {
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
            <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">Starter revenue pulse</p>
              <div className="space-y-2">
                {[
                  { label: 'Week 1', value: 18 },
                  { label: 'Week 2', value: 36 },
                  { label: 'Week 3', value: 57 },
                  { label: 'Week 4', value: 72 },
                ].map((item) => (
                  <div key={item.label} className="grid grid-cols-[72px,1fr,42px] items-center gap-2">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{item.label}</p>
                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                    <p className="text-right text-xs font-semibold text-slate-600 dark:text-slate-300">{item.value}%</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300">
                Use this as a reminder to optimize offer clarity before adding feature complexity.
              </p>
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

export function PricingPage({ signedIn }: PricingPageProps): ReactElement {
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

export function ProductCatalog({ onNavigate }: ProductCatalogProps): ReactElement {
  const notify = useToast();
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
        const detail = requestError instanceof Error ? requestError.message : 'Could not load catalog.';
        setError(detail);
        notify({ title: 'Catalog request failed', detail, variant: 'error' });
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

export function ProductDetail({ slug, signedIn, onNavigate, getToken }: ProductDetailProps): ReactElement {
  const notify = useToast();
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
      notify({
        title: 'Manual checkout confirmed',
        detail: 'Order marked paid for local development mode.',
        variant: 'success',
      });
      onNavigate('/checkout/success');
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not complete purchase flow.';
      setError(detail);
      notify({ title: 'Checkout action failed', detail, variant: 'error' });
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

export function CheckoutState({ state, onNavigate }: CheckoutStateProps): ReactElement {
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
