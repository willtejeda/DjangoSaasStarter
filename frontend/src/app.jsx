import {
  PricingTable,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
  useUser
} from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useEffect, useMemo, useState } from 'preact/hooks';

import { apiRequest, authedRequest, getApiBaseUrl } from './lib/api';

const BILLING_PORTAL_URL = (import.meta.env.VITE_CLERK_BILLING_PORTAL_URL || '').trim();

function formatCurrencyFromCents(cents, currency = 'USD') {
  const numeric = Number(cents || 0) / 100;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
  }).format(numeric);
}

function inferPlanFromFeatures(features) {
  const normalized = new Set((features || []).map((item) => String(item).toLowerCase()));
  if (normalized.has('enterprise')) {
    return 'enterprise';
  }
  if (normalized.has('pro') || normalized.has('premium') || normalized.has('growth')) {
    return 'pro';
  }
  return 'free';
}

function usePathname() {
  const [pathname, setPathname] = useState(() => window.location.pathname || '/');

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname || '/');
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = (nextPath) => {
    if (!nextPath || nextPath === pathname) {
      return;
    }
    window.history.pushState({}, '', nextPath);
    setPathname(nextPath);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return { pathname, navigate };
}

function NavLink({ to, currentPath, onNavigate, children }) {
  const active = currentPath === to;

  return (
    <a
      href={to}
      className={`site-link ${active ? 'site-link-active' : ''}`}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(to);
      }}
    >
      {children}
    </a>
  );
}

function Header({ pathname, onNavigate, signedIn }) {
  return (
    <header className="site-header panel">
      <div className="site-brand" onClick={() => onNavigate(signedIn ? '/app' : '/')}>DjangoStarter Commerce</div>
      <nav className="site-nav" aria-label="Primary">
        <NavLink to={signedIn ? '/app' : '/'} currentPath={pathname} onNavigate={onNavigate}>Home</NavLink>
        <NavLink to="/products" currentPath={pathname} onNavigate={onNavigate}>Products</NavLink>
        <NavLink to="/pricing" currentPath={pathname} onNavigate={onNavigate}>Pricing</NavLink>
        {signedIn ? (
          <>
            <NavLink to="/account/purchases" currentPath={pathname} onNavigate={onNavigate}>Purchases</NavLink>
            <NavLink to="/account/downloads" currentPath={pathname} onNavigate={onNavigate}>Downloads</NavLink>
            <NavLink to="/account/subscriptions" currentPath={pathname} onNavigate={onNavigate}>Subscriptions</NavLink>
          </>
        ) : null}
      </nav>
      <div className="site-actions">
        {signedIn ? (
          <UserButton afterSignOutUrl="/" />
        ) : (
          <>
            <SignInButton mode="modal">
              <button type="button" className="button button-secondary">Sign In</button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button type="button" className="button button-primary">Start Free</button>
            </SignUpButton>
          </>
        )}
      </div>
    </header>
  );
}

function MarketingHome({ onNavigate }) {
  return (
    <>
      <header className="hero">
        <div className="hero-chip">Django + Supabase + Clerk + Preact</div>
        <h1>Ship digital product and service revenue in one stack.</h1>
        <p>
          Sell files, subscriptions, and service engagements with Clerk billing, Django APIs,
          and a buyer portal for purchases, downloads, and account lifecycle.
        </p>
        <div className="hero-actions">
          <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
            Browse Products
          </button>
          <button type="button" className="button button-secondary" onClick={() => onNavigate('/pricing')}>
            View Pricing
          </button>
        </div>
      </header>

      <section className="panel grid-three">
        <article>
          <h3>Commerce data model</h3>
          <p>Products, prices, orders, subscriptions, entitlements, and delivery grants are modeled in Django ORM.</p>
        </article>
        <article>
          <h3>Billing through Clerk</h3>
          <p>Use Pricing Table and Clerk subscriptions while syncing local billing state through webhooks.</p>
        </article>
        <article>
          <h3>Customer delivery UX</h3>
          <p>Buyers get purchases, downloadable assets, and service booking requests in one account surface.</p>
        </article>
      </section>

      <section className="panel">
        <h2>Pages included</h2>
        <ul className="check-grid">
          <li>Pricing page with Clerk Billing table</li>
          <li>Public product catalog and product detail pages</li>
          <li>Checkout success and cancel states</li>
          <li>Account purchases, subscriptions, downloads, bookings</li>
          <li>Customer dashboard and seller APIs</li>
        </ul>
      </section>
    </>
  );
}

