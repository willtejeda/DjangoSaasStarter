import type { ReactElement } from 'react';

import { buttonSecondary, cardClass, cn } from '../../shared/ui-utils';

interface FrontendBackendExamplesProps {
  onNavigate: (nextPath: string) => void;
}

interface ScenarioExample {
  id: string;
  stage: string;
  title: string;
  route: string;
  note: string;
  language: 'ts' | 'tsx';
  code: string;
}

const examples: ScenarioExample[] = [
  {
    id: 'public_catalog',
    stage: 'Discovery',
    title: 'Read public offer catalog',
    route: '/products',
    note: 'Render all published digital or service offers with server-driven prices.',
    language: 'ts',
    code: `import { apiRequest } from '../lib/api';

const catalog = await apiRequest<Array<{
  id: number;
  slug: string;
  name: string;
  product_type: 'digital' | 'service';
  active_price?: { id: number; amount_cents: number; currency: string } | null;
}>>('/products/');`,
  },
  {
    id: 'seller_create_offer',
    stage: 'Setup',
    title: 'Create product + price from frontend',
    route: '/products',
    note: 'Use seller APIs to publish buyable offers directly from the app UI.',
    language: 'ts',
    code: `const product = await authedRequest<{ id: number }>(getToken, '/seller/products/', {
  method: 'POST',
  body: {
    name: 'Retouch Package',
    product_type: 'service',
    visibility: 'published',
    feature_keys: ['priority_support'],
  },
});

await authedRequest(getToken, \`/seller/products/\${product.id}/prices/\`, {
  method: 'POST',
  body: { name: 'One-time', amount_cents: 7900, currency: 'USD', billing_period: 'one_time', is_active: true, is_default: true },
});`,
  },
  {
    id: 'order_create',
    stage: 'Checkout',
    title: 'Create pending order before payment',
    route: '/products',
    note: 'Always create server-side order state first, then redirect to checkout URL if present.',
    language: 'ts',
    code: `const created = await authedRequest<{
  order: { public_id: string };
  checkout?: { checkout_url?: string | null };
}>(getToken, '/account/orders/create/', {
  method: 'POST',
  body: { price_id: 12, quantity: 1 },
});

if (created.checkout?.checkout_url) {
  window.location.href = created.checkout.checkout_url;
}`,
  },
  {
    id: 'purchases',
    stage: 'Post-purchase',
    title: 'Read purchases history',
    route: '/account/purchases',
    note: 'Show auditable order status transitions from pending to paid and fulfilled.',
    language: 'ts',
    code: `const orders = await authedRequest<Array<{
  public_id: string;
  status: string;
  total_cents: number;
  currency: string;
}>>(getToken, '/account/orders/');`,
  },
  {
    id: 'checkout_state',
    stage: 'Post-checkout',
    title: 'Handle checkout success and cancel pages',
    route: '/checkout/success',
    note: 'Use checkout state routes as explicit user feedback after payment redirects.',
    language: 'tsx',
    code: `if (pathname === '/checkout/success') {
  return <CheckoutStatePage state="success" onNavigate={onNavigate} />;
}
if (pathname === '/checkout/cancel') {
  return <CheckoutStatePage state="cancel" onNavigate={onNavigate} />;
}`,
  },
  {
    id: 'downloads',
    stage: 'Fulfillment',
    title: 'List downloads and request signed URL access',
    route: '/account/downloads',
    note: 'Supports ready and locked downloadable objects with secure access endpoint.',
    language: 'ts',
    code: `const grants = await authedRequest<Array<{ token: string; asset_title: string; can_download: boolean }>>(
  getToken,
  '/account/downloads/'
);

const access = await authedRequest<{ download_url?: string | null }>(
  getToken,
  \`/account/downloads/\${grants[0].token}/access/\`,
  { method: 'POST' }
);`,
  },
  {
    id: 'subscriptions',
    stage: 'Retention',
    title: 'Read subscription state',
    route: '/account/subscriptions',
    note: 'Subscription rows are synced from checkout plus webhook history backfill.',
    language: 'ts',
    code: `const subscriptions = await authedRequest<Array<{
  id: number;
  product_name?: string | null;
  status: string;
  price_summary?: { amount_cents: number; currency: string; billing_period: string } | null;
}>>(getToken, '/account/subscriptions/');`,
  },
  {
    id: 'work_orders',
    stage: 'Fulfillment',
    title: 'Track service work orders',
    route: '/account/orders/work',
    note: 'Personalized purchases map to fulfillment work orders, with delivery-mode specific metadata.',
    language: 'ts',
    code: `const workOrders = await authedRequest<Array<{
  id: number;
  product_name?: string | null;
  status: string;
  delivery_mode: 'downloadable' | 'physical_shipped';
  download_ready?: boolean;
}>>(getToken, '/account/orders/work/');`,
  },
  {
    id: 'preflight',
    stage: 'Operations',
    title: 'Run preflight checks from dashboard',
    route: '/app',
    note: 'Validate account sync, Supabase probe, and transactional email delivery before feature work.',
    language: 'ts',
    code: `const me = await authedRequest(getToken, '/me/');
const supabaseProbe = await authedRequest(getToken, '/supabase/profile/');
const emailTest = await authedRequest(
  getToken,
  '/account/preflight/email-test/',
  { method: 'POST' }
);`,
  },
  {
    id: 'ai_usage',
    stage: 'Retention',
    title: 'Read AI provider and usage scaffolding',
    route: '/app',
    note: 'Use provider readiness, enforced usage buckets, and simulator endpoints to gate subscription AI features.',
    language: 'ts',
    code: `const [providers, usage] = await Promise.all([
  authedRequest(getToken, '/ai/providers/'),
  authedRequest(getToken, '/ai/usage/summary/'),
]);

const estimate = await authedRequest(getToken, '/ai/tokens/estimate/', {
  method: 'POST',
  body: { messages: [{ role: 'user', content: 'Draft an onboarding email.' }] },
});

const debugRun = await authedRequest(getToken, '/ai/chat/complete/', {
  method: 'POST',
  body: { provider: 'simulator', messages: [{ role: 'user', content: 'Run quota test.' }] },
});`,
  },
  {
    id: 'pricing',
    stage: 'Checkout',
    title: 'Render pricing from Clerk',
    route: '/pricing',
    note: 'Frontend pricing can stay declarative while plan data remains source-of-truth in Clerk Billing.',
    language: 'tsx',
    code: `import { PricingTable } from '@clerk/clerk-react';

export function PricingSurface() {
  return <PricingTable />;
}`,
  },
];

