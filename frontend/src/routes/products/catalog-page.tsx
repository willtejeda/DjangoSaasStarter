import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../components/layout/app-shell';
import { useToast } from '../../components/feedback/toast';
import { apiRequest, authedRequest } from '../../lib/api';
import type { Id, OrderCreateResponse, ProductCatalogProps, ProductRecord } from '../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../shared/ui-utils';

type ProductTypeValue = 'digital' | 'service';
type BillingPeriodValue = 'one_time' | 'monthly' | 'yearly';

interface OfferDraftState {
  name: string;
  tagline: string;
  description: string;
  featureKeys: string;
  productType: ProductTypeValue;
  priceName: string;
  amount: string;
  currency: string;
  billingPeriod: BillingPeriodValue;
  checkoutUrl: string;
  clerkPlanId: string;
  clerkPriceId: string;
}

const INITIAL_DRAFT: OfferDraftState = {
  name: 'Starter Offer',
  tagline: 'Fast validation offer',
  description: '',
  featureKeys: '',
  productType: 'digital',
  priceName: 'Starter',
  amount: '29',
  currency: 'USD',
  billingPeriod: 'one_time',
  checkoutUrl: '',
  clerkPlanId: '',
  clerkPriceId: '',
};

function parseAmountToCents(value: string): number | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return null;
  }
  return Math.round(numeric * 100);
}

function normalizeFeatureKeys(raw: string): string[] {
  const seen = new Set<string>();
  return raw
    .split(',')
    .map((item) => item.trim().toLowerCase().replace(/\s+/g, '_'))
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
}

function actionKey(productId: Id, priceId: Id): string {
  return `${String(productId)}:${String(priceId)}`;
}

