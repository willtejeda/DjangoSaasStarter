import {
  SignInButton,
  SignUpButton,
} from '@clerk/clerk-react';
import type { ReactElement } from 'react';

import { PageIntro, StatCard } from '../../components/layout/app-shell';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  sectionClass,
} from '../../shared/ui-utils';

export function LandingPage(): ReactElement {
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
