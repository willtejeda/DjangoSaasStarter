import { SignedIn } from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useEffect, useRef, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { useToast } from '../../../components/feedback/toast';
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

const AUTO_SYNC_REASON_CODES = new Set(['no_subscription_payload', 'no_active_subscription', 'synced_with_partial_errors']);

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
  const notify = useToast();
  const autoSyncAttemptedRef = useRef(false);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [billingSync, setBillingSync] = useState<BillingSyncStatus>(DEFAULT_BILLING_SYNC);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');

  const syncFromClerk = async (): Promise<void> => {
    setSyncing(true);
    setError('');
    try {
      const refreshedBillingSync = await authedRequest<BillingSyncStatus>(getToken, '/account/subscriptions/status/?refresh=1');
      const refreshedSubscriptions = await authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/');
      const normalizedSubscriptions = Array.isArray(refreshedSubscriptions) ? refreshedSubscriptions : [];
      setBillingSync(refreshedBillingSync || DEFAULT_BILLING_SYNC);
      setSubscriptions(normalizedSubscriptions);
      notify({
        title: normalizedSubscriptions.length ? 'Subscription sync updated' : 'No subscriptions found in Clerk',
        detail: normalizedSubscriptions.length
          ? 'Local records now match the latest billing sync.'
          : 'No recurring subscription payload is currently available for this account.',
        variant: 'info',
      });
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not sync subscriptions.';
      setError(detail);
      notify({
        title: 'Subscription sync failed',
        detail,
        variant: 'error',
      });
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    let active = true;
    const loadSubscriptions = async (): Promise<void> => {
      try {
        const subscriptionsPayload = await authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/');
        const normalizedSubscriptions = Array.isArray(subscriptionsPayload) ? subscriptionsPayload : [];
        if (!active) {
          return;
        }
        setSubscriptions(normalizedSubscriptions);

        let billingSyncPayload =
          (await authedRequest<BillingSyncStatus>(getToken, '/account/subscriptions/status/').catch(
            () => DEFAULT_BILLING_SYNC
          )) || DEFAULT_BILLING_SYNC;

        const shouldAutoSync =
          !autoSyncAttemptedRef.current
          && normalizedSubscriptions.length === 0
          && !billingSyncPayload.blocking
          && AUTO_SYNC_REASON_CODES.has(String(billingSyncPayload.reason_code || '').trim().toLowerCase());

        if (shouldAutoSync) {
          autoSyncAttemptedRef.current = true;
          billingSyncPayload =
            (await authedRequest<BillingSyncStatus>(getToken, '/account/subscriptions/status/?refresh=1').catch(
              () => billingSyncPayload
            )) || billingSyncPayload;
          const refreshedSubscriptions = await authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/').catch(
            () => normalizedSubscriptions
          );
          if (!active) {
            return;
          }
          setSubscriptions(Array.isArray(refreshedSubscriptions) ? refreshedSubscriptions : []);
        }
        if (!active) {
          return;
        }
        setBillingSync(billingSyncPayload);
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
          <div className="flex flex-col items-end gap-2">
            <StatusPill value={billingSync.state} />
            <button
              type="button"
              className={cn(buttonSecondary, 'h-8 px-3 py-1 text-xs')}
              onClick={() => {
                void syncFromClerk();
              }}
              disabled={syncing || loading}
            >
              {syncing ? 'Syncing...' : 'Sync from Clerk'}
            </button>
          </div>
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
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No subscription records synced yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            This view renders local records. If Clerk shows an active plan, run sync now to pull the latest state.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className={buttonSecondary}
              onClick={() => {
                void syncFromClerk();
              }}
              disabled={syncing}
            >
              {syncing ? 'Syncing...' : 'Sync from Clerk'}
            </button>
            <button type="button" className={buttonPrimary} onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
          </div>
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