export function ProductCatalogPage({ onNavigate, getToken }: ProductCatalogProps): ReactElement {
  const notify = useToast();
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [draft, setDraft] = useState<OfferDraftState>(INITIAL_DRAFT);
  const [buyingFor, setBuyingFor] = useState('');

  const loadCatalog = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError('');
    try {
      const payload = await apiRequest<ProductRecord[]>('/products/');
      setProducts(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not load catalog.';
      setError(detail);
      notify({ title: 'Catalog request failed', detail, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  const handleDraftChange = (field: keyof OfferDraftState) => (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ): void => {
    setDraft((previous) => ({ ...previous, [field]: event.target.value }));
  };

  const handleCreateOffer = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setCreating(true);
    setCreateError('');
    setCreateSuccess('');

    const name = draft.name.trim();
    const amountCents = parseAmountToCents(draft.amount.trim());
    const currency = draft.currency.trim().toUpperCase();
    const checkoutUrl = draft.checkoutUrl.trim();

    if (!name) {
      setCreateError('Offer name is required.');
      setCreating(false);
      return;
    }
    if (amountCents === null) {
      setCreateError('Price amount must be greater than zero.');
      setCreating(false);
      return;
    }
    if (currency.length !== 3) {
      setCreateError('Currency must be a 3-letter code like USD.');
      setCreating(false);
      return;
    }

    let createdProductId: Id | null = null;

    try {
      const product = await authedRequest<{ id: Id; name: string }>(getToken, '/seller/products/', {
        method: 'POST',
        body: {
          name,
          tagline: draft.tagline.trim(),
          description: draft.description.trim(),
          product_type: draft.productType,
          visibility: 'published',
          feature_keys: normalizeFeatureKeys(draft.featureKeys),
        },
      });
      createdProductId = product.id;

      await authedRequest<{ id: Id }>(getToken, `/seller/products/${product.id}/prices/`, {
        method: 'POST',
        body: {
          name: draft.priceName.trim(),
          amount_cents: amountCents,
          currency,
          billing_period: draft.billingPeriod,
          clerk_plan_id: draft.clerkPlanId.trim(),
          clerk_price_id: draft.clerkPriceId.trim(),
          is_active: true,
          is_default: true,
          metadata: checkoutUrl ? { checkout_url: checkoutUrl } : {},
        },
      });

      if (draft.productType === 'service') {
        await authedRequest(getToken, `/seller/products/${product.id}/service-offer/`, {
          method: 'PUT',
          body: {
            session_minutes: 60,
            delivery_days: 7,
            revision_count: 1,
            onboarding_instructions: 'Share project goals and current blockers before the session.',
          },
        });
      }

      setCreateSuccess(`Created "${product.name}" and attached a buyable price.`);
      notify({
        title: 'Offer created',
        detail: 'Product and price saved in Django. You can buy it below now.',
        variant: 'success',
      });
      setDraft((previous) => ({
        ...INITIAL_DRAFT,
        currency: previous.currency,
        billingPeriod: previous.billingPeriod,
        amount: previous.amount,
      }));
      await loadCatalog();
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not create offer.';
      const postCreateNote =
        createdProductId !== null
          ? ` Product was created (id ${String(createdProductId)}), but price or Clerk mapping failed.`
          : '';
      setCreateError(`${detail}${postCreateNote}`);
      notify({
        title: 'Offer creation failed',
        detail: `${detail}${postCreateNote}`,
        variant: 'error',
      });
    } finally {
      setCreating(false);
    }
  };

  const handleQuickBuy = async (product: ProductRecord): Promise<void> => {
    const activePriceId = product.active_price?.id;
    if (!activePriceId) {
      notify({
        title: 'No active price found',
        detail: 'Attach an active default price before running a purchase test.',
        variant: 'error',
      });
      return;
    }

    const key = actionKey(product.id, activePriceId);
    setBuyingFor(key);

    try {
      const orderResponse = await authedRequest<OrderCreateResponse, { price_id: Id; quantity: number }>(
        getToken,
        '/account/orders/create/',
        {
          method: 'POST',
          body: { price_id: activePriceId, quantity: 1 },
        }
      );
      const checkoutUrl = orderResponse?.checkout?.checkout_url || '';
      const publicId = orderResponse?.order?.public_id;

      if (!publicId) {
        throw new Error('Order was created without a valid public id.');
      }

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
        return;
      }

      notify({
        title: 'Pending order created',
        detail: 'Checkout URL is missing. Open Purchases to verify the pending order record.',
        variant: 'info',
      });
      onNavigate('/account/purchases');
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not create purchase test.';
      notify({ title: 'Purchase test failed', detail, variant: 'error' });
    } finally {
      setBuyingFor('');
    }
  };

  const fieldClass =
    'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-200 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-cyan-800';

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Offers"
        title="Buyable offers with production checkout paths"
        description="Publish digital or service products, attach prices, and route buyers into secure order creation."
      />
      <TutorialBlock
        whatThisDoes="Creates offers through Django seller APIs with optional Clerk mapping, then runs purchase tests directly from catalog cards."
        howToTest={[
          'Create one offer and one active price in the form below',
          'Click Buy Test on that new offer',
          'Open Purchases and verify pending, paid, or fulfilled state',
        ]}
        expectedResult="Offer creation and purchase testing happen from one screen with server-side order records."
      />

      <article className={cardClass}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Create Offer Fast</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Saves product and price in Django ORM. Optional Clerk plan, price, and checkout URL fields keep billing mapping explicit.
            </p>
          </div>
          <StatusPill value="seller" />
        </div>

        <form className="mt-4 space-y-4" onSubmit={(event) => void handleCreateOffer(event)}>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Offer name
              <input className={fieldClass} type="text" value={draft.name} onChange={handleDraftChange('name')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Product type
              <select className={fieldClass} value={draft.productType} onChange={handleDraftChange('productType')}>
                <option value="digital">Digital</option>
                <option value="service">Service</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Tagline
              <input className={fieldClass} type="text" value={draft.tagline} onChange={handleDraftChange('tagline')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Price name
              <input className={fieldClass} type="text" value={draft.priceName} onChange={handleDraftChange('priceName')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Amount
              <input className={fieldClass} type="number" min="1" step="0.01" value={draft.amount} onChange={handleDraftChange('amount')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Billing period
              <select className={fieldClass} value={draft.billingPeriod} onChange={handleDraftChange('billingPeriod')}>
                <option value="one_time">One time</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Currency
              <input className={fieldClass} type="text" maxLength={3} value={draft.currency} onChange={handleDraftChange('currency')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Clerk plan id
              <input className={fieldClass} type="text" value={draft.clerkPlanId} onChange={handleDraftChange('clerkPlanId')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
              Clerk price id
              <input className={fieldClass} type="text" value={draft.clerkPriceId} onChange={handleDraftChange('clerkPriceId')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200 md:col-span-2">
              Clerk checkout URL
              <input className={fieldClass} type="url" value={draft.checkoutUrl} onChange={handleDraftChange('checkoutUrl')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200 md:col-span-2">
              Feature keys (comma separated)
              <input className={fieldClass} type="text" value={draft.featureKeys} onChange={handleDraftChange('featureKeys')} />
            </label>
            <label className="grid gap-1 text-sm font-semibold text-slate-700 dark:text-slate-200 md:col-span-2">
              Description
              <textarea
                className={fieldClass}
                rows={3}
                value={draft.description}
                onChange={handleDraftChange('description')}
              />
            </label>
          </div>

          {createError ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{createError}</p> : null}
          {createSuccess ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{createSuccess}</p> : null}

          <div className="flex flex-wrap gap-2">
            <button type="submit" className={buttonPrimary} disabled={creating}>
              {creating ? 'Creating offer...' : 'Create Offer'}
            </button>
            <button
              type="button"
              className={buttonSecondary}
              disabled={creating}
              onClick={() => {
                setDraft(INITIAL_DRAFT);
                setCreateError('');
                setCreateSuccess('');
              }}
            >
              Reset
            </button>
          </div>
        </form>
      </article>

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading catalog...</p> : null}

      {!loading && products.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No published products yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Use the form above to create one product and one active price, then run a purchase test.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
              Open Pricing
            </button>
            <button type="button" className={buttonPrimary} onClick={() => onNavigate('/app')}>
              Open Preflight Dashboard
            </button>
          </div>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        {products.map((product) => (
          <article key={product.id} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <StatusPill value={product.product_type} />
              <p className="text-sm font-semibold text-slate-900 dark:text-white">
                {product.active_price
                  ? formatCurrencyFromCents(product.active_price.amount_cents, product.active_price.currency)
                  : 'Unpriced'}
              </p>
            </div>
            <h3 className="mt-3 text-xl font-bold tracking-tight text-slate-900 dark:text-white">{product.name}</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {product.tagline || product.description || 'No description yet.'}
            </p>
            <div className="mt-4 grid gap-2">
              <button
                type="button"
                className={cn(buttonPrimary, 'w-full')}
                disabled={!product.active_price?.id || Boolean(buyingFor)}
                onClick={() => void handleQuickBuy(product)}
              >
                {buyingFor === actionKey(product.id, product.active_price?.id || '') ? 'Processing...' : 'Buy Test'}
              </button>
              <button
                type="button"
                className={cn(buttonSecondary, 'w-full')}
                onClick={() => onNavigate(`/products/${product.slug}`)}
              >
                View Offer
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
