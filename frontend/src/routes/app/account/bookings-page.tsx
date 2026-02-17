import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { authedRequest } from '../../../lib/api';
import type { TokenNavigateProps, WorkOrderRecord } from '../../../shared/types';
import { buttonPrimary, cardClass, cn, sectionClass } from '../../../shared/ui-utils';

export function AccountWorkOrdersPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [orders, setOrders] = useState<WorkOrderRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest<WorkOrderRecord[]>(getToken, '/account/orders/work/')
      .then((payload) => {
        if (!active) {
          return;
        }
        setOrders(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load work orders.');
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
        title="Work Orders"
        description="Track personalized fulfillment orders and delivery status."
      />
      <TutorialBlock
        whatThisDoes="Tracks order-backed fulfillment requests created after paid service purchases."
        howToTest={[
          'Purchase a personalized service product',
          'Open this page and confirm a work order appears',
          'For downloadable work, confirm matching locked entry appears in Downloads',
        ]}
        expectedResult="Each personalized purchase creates a fulfillment order with delivery-mode visibility."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading work orders...</p> : null}

      {!loading && orders.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No fulfillment orders yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Personalized service orders appear here after payment is confirmed.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Open Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {orders.map((order) => (
          <article key={order.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{order.product_name || 'Custom order'}</h3>
              <StatusPill value={order.status} />
            </div>
            <p className="mt-2 text-sm capitalize text-slate-600 dark:text-slate-300">
              Delivery: {String(order.delivery_mode || 'downloadable').replace('_', ' ')}
            </p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {order.customer_request || 'No request notes provided.'}
            </p>
            {order.shipping_tracking_number ? (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Tracking: {order.shipping_carrier || 'Carrier'} {order.shipping_tracking_number}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export const AccountBookingsPage = AccountWorkOrdersPage;