export function FrontendBackendExamples({ onNavigate }: FrontendBackendExamplesProps): ReactElement {
  const routeShortcuts = Array.from(new Set(examples.map((example) => example.route)));

  return (
    <section className="space-y-4">
      <header className={cn(cardClass, 'space-y-3')}>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-700 dark:text-cyan-300">Scenario coverage</p>
        <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-white">Examples for all shipped flows</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          These snippets map to every core scenario currently offered in the app.
        </p>
        <div className="flex flex-wrap gap-2">
          {routeShortcuts.map((route) => (
            <button
              key={route}
              type="button"
              className={cn(buttonSecondary, 'px-3 py-1.5 text-xs')}
              onClick={() => onNavigate(route)}
            >
              {route}
            </button>
          ))}
        </div>
      </header>

      {examples.map((example) => (
        <article key={example.id} className={cardClass}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-700 dark:text-cyan-300">{example.stage}</p>
              <h3 className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white">{example.title}</h3>
            </div>
            <button type="button" className={buttonSecondary} onClick={() => onNavigate(example.route)}>
              Open {example.route}
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{example.note}</p>
          <pre className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-xs leading-relaxed text-slate-100 dark:border-slate-700">
            <code className={`language-${example.language}`}>{example.code}</code>
          </pre>
        </article>
      ))}
    </section>
  );
}
