import { SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';
import { useEffect, useState, type ReactElement } from 'react';

import type {
  AiUsageBucketRecord,
  HeaderProps,
  MetricCardProps,
  NavigateFn,
  PageIntroProps,
  TutorialBlockProps,
} from '../../shared/types';
import {
  buttonGhost,
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  statusPillClasses,
} from '../../shared/ui-utils';

export function usePathname(): { pathname: string; navigate: NavigateFn } {
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

export function StatusPill({ value }: { value: string }): ReactElement {
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

export function Header({ pathname, onNavigate, signedIn, themeLabel, onToggleTheme }: HeaderProps): ReactElement {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  const links = signedIn
    ? [
        { label: 'Dashboard', to: '/app' },
        { label: 'Offers', to: '/products' },
        { label: 'Pricing', to: '/pricing' },
        { label: 'Examples', to: '/examples' },
      ]
    : [
        { label: 'Home', to: '/' },
        { label: 'Offers', to: '/products' },
        { label: 'Pricing', to: '/pricing' },
        { label: 'Examples', to: '/examples' },
      ];

  return (
    <header className="sticky top-3 z-30 rounded-2xl border border-slate-200 bg-white/92 px-4 py-4 shadow-lg shadow-slate-900/5 backdrop-blur dark:border-slate-700 dark:bg-slate-900/88 sm:px-6">
      <div className="flex items-center justify-between gap-3">
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

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={cn(buttonGhost, 'lg:hidden')}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-primary-nav"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? 'Close' : 'Menu'}
          </button>
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

      <nav
        id="mobile-primary-nav"
        className={cn('mt-4 grid gap-2 lg:hidden', !mobileMenuOpen && 'hidden')}
        aria-label="Primary"
      >
        {links.map((link) => {
          const active = pathname === link.to;
          return (
            <a
              key={link.to}
              href={link.to}
              className={cn(
                'rounded-xl px-3 py-2 text-sm font-semibold transition',
                active
                  ? 'bg-slate-950 text-white dark:bg-cyan-400 dark:text-slate-950'
                  : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              )}
              onClick={(event) => {
                event.preventDefault();
                setMobileMenuOpen(false);
                onNavigate(link.to);
              }}
            >
              {link.label}
            </a>
          );
        })}
      </nav>
    </header>
  );
}

export function Sidebar({ pathname, onNavigate, signedIn }: { pathname: string; onNavigate: NavigateFn; signedIn: boolean }): ReactElement {
  const signedInLinks = [
    { label: 'Dashboard', to: '/app' },
    { label: 'Offers', to: '/products' },
    { label: 'Pricing', to: '/pricing' },
    { label: 'Purchases', to: '/account/purchases' },
    { label: 'Downloads', to: '/account/downloads' },
    { label: 'Subscriptions', to: '/account/subscriptions' },
    { label: 'Bookings', to: '/account/bookings' },
    { label: 'Examples', to: '/examples' },
  ];

  const publicLinks = [
    { label: 'Home', to: '/' },
    { label: 'Offers', to: '/products' },
    { label: 'Pricing', to: '/pricing' },
    { label: 'Examples', to: '/examples' },
  ];

  const links = signedIn ? signedInLinks : publicLinks;

  return (
    <aside className="h-full rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/85">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Navigation</p>
      <nav className="mt-3 grid gap-2">
        {links.map((link) => {
          const active = pathname === link.to;
          return (
            <a
              key={link.to}
              href={link.to}
              className={cn(
                'rounded-xl px-3 py-2 text-sm font-semibold transition',
                active
                  ? 'bg-slate-950 text-white dark:bg-cyan-400 dark:text-slate-950'
                  : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              )}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(link.to);
              }}
            >
              {link.label}
            </a>
          );
        })}
      </nav>
      <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-800 dark:bg-emerald-900/20">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700 dark:text-emerald-300">Mission</p>
        <p className="mt-1 text-xs leading-relaxed text-emerald-800 dark:text-emerald-200">
          Ship one paid loop first. Then optimize retention and traffic.
        </p>
      </div>
    </aside>
  );
}

export function PageIntro({ eyebrow, title, description, actions }: PageIntroProps): ReactElement {
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

export function TutorialBlock({ whatThisDoes, howToTest, expectedResult }: TutorialBlockProps): ReactElement {
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

export function StatCard({ label, value, note }: { label: string; value: string; note: string }): ReactElement {
  return (
    <article className={cardClass}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{label}</p>
      <h3 className="mt-2 text-2xl font-black tracking-tight text-slate-900 dark:text-white">{value}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{note}</p>
    </article>
  );
}

export function MetricCard({ label, value, note }: MetricCardProps): ReactElement {
  return (
    <article className={cardClass}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{label}</p>
      <h3 className="mt-2 text-2xl font-black tracking-tight text-slate-900 dark:text-white">{value}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{note}</p>
    </article>
  );
}

export function UsageBar({ bucket }: { bucket: AiUsageBucketRecord }): ReactElement {
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
