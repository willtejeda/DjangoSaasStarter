import { SignedIn } from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { authedRequest } from '../../../lib/api';
import type { SubscriptionRecord, TokenNavigateProps } from '../../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../../shared/ui-utils';

export function AccountSubscriptionsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
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