function PricingPage({ signedIn }) {
  return (
    <section className="panel">
      <h1>Pricing</h1>
      <p>
        Configure plans in Clerk Billing, then this table renders live pricing and checkout.
      </p>
      <div className="pricing-shell">
        <PricingTable />
      </div>
      {signedIn ? (
        <p className="helper-text">Signed in customers can manage active plans from subscriptions page.</p>
      ) : (
        <p className="helper-text">Sign in to subscribe and manage your billing profile.</p>
      )}
    </section>
  );
}

function ProductCatalog({ onNavigate }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isActive = true;
    setLoading(true);
    setError('');

    apiRequest('/products/')
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
        setError(requestError instanceof Error ? requestError.message : 'Could not load catalog.');
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
    <section className="panel">
      <h1>Products</h1>
      <p>Choose a digital product or service offer. Clerk handles billing and the app handles fulfillment.</p>
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading catalog...</p> : null}
      {!loading && products.length === 0 ? <p>No published products yet.</p> : null}

      <div className="catalog-grid">
        {products.map((product) => (
          <article key={product.id} className="product-card">
            <div className="product-card-top">
              <span className={`pill pill-${product.product_type}`}>{product.product_type}</span>
              {product.active_price ? (
                <strong>{formatCurrencyFromCents(product.active_price.amount_cents, product.active_price.currency)}</strong>
              ) : (
                <strong>Unpriced</strong>
              )}
            </div>
            <h3>{product.name}</h3>
            <p>{product.tagline || product.description || 'No description yet.'}</p>
            <button
              type="button"
              className="button button-secondary"
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

function ProductDetail({ slug, signedIn, onNavigate, getToken }) {
  const [product, setProduct] = useState(null);
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

    apiRequest(`/products/${slug}/`)
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

  const handleBuy = async (priceId) => {
    if (!signedIn) {
      onNavigate('/pricing');
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const orderResponse = await authedRequest(getToken, '/account/orders/create/', {
        method: 'POST',
        body: { price_id: priceId, quantity: 1 }
      });

      const checkoutUrl = orderResponse?.checkout?.checkout_url || '';
      const publicId = orderResponse?.order?.public_id;

      if (!publicId) {
        throw new Error('Order did not return a valid id.');
      }

      if (checkoutUrl) {
        window.location.href = checkoutUrl;
        return;
      }

      await authedRequest(getToken, `/account/orders/${publicId}/confirm/`, {
        method: 'POST',
        body: {
          provider: 'manual',
          external_id: `manual_${Date.now()}`
        }
      });

      setSuccess('Purchase completed. Your fulfillment has been created.');
      onNavigate('/checkout/success');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not complete purchase flow.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <section className="panel"><p>Loading offer...</p></section>;
  }

  if (!product) {
    return <section className="panel"><p>Offer not found.</p></section>;
  }

  return (
    <section className="panel">
      <div className="product-detail-head">
        <span className={`pill pill-${product.product_type}`}>{product.product_type}</span>
        <h1>{product.name}</h1>
        <p>{product.description || product.tagline || 'No description yet.'}</p>
      </div>

      {error ? <p className="warning-text">{error}</p> : null}
      {success ? <p className="success-text">{success}</p> : null}

      <div className="pricing-grid">
        {(product.prices || []).map((price) => (
          <article className="billing-plan-card" key={price.id}>
            <div className="billing-plan-header">
              <h3>{price.name || price.billing_period}</h3>
              <span className="plan-price">{formatCurrencyFromCents(price.amount_cents, price.currency)}</span>
            </div>
            <p className="plan-audience">{price.billing_period.replace('_', ' ')}</p>
            <button
              type="button"
              className="button button-primary"
              disabled={saving}
              onClick={() => handleBuy(price.id)}
            >
              {saving ? 'Processing...' : signedIn ? 'Buy Now' : 'Sign In to Buy'}
            </button>
          </article>
        ))}
      </div>

      {product.assets?.length ? (
        <div>
          <h2>Included assets</h2>
          <ul className="check-grid">
            {product.assets.map((asset) => (
              <li key={asset.id}>{asset.title}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {product.service_offer ? (
        <div>
          <h2>Service delivery</h2>
          <ul className="check-grid">
            <li>Session minutes: {product.service_offer.session_minutes}</li>
            <li>Delivery days: {product.service_offer.delivery_days}</li>
            <li>Revisions: {product.service_offer.revision_count}</li>
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function PurchasesPage({ getToken }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOrders = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await authedRequest(getToken, '/account/orders/');
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
    <section className="panel">
      <h1>Purchases</h1>
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading purchases...</p> : null}
      {!loading && orders.length === 0 ? <p>No purchases yet.</p> : null}

      <div className="order-list">
        {orders.map((order) => (
          <article key={order.public_id} className="order-card">
            <div className="project-heading">
              <h3>Order {String(order.public_id).slice(0, 8)}</h3>
              <span className={`pill pill-${order.status}`}>{order.status}</span>
            </div>
            <p>Total: {formatCurrencyFromCents(order.total_cents, order.currency)}</p>
            <p>{order.items?.length || 0} item(s)</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function SubscriptionsPage({ getToken }) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest(getToken, '/account/subscriptions/')
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
    <section className="panel">
      <h1>Subscriptions</h1>
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading subscriptions...</p> : null}
      {!loading && subscriptions.length === 0 ? <p>No active subscriptions found.</p> : null}

      <div className="order-list">
        {subscriptions.map((subscription) => (
          <article key={subscription.id} className="order-card">
            <div className="project-heading">
              <h3>{subscription.product_name || 'Subscription'}</h3>
              <span className={`pill pill-${subscription.status}`}>{subscription.status}</span>
            </div>
            <p>
              {subscription.price_summary
                ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                : 'No linked local price'}
            </p>
          </article>
        ))}
      </div>

      <SignedIn>
        <div className="panel">
          <h3>Manage in Clerk</h3>
          <SubscriptionDetailsButton>
            <button type="button" className="button button-secondary">Open Subscription Details</button>
          </SubscriptionDetailsButton>
        </div>
      </SignedIn>
    </section>
  );
}

function DownloadsPage({ getToken }) {
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const loadGrants = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await authedRequest(getToken, '/account/downloads/');
      setGrants(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load downloads.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGrants();
  }, []);

  const requestAccess = async (token) => {
    setAccessingToken(token);
    setError('');

    try {
      const payload = await authedRequest(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST'
      });

      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      await loadGrants();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not generate download access.');
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <section className="panel">
      <h1>Downloads</h1>
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading downloadable assets...</p> : null}
      {!loading && grants.length === 0 ? <p>No digital deliveries are available yet.</p> : null}

      <div className="order-list">
        {grants.map((grant) => (
          <article key={grant.token} className="order-card">
            <div className="project-heading">
              <h3>{grant.asset_title}</h3>
              <span className={`pill ${grant.can_download ? 'pill-live' : 'pill-paused'}`}>
                {grant.can_download ? 'ready' : 'locked'}
              </span>
            </div>
            <p>{grant.product_name}</p>
            <p>{grant.download_count}/{grant.max_downloads} downloads used</p>
            <button
              type="button"
              className="button button-primary"
              disabled={!grant.can_download || accessingToken === grant.token}
              onClick={() => requestAccess(grant.token)}
            >
              {accessingToken === grant.token ? 'Preparing...' : 'Get Download Link'}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function BookingsPage({ getToken }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authedRequest(getToken, '/account/bookings/')
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
    <section className="panel">
      <h1>Bookings</h1>
      {error ? <p className="warning-text">{error}</p> : null}
      {loading ? <p>Loading booking requests...</p> : null}
      {!loading && bookings.length === 0 ? <p>No service bookings yet.</p> : null}

      <div className="order-list">
        {bookings.map((booking) => (
          <article key={booking.id} className="order-card">
            <div className="project-heading">
              <h3>{booking.product_name || 'Service booking'}</h3>
              <span className={`pill pill-${booking.status}`}>{booking.status}</span>
            </div>
            <p>{booking.customer_notes || 'No notes provided.'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function CheckoutState({ state, onNavigate }) {
  const isSuccess = state === 'success';
  return (
    <section className="panel">
      <h1>{isSuccess ? 'Checkout Successful' : 'Checkout Canceled'}</h1>
      <p>
        {isSuccess
          ? 'Payment completed. Your order fulfillment is available in purchases and downloads.'
          : 'No charge was made. You can return to product details and try again.'}
      </p>
      <div className="hero-actions">
        <button type="button" className="button button-primary" onClick={() => onNavigate('/account/purchases')}>
          View Purchases
        </button>
        <button type="button" className="button button-secondary" onClick={() => onNavigate('/products')}>
          Browse Products
        </button>
      </div>
    </section>
  );
}

function MetricCard({ label, value, note }) {
  return (
    <article className="metric-card">
      <p className="metric-label">{label}</p>
      <h3>{value}</h3>
      <p className="metric-note">{note}</p>
    </article>
  );
}

function AccountDashboard({ onNavigate }) {
  const { getToken, isLoaded, userId } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState(null);
  const [billing, setBilling] = useState({ enabled_features: [] });
  const [orders, setOrders] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [entitlements, setEntitlements] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const apiBase = getApiBaseUrl();

  const loadDashboard = async ({ silent = false } = {}) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');

    try {
      const [
        mePayload,
        billingPayload,
        ordersPayload,
        subscriptionsPayload,
        downloadsPayload,
        entitlementsPayload,
        bookingsPayload
      ] = await Promise.all([
        authedRequest(getToken, '/me/'),
        authedRequest(getToken, '/billing/features/'),
        authedRequest(getToken, '/account/orders/'),
        authedRequest(getToken, '/account/subscriptions/'),
        authedRequest(getToken, '/account/downloads/'),
        authedRequest(getToken, '/account/entitlements/'),
        authedRequest(getToken, '/account/bookings/')
      ]);
      setMe(mePayload || null);
      setBilling(billingPayload || { enabled_features: [] });
      setOrders(Array.isArray(ordersPayload) ? ordersPayload : []);
      setSubscriptions(Array.isArray(subscriptionsPayload) ? subscriptionsPayload : []);
      setDownloads(Array.isArray(downloadsPayload) ? downloadsPayload : []);
      setEntitlements(Array.isArray(entitlementsPayload) ? entitlementsPayload : []);
      setBookings(Array.isArray(bookingsPayload) ? bookingsPayload : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!isLoaded || !userId) {
      return;
    }
    loadDashboard();
  }, [isLoaded, userId]);

  const enabledFeatures = billing.enabled_features || me?.billing_features || [];
  const planTier = me?.profile?.plan_tier || inferPlanFromFeatures(enabledFeatures);
  const displayName =
    me?.customer_account?.full_name ||
    user?.firstName ||
    me?.profile?.first_name ||
    user?.primaryEmailAddress?.emailAddress ||
    user?.username ||
    user?.id ||
    'there';

  const paidOrders = useMemo(
    () => orders.filter((order) => ['paid', 'fulfilled'].includes(order.status)).length,
    [orders]
  );

  const activeSubscriptions = useMemo(
    () => subscriptions.filter((subscription) => ['active', 'trialing', 'past_due'].includes(subscription.status)),
    [subscriptions]
  );

  const readyDownloads = useMemo(
    () => downloads.filter((grant) => grant.can_download).length,
    [downloads]
  );

  const currentEntitlements = useMemo(
    () => entitlements.filter((entitlement) => entitlement.is_current).length,
    [entitlements]
  );

  const openServiceRequests = useMemo(
    () => bookings.filter((booking) => ['requested', 'confirmed'].includes(booking.status)).length,
    [bookings]
  );

  const requestAccess = async (token) => {
    setAccessingToken(token);
    setError('');
    try {
      const payload = await authedRequest(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST'
      });
      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      await loadDashboard({ silent: true });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not generate download access.');
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <>
      <section className="metrics-grid">
        <MetricCard label="Plan" value={planTier.toUpperCase()} note={`${enabledFeatures.length} features enabled`} />
        <MetricCard label="Paid Orders" value={String(paidOrders)} note={`${orders.length} total purchases`} />
        <MetricCard label="Active Subs" value={String(activeSubscriptions.length)} note={`${subscriptions.length} total subscriptions`} />
        <MetricCard label="Ready Downloads" value={String(readyDownloads)} note={`${downloads.length} total deliveries`} />
        <MetricCard label="Feature Access" value={String(currentEntitlements)} note="Current entitlements" />
        <MetricCard label="Open Requests" value={String(openServiceRequests)} note="Service bookings in progress" />
      </section>

      {error ? <section className="panel warning-panel">{error}</section> : null}

      <section className="panel split-grid">
        <article>
          <p className="eyebrow">Account Home</p>
          <h2>Welcome back, {displayName}.</h2>
          <p>
            This dashboard keeps your subscriptions, orders, and downloadable purchases in one place.
          </p>
          <div className="hero-actions">
            <button type="button" className="button button-primary" onClick={() => onNavigate('/products')}>
              Browse Products
            </button>
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/pricing')}>
              View Pricing
            </button>
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/purchases')}>
              View Purchases
            </button>
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/downloads')}>
              View Downloads
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={() => onNavigate('/account/subscriptions')}
            >
              View Subscriptions
            </button>
            <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/bookings')}>
              View Bookings
            </button>
          </div>
          {BILLING_PORTAL_URL ? (
            <a className="button button-secondary" href={BILLING_PORTAL_URL} target="_blank" rel="noreferrer">
              Manage Billing
            </a>
          ) : (
            <SubscriptionDetailsButton>
              <button type="button" className="button button-secondary">Manage Billing</button>
            </SubscriptionDetailsButton>
          )}
        </article>

        <article>
          <h2>Recent purchases</h2>
          {loading ? <p>Loading purchases...</p> : null}
          {!loading && orders.length === 0 ? <p>No purchases yet.</p> : null}
          <div className="order-list">
            {orders.slice(0, 5).map((order) => (
              <article className="order-card" key={order.public_id}>
                <div className="project-heading">
                  <h3>Order {String(order.public_id).slice(0, 8)}</h3>
                  <span className={`pill pill-${order.status}`}>{order.status}</span>
                </div>
                <p>Total: {formatCurrencyFromCents(order.total_cents, order.currency)}</p>
                <p>{order.items?.length || 0} item(s)</p>
              </article>
            ))}
          </div>
          <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/purchases')}>
            Open Purchases
          </button>
        </article>
      </section>

      <section className="panel split-grid">
        <article>
          <h2>Digital deliveries</h2>
          {loading ? <p>Loading downloads...</p> : null}
          {!loading && downloads.length === 0 ? <p>No digital deliveries available yet.</p> : null}
          <div className="order-list">
            {downloads.slice(0, 5).map((grant) => (
              <article className="order-card" key={grant.token}>
                <div className="project-heading">
                  <h3>{grant.asset_title}</h3>
                  <span className={`pill ${grant.can_download ? 'pill-live' : 'pill-paused'}`}>
                    {grant.can_download ? 'ready' : 'locked'}
                  </span>
                </div>
                <p>{grant.product_name}</p>
                <p>{grant.download_count}/{grant.max_downloads} downloads used</p>
                <button
                  type="button"
                  className="button button-primary"
                  disabled={!grant.can_download || accessingToken === grant.token}
                  onClick={() => requestAccess(grant.token)}
                >
                  {accessingToken === grant.token ? 'Preparing...' : 'Download'}
                </button>
              </article>
            ))}
          </div>
          <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/downloads')}>
            Open Downloads
          </button>
        </article>

        <article>
          <h2>Subscriptions and access</h2>
          {loading ? <p>Loading subscriptions...</p> : null}
          {!loading && activeSubscriptions.length === 0 ? <p>No active subscriptions found.</p> : null}
          <div className="order-list">
            {activeSubscriptions.slice(0, 4).map((subscription) => (
              <article className="order-card" key={subscription.id}>
                <div className="project-heading">
                  <h3>{subscription.product_name || 'Subscription'}</h3>
                  <span className={`pill pill-${subscription.status}`}>{subscription.status}</span>
                </div>
                <p>
                  {subscription.price_summary
                    ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                    : 'No linked local price'}
                </p>
              </article>
            ))}
          </div>
          <h3>Current feature access</h3>
          {entitlements.filter((entitlement) => entitlement.is_current).length === 0 ? (
            <p className="helper-text">No active entitlements yet.</p>
          ) : (
            <div className="feature-list">
              {entitlements
                .filter((entitlement) => entitlement.is_current)
                .slice(0, 8)
                .map((entitlement) => (
                  <span className="feature-tag" key={entitlement.id}>
                    {entitlement.feature_key}
                  </span>
                ))}
            </div>
          )}
          <button
            type="button"
            className="button button-secondary"
            onClick={() => onNavigate('/account/subscriptions')}
          >
            Open Subscriptions
          </button>
        </article>
      </section>

      <section className="panel split-grid">
        <article>
          <h2>Service bookings</h2>
          {loading ? <p>Loading booking requests...</p> : null}
          {!loading && bookings.length === 0 ? <p>No booking requests yet.</p> : null}
          <div className="order-list">
            {bookings.slice(0, 4).map((booking) => (
              <article className="order-card" key={booking.id}>
                <div className="project-heading">
                  <h3>{booking.product_name || 'Service booking'}</h3>
                  <span className={`pill pill-${booking.status}`}>{booking.status}</span>
                </div>
                <p>{booking.customer_notes || 'No notes provided.'}</p>
              </article>
            ))}
          </div>
          <button type="button" className="button button-secondary" onClick={() => onNavigate('/account/bookings')}>
            Open Bookings
          </button>
        </article>
        <article>
          <h2>Developer context</h2>
          <p className="helper-text">API base: <code>{apiBase}</code></p>
          <p className="helper-text">Data refresh: {refreshing ? 'updating now' : 'automatic on page load and downloads'}</p>
          <p className="helper-text">Use the account routes for full detail views.</p>
        </article>
      </section>

      {user ? <p className="helper-text">Signed in as {user.primaryEmailAddress?.emailAddress || user.username || user.id}</p> : null}
    </>
  );
}

function SignedOutApp({ pathname, onNavigate }) {
  const isProductDetail = pathname.startsWith('/products/');
  const productSlug = isProductDetail ? pathname.replace('/products/', '') : '';

  let content = <MarketingHome onNavigate={onNavigate} />;
  if (pathname === '/pricing') {
    content = <PricingPage signedIn={false} />;
  } else if (pathname === '/products') {
    content = <ProductCatalog onNavigate={onNavigate} />;
  } else if (isProductDetail && productSlug) {
    content = <ProductDetail slug={productSlug} signedIn={false} onNavigate={onNavigate} getToken={null} />;
  }

  return (
    <main className="shell">
      <Header pathname={pathname} onNavigate={onNavigate} signedIn={false} />
      {content}
    </main>
  );
}

function SignedInApp({ pathname, onNavigate }) {
  const { getToken } = useAuth();
  const isProductDetail = pathname.startsWith('/products/');
  const productSlug = isProductDetail ? pathname.replace('/products/', '') : '';

  let content = <AccountDashboard onNavigate={onNavigate} />;

  if (pathname === '/pricing') {
    content = <PricingPage signedIn />;
  } else if (pathname === '/products') {
    content = <ProductCatalog onNavigate={onNavigate} />;
  } else if (isProductDetail && productSlug) {
    content = <ProductDetail slug={productSlug} signedIn onNavigate={onNavigate} getToken={getToken} />;
  } else if (pathname === '/account/purchases') {
    content = <PurchasesPage getToken={getToken} />;
  } else if (pathname === '/account/subscriptions') {
    content = <SubscriptionsPage getToken={getToken} />;
  } else if (pathname === '/account/downloads') {
    content = <DownloadsPage getToken={getToken} />;
  } else if (pathname === '/account/bookings') {
    content = <BookingsPage getToken={getToken} />;
  } else if (pathname === '/checkout/success') {
    content = <CheckoutState state="success" onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/cancel') {
    content = <CheckoutState state="cancel" onNavigate={onNavigate} />;
  } else if (pathname !== '/' && pathname !== '/app') {
    content = (
      <section className="panel">
        <h1>Page not found</h1>
        <p>Try one of the available pages from navigation.</p>
      </section>
    );
  }

  return (
    <main className="shell">
      <Header pathname={pathname} onNavigate={onNavigate} signedIn />
      {content}
    </main>
  );
}

export function App() {
  const { pathname, navigate } = usePathname();

  return (
    <>
      <SignedOut>
        <SignedOutApp pathname={pathname} onNavigate={navigate} />
      </SignedOut>
      <SignedIn>
        <SignedInApp pathname={pathname} onNavigate={navigate} />
      </SignedIn>
    </>
  );
}
