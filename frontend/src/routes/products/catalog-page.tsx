import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../components/layout/app-shell';
import { useToast } from '../../components/feedback/toast';
import { apiRequest } from '../../lib/api';
import type { ProductCatalogProps, ProductRecord } from '../../shared/types';
import {
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  sectionClass,
} from '../../shared/ui-utils';

export function ProductCatalogPage({ onNavigate }: ProductCatalogProps): ReactElement {
  const notify = useToast();
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isActive = true;
    setLoading(true);
    setError('');

    apiRequest<ProductRecord[]>('/products/')
      .then((payload) => {
        if (!isActive) {
          return;
        }
        setProducts(Array.isArray(payload) ? payload : []);
      })
      .catch((requestError) => {
        if (!isActive) {
          return;
        }
        const detail = requestError instanceof Error ? requestError.message : 'Could not load catalog.';
        setError(detail);
        notify({ title: 'Catalog request failed', detail, variant: 'error' });
      })
      .finally(() => {
        if (isActive) {
          setLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Offers"
        title="Buyable offers with production checkout paths"
        description="Publish digital or service products, attach prices, and route buyers into secure order creation."
      />
      <TutorialBlock
        whatThisDoes="Shows published catalog entries and current active prices from backend APIs."
        howToTest={[
          'Create a product and active price in seller APIs',
          'Refresh and open the product detail page',
          'Start checkout to create a pending order',
        ]}
        expectedResult="Catalog cards always reflect backend data and payment flow stays server-led."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading catalog...</p> : null}

      {!loading && products.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No published products yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Create one product and one active price, then return to validate conversion flow.
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
            <button
              type="button"
              className={cn(buttonSecondary, 'mt-4 w-full')}
              onClick={() => onNavigate(`/products/${product.slug}`)}
            >
              View Offer
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
