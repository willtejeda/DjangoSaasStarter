import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../components/layout/app-shell';
import { useToast } from '../../components/feedback/toast';
import { apiRequest, authedRequest } from '../../lib/api';
import type {
  Id,
  OrderCreateResponse,
  ProductDetailProps,
  ProductRecord,
} from '../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../shared/ui-utils';

const ENABLE_DEV_MANUAL_CHECKOUT =
  (import.meta.env.VITE_ENABLE_DEV_MANUAL_CHECKOUT || '').trim().toLowerCase() === 'true';

export function ProductDetailPage({ slug, signedIn, onNavigate, getToken }: ProductDetailProps): ReactElement {
  const notify = useToast();
  const [product, setProduct] = useState<ProductRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!slug) {
      setProduct(null);
      return;
    }

    let isActive = true;
    setLoading(true);
    setError('');

    apiRequest<ProductRecord>(`/products/${slug}/`)
      .then((payload) => {
        if (!isActive) {
          return;
        }
        setProduct(payload || null);
      })
      .catch((requestError) => {
        if (!isActive) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : 'Could not load product.');
      })
      .finally(() => {
        if (isActive) {
          setLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [slug]);

  const handleBuy = async (priceId: Id): Promise<void> => {
    if (!signedIn) {
      onNavigate('/pricing');
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const orderResponse = await authedRequest<OrderCreateResponse, { price_id: Id; quantity: number }>(
        getToken,
        '/account/orders/create/',
        {
          method: 'POST',
          body: { price_id: priceId, quantity: 1 },
        }
      );

      const checkoutUrl = orderResponse?.checkout?.checkout_url || '';
      const publicId = orderResponse?.order?.public_id;

      if (!publicId) {
        throw new Error('Order did not return a valid id.');
      }

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
        return;
      }

      if (!ENABLE_DEV_MANUAL_CHECKOUT) {
        throw new Error(
          'Checkout URL missing for this price. Configure Clerk checkout metadata or use local manual mode only in development.'
        );
      }

      await authedRequest<unknown, { provider: string; external_id: string }>(
        getToken,
        `/account/orders/${publicId}/confirm/`,
        {
          method: 'POST',
          body: {
            provider: 'manual',
            external_id: `manual_${Date.now()}`,
          },
        }
      );

      setSuccess('Purchase completed. Fulfillment has been created.');
      notify({
        title: 'Manual checkout confirmed',
        detail: 'Order marked paid for local development mode.',
        variant: 'success',
      });
      onNavigate('/checkout/success');
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not complete purchase flow.';
      setError(detail);
      notify({ title: 'Checkout action failed', detail, variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <section className={sectionClass}>
        <PageIntro eyebrow="Offer" title="Loading offer" description="Fetching product details and pricing." />
      </section>
    );
  }

  if (!product) {
    return (
      <section className={sectionClass}>
        <PageIntro eyebrow="Offer" title="Offer not found" description="This route does not match a published product." />
      </section>
    );
  }

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Offer detail"
        title={product.name}
        description={product.description || product.tagline || 'No description yet.'}
        actions={(
          <>
            <StatusPill value={product.product_type} />
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
              Back to Offers
            </button>
          </>
        )}
      />

      <TutorialBlock
        whatThisDoes="Creates pending orders server-side and routes users into checkout without trusting client payment state."
        howToTest={[
          'Confirm at least one price exists on this product',
          'Click Buy and ensure pending order is created',
          'Finish checkout and confirm fulfillment in account pages',
        ]}
        expectedResult="Order status transitions happen server-side and fulfillment appears only after payment confirmation."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {success ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{success}</p> : null}

      {!product.prices?.length ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No price attached to this offer</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Add at least one active price through seller APIs, then return to validate checkout flow.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
            <button type="button" className={buttonPrimary} onClick={() => onNavigate('/app')}>
              Back to Preflight Dashboard
            </button>
          </div>
        </article>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {(product.prices || []).map((price) => (
            <article className={cardClass} key={price.id}>
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{price.name || price.billing_period}</h3>
                <p className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                  {formatCurrencyFromCents(price.amount_cents, price.currency)}
                </p>
              </div>
              <p className="mt-1 text-sm capitalize text-slate-600 dark:text-slate-300">
                Billed {price.billing_period.replace('_', ' ')}
              </p>
              <button
                type="button"
                className={cn(buttonPrimary, 'mt-4 w-full')}
                disabled={saving}
                onClick={() => handleBuy(price.id)}
              >
                {saving ? 'Processing...' : signedIn ? 'Buy Now' : 'Sign In to Buy'}
              </button>
            </article>
          ))}
        </div>
      )}

      {product.assets?.length ? (
        <article className={cardClass}>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Included assets</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            {product.assets.map((asset) => (
              <li key={asset.id}>{asset.title}</li>
            ))}
          </ul>
        </article>
      ) : null}

      {product.service_offer ? (
        <article className={cardClass}>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Service delivery details</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            <li>Session minutes: {product.service_offer.session_minutes}</li>
            <li>Delivery days: {product.service_offer.delivery_days}</li>
            <li>Revisions: {product.service_offer.revision_count}</li>
          </ul>
        </article>
      ) : null}
    </section>
  );
}
