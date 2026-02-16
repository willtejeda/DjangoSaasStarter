import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { authedRequest } from '../../../lib/api';
import type { OrderRecord, TokenNavigateProps } from '../../../shared/types';
import {
  buttonPrimary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../../shared/ui-utils';

export function AccountPurchasesPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
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
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Purchases"
        description="Track order status and verify payment transitions from pending to paid or fulfilled."
      />
      <TutorialBlock
        whatThisDoes="Displays every order for the signed-in account with server-side status and totals."
        howToTest={[
          'Complete checkout from any offer',
          'Return after webhook processing',
          'Confirm status reflects paid or fulfilled',
        ]}
        expectedResult="Order state is auditable and never relies on optimistic frontend state."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading purchases...</p> : null}

      {!loading && orders.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No purchases yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Run one checkout flow and return to validate payment transition.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Browse Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {orders.map((order) => (
          <article key={order.public_id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Order {String(order.public_id).slice(0, 8)}</h3>
              <StatusPill value={order.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Total: {formatCurrencyFromCents(order.total_cents, order.currency)}
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-300">{order.items?.length || 0} item(s)</p>
          </article>
        ))}
      </div>
    </section>
  );
}
