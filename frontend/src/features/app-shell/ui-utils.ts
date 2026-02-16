import type { PlanTier } from './types';

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

const buttonBase =
  'inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60';

export const buttonPrimary =
  `${buttonBase} bg-slate-950 text-white shadow-sm hover:bg-slate-800 dark:bg-cyan-400 dark:text-slate-950 dark:hover:bg-cyan-300`;
export const buttonSecondary =
  `${buttonBase} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800`;
export const buttonGhost =
  `${buttonBase} border border-transparent bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800`;
export const sectionClass =
  'rounded-3xl border border-slate-200 bg-white/90 p-7 shadow-xl shadow-slate-900/5 backdrop-blur dark:border-slate-700 dark:bg-slate-900/80 sm:p-8 lg:p-10';
export const cardClass =
  'rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900';

export function formatCurrencyFromCents(cents: number, currency = 'USD'): string {
  const numeric = Number(cents || 0) / 100;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(numeric);
}

export function inferPlanFromFeatures(features: ReadonlyArray<string | null | undefined> | null | undefined): PlanTier {
  const normalized = new Set((features || []).map((item) => String(item).toLowerCase()));
  if (normalized.has('enterprise')) {
    return 'enterprise';
  }
  if (normalized.has('pro') || normalized.has('premium') || normalized.has('growth')) {
    return 'pro';
  }
  return 'free';
}

export function isPlanTier(value: string | null | undefined): value is PlanTier {
  return value === 'free' || value === 'pro' || value === 'enterprise';
}

export function statusPillClasses(status: string): string {
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
