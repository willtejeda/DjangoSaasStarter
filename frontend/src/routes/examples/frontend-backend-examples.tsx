import type { ReactElement } from 'react';

const examples = [
  {
    title: 'Read pricing and offers',
    note: 'Use public catalog to render marketing cards and CTA routes.',
    language: 'ts',
    code: `import { apiRequest } from '../lib/api';

const catalog = await apiRequest<Array<{
  id: number;
  slug: string;
  name: string;
  active_price?: { amount_cents: number; currency: string } | null;
}>>('/products/');`,
  },
  {
    title: 'Create pending order before checkout',
    note: 'Payment state starts server-side and only transitions after verification.',
    language: 'ts',
    code: `import { authedRequest } from '../lib/api';
import { useAuth } from '@clerk/clerk-react';

const { getToken } = useAuth();

const created = await authedRequest<{
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
    title: 'Read usage buckets for AI subscriptions',
    note: 'Use this for token, image, and video monthly limits.',
    language: 'ts',
    code: `const usage = await authedRequest<{
  plan_tier: string;
  buckets: Array<{ key: string; used: number; limit: number | null; near_limit: boolean }>;
}>(getToken, '/ai/usage/summary/');

const nearLimit = usage.buckets.filter((bucket) => bucket.near_limit);`,
  },
];

export function FrontendBackendExamples(): ReactElement {
  return (
    <section className="space-y-4">
      {examples.map((example) => (
        <article key={example.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">{example.title}</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{example.note}</p>
          <pre className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-xs leading-relaxed text-slate-100 dark:border-slate-700">
            <code className={`language-${example.language}`}>{example.code}</code>
          </pre>
        </article>
      ))}
    </section>
  );
}
