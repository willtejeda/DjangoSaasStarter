import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { authedRequest } from '../../../lib/api';
import type { BookingRecord, TokenNavigateProps } from '../../../shared/types';
import { buttonPrimary, cardClass, cn, sectionClass } from '../../../shared/ui-utils';

export function AccountBookingsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const [bookings, setBookings] = useState<BookingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest<BookingRecord[]>(getToken, '/account/bookings/')
      .then((payload) => {
        if (!active) {
          return;
        }
        setBookings(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load bookings.');
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
        title="Bookings"
        description="Review service delivery requests and customer notes."
      />
      <TutorialBlock
        whatThisDoes="Tracks service bookings created by fulfilled service purchases."
        howToTest={[
          'Create and publish a service offer',
          'Purchase service and wait for fulfillment',
          'Confirm booking appears with status and notes',
        ]}
        expectedResult="Paid service orders create operational booking records you can manage."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading bookings...</p> : null}

      {!loading && bookings.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No service bookings yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Service bookings appear after paid fulfillment.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Open Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {bookings.map((booking) => (
          <article key={booking.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{booking.product_name || 'Service booking'}</h3>
              <StatusPill value={booking.status} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{booking.customer_notes || 'No notes provided.'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
