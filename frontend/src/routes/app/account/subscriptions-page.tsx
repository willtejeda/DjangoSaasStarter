import { SignedIn } from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { authedRequest } from '../../../lib/api';
import type { BillingSyncStatus, SubscriptionRecord, TokenNavigateProps } from '../../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../../shared/ui-utils';

const DEFAULT_BILLING_SYNC: BillingSyncStatus = {
  state: 'hard_stale',
  blocking: true,
  reason_code: 'unknown',
  error_code: null,
  detail: 'Billing sync status unavailable.',
  last_attempt_at: null,
  last_success_at: null,
  age_seconds: null,
  soft_window_seconds: 900,
  hard_ttl_seconds: 10800,
};

function formatSyncTime(value?: string | null): string {
  const raw = String(value || '').trim();
  if (!raw) {
    return 'Never';
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return 'Unknown';
  }
  return parsed.toLocaleString();
}

export function AccountSubscriptionsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [billingSync, setBillingSync] = useState<BillingSyncStatus>(DEFAULT_BILLING_SYNC);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const loadSubscriptions = async (): Promise<void> => {
      try {
        const subscriptionsPayload = await authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/');
        if (!active) {
          return;
        }
        setSubscriptions(Array.isArray(subscriptionsPayload) ? subscriptionsPayload : []);

        const billingSyncPayload = await authedRequest<BillingSyncStatus>(getToken, '/account/subscriptions/status/').catch(
          () => DEFAULT_BILLING_SYNC
        );
        if (!active) {
          return;
        }
        setBillingSync(billingSyncPayload || DEFAULT_BILLING_SYNC);
      } catch (requestError) {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load subscriptions.');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadSubscriptions();

    return () => {
      active = false;
    };
  }, [getToken]);

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

      <article
        className={cn(
          cardClass,
          billingSync.blocking
            ? 'border-rose-300 bg-rose-50/60 dark:border-rose-800 dark:bg-rose-900/20'
            : billingSync.state === 'soft_stale'
              ? 'border-amber-300 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-900/20'
              : ''
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Billing sync status</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{billingSync.detail}</p>
          </div>
          <StatusPill value={billingSync.state} />
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          Last synced: {formatSyncTime(billingSync.last_success_at)} | reason: {billingSync.reason_code}
          {billingSync.error_code ? ` | error: ${billingSync.error_code}` : ''}
        </p>
      </article>

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
