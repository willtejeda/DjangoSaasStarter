import { useAuth, useUser } from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useEffect, useMemo, useState, type ReactElement } from 'react';

import { MetricCard, PageIntro, StatusPill, TutorialBlock, UsageBar } from '../../../components/layout/app-shell';
import { useToast } from '../../../components/feedback/toast';
import { apiRequest, authedRequest, getApiBaseUrl } from '../../../lib/api';
import type {
  AiProviderRecord,
  AiUsageSummaryResponse,
  BillingFeaturesResponse,
  DashboardProps,
  DownloadAccessResponse,
  DownloadGrant,
  EntitlementRecord,
  MeResponse,
  OrderRecord,
  PreflightEmailResponse,
  ProductRecord,
  SubscriptionRecord,
  SupabaseProbeResponse,
  WorkOrderRecord,
} from '../../../shared/types';
import {
  buttonGhost,
  buttonPrimary,
  buttonSecondary,
  cardClass,
  cn,
  formatCurrencyFromCents,
  inferPlanFromFeatures,
  isPlanTier,
  sectionClass,
} from '../../../shared/ui-utils';

const BILLING_PORTAL_URL = (import.meta.env.VITE_CLERK_BILLING_PORTAL_URL || '').trim();
const PREFLIGHT_EMAIL_STORAGE_KEY = 'ds-preflight-email-test';

function isInternalClerkLikeId(value: string): boolean {
  const normalized = value.trim();
  return /^user_[A-Za-z0-9]+$/.test(normalized);
}

function normalizeDisplayLabel(value?: string | null): string {
  const normalized = String(value || '').trim();
  if (!normalized) {
    return '';
  }
  if (isInternalClerkLikeId(normalized)) {
    return '';
  }
  return normalized;
}

function firstNameFromFullName(fullName?: string | null): string {
  const normalized = normalizeDisplayLabel(fullName);
  if (!normalized) {
    return '';
  }
  return normalized.split(/\s+/)[0] || '';
}

function friendlyNameFromEmail(email?: string | null): string {
  const normalizedEmail = String(email || '').trim();
  if (!normalizedEmail) {
    return '';
  }
  const localPart = normalizedEmail.split('@')[0]?.trim() || '';
  if (!localPart || isInternalClerkLikeId(localPart)) {
    return '';
  }
  const words = localPart
    .replace(/[._-]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3);
  if (!words.length) {
    return '';
  }
  return words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

export function AccountDashboard({ onNavigate, getToken }: DashboardProps): ReactElement {
  const notify = useToast();
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState<MeResponse | null>(null);
  const [billing, setBilling] = useState<BillingFeaturesResponse>({ enabled_features: [] });
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [downloads, setDownloads] = useState<DownloadGrant[]>([]);
  const [entitlements, setEntitlements] = useState<EntitlementRecord[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrderRecord[]>([]);
  const [catalogProducts, setCatalogProducts] = useState<ProductRecord[]>([]);
  const [aiProviders, setAiProviders] = useState<AiProviderRecord[]>([]);
  const [aiUsage, setAiUsage] = useState<AiUsageSummaryResponse>({ period: 'current', plan_tier: 'free', buckets: [], notes: [] });
  const [supabaseProbe, setSupabaseProbe] = useState<{ checked: boolean; ok: boolean; detail: string }>({
    checked: false,
    ok: false,
    detail: 'Not tested yet.',
  });
  const [emailTestStatus, setEmailTestStatus] = useState<{
    sent: boolean;
    detail: string;
    recipientEmail: string;
    sentAt: string;
    running: boolean;
  }>(() => {
    if (typeof window === 'undefined') {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }

    const raw = window.localStorage.getItem(PREFLIGHT_EMAIL_STORAGE_KEY);
    if (!raw) {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }

    try {
      const parsed = JSON.parse(raw) as { recipient_email?: string; sent_at?: string };
      const sentAt = String(parsed.sent_at || '');
      return {
        sent: Boolean(sentAt),
        detail: sentAt ? `Last test email sent at ${new Date(sentAt).toLocaleString()}.` : 'Not tested yet.',
        recipientEmail: String(parsed.recipient_email || ''),
        sentAt,
        running: false,
      };
    } catch {
      return {
        sent: false,
        detail: 'Not tested yet.',
        recipientEmail: '',
        sentAt: '',
        running: false,
      };
    }
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const apiBase = getApiBaseUrl();

  const loadDashboard = async ({ silent = false }: { silent?: boolean } = {}): Promise<void> => {
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
        workOrdersPayload,
        catalogPayload,
        aiProvidersPayload,
        aiUsagePayload,
        supabaseProbePayload,
      ] = await Promise.all([
        authedRequest<MeResponse>(getToken, '/me/'),
        authedRequest<BillingFeaturesResponse>(getToken, '/billing/features/'),
        authedRequest<OrderRecord[]>(getToken, '/account/orders/'),
        authedRequest<SubscriptionRecord[]>(getToken, '/account/subscriptions/'),
        authedRequest<DownloadGrant[]>(getToken, '/account/downloads/'),
        authedRequest<EntitlementRecord[]>(getToken, '/account/entitlements/'),
        authedRequest<WorkOrderRecord[]>(getToken, '/account/orders/work/'),
        apiRequest<ProductRecord[]>('/products/').catch(() => []),
        authedRequest<AiProviderRecord[]>(getToken, '/ai/providers/').catch(() => []),
        authedRequest<AiUsageSummaryResponse>(getToken, '/ai/usage/summary/').catch(() => ({
          period: 'current',
          plan_tier: 'free',
          buckets: [],
          notes: [],
        })),
        authedRequest<SupabaseProbeResponse>(getToken, '/supabase/profile/')
          .then((payload) => {
            const ok = payload?.ok ?? true;
            const detailFromApi = typeof payload?.detail === 'string' ? payload.detail.trim() : '';
            const detail = detailFromApi
              || (ok
                ? (payload?.profile ? 'Supabase profile probe succeeded.' : 'Supabase probe succeeded. No profile row found yet.')
                : 'Supabase probe failed.');
            return {
              checked: true,
              ok,
              detail,
            };
          })
          .catch((probeError) => ({
            checked: true,
            ok: false,
            detail: probeError instanceof Error ? probeError.message : 'Supabase probe failed.',
          })),
      ]);
      setMe(mePayload || null);
      setBilling(billingPayload || { enabled_features: [] });
      setOrders(Array.isArray(ordersPayload) ? ordersPayload : []);
      setSubscriptions(Array.isArray(subscriptionsPayload) ? subscriptionsPayload : []);
      setDownloads(Array.isArray(downloadsPayload) ? downloadsPayload : []);
      setEntitlements(Array.isArray(entitlementsPayload) ? entitlementsPayload : []);
      setWorkOrders(Array.isArray(workOrdersPayload) ? workOrdersPayload : []);
      setCatalogProducts(Array.isArray(catalogPayload) ? catalogPayload : []);
      setAiProviders(Array.isArray(aiProvidersPayload) ? aiProvidersPayload : []);
      setAiUsage(aiUsagePayload || { period: 'current', plan_tier: 'free', buckets: [], notes: [] });
      setSupabaseProbe(
        supabaseProbePayload || {
          checked: false,
          ok: false,
          detail: 'Not tested yet.',
        }
      );

      const metadata = mePayload?.customer_account?.metadata;
      if (metadata && typeof metadata === 'object') {
        const sentAt = String((metadata as Record<string, unknown>).preflight_email_last_sent_at || '');
        const recipientEmail = String((metadata as Record<string, unknown>).preflight_email_last_recipient || '');
        if (sentAt) {
          const detail = `Last test email sent at ${new Date(sentAt).toLocaleString()}.`;
          setEmailTestStatus((previous) => ({
            ...previous,
            sent: true,
            detail,
            recipientEmail: recipientEmail || previous.recipientEmail,
            sentAt,
            running: false,
          }));
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(
              PREFLIGHT_EMAIL_STORAGE_KEY,
              JSON.stringify({
                recipient_email: recipientEmail,
                sent_at: sentAt,
              })
            );
          }
        }
      }
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Failed to load dashboard data.';
      setError(detail);
      notify({
        title: 'Dashboard sync failed',
        detail,
        variant: 'error',
      });
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

  const enabledFeatures: string[] = billing.enabled_features || me?.billing_features || [];
  const planTier = isPlanTier(me?.profile?.plan_tier) ? me.profile.plan_tier : inferPlanFromFeatures(enabledFeatures);
  const primaryEmail = String(user?.primaryEmailAddress?.emailAddress || '').trim();
  const displayName =
    firstNameFromFullName(me?.customer_account?.full_name)
    || normalizeDisplayLabel(user?.firstName)
    || normalizeDisplayLabel(me?.profile?.first_name)
    || firstNameFromFullName(friendlyNameFromEmail(primaryEmail))
    || 'creator';
  const accountIdentityLabel =
    primaryEmail
    || normalizeDisplayLabel(user?.username)
    || displayName;

  const paidOrders = useMemo(() => orders.filter((order) => ['paid', 'fulfilled'].includes(order.status)).length, [orders]);

  const activeSubscriptions = useMemo(
    () => subscriptions.filter((subscription) => ['active', 'trialing', 'past_due'].includes(subscription.status)),
    [subscriptions]
  );

  const readyDownloads = useMemo(() => downloads.filter((grant) => grant.can_download).length, [downloads]);

  const currentEntitlements = useMemo(
    () => entitlements.filter((entitlement) => entitlement.is_current).length,
    [entitlements]
  );

  const openServiceRequests = useMemo(
    () => workOrders.filter((order) => ['requested', 'in_progress', 'ready_for_delivery'].includes(order.status)).length,
    [workOrders]
  );

  const publishedProducts = catalogProducts.length;
  const pricedProducts = useMemo(
    () => catalogProducts.filter((product) => Boolean(product.active_price || product.prices?.length)).length,
    [catalogProducts]
  );

  const configuredAiProviders = aiProviders.filter((provider) => provider.enabled).length;
  const bucketsNearLimit = aiUsage.buckets.filter((bucket) => bucket.near_limit).length;
  const subscriptionUsageReady = activeSubscriptions.length > 0 && aiUsage.buckets.length > 0;

  const sendPreflightEmailTest = async (): Promise<void> => {
    setEmailTestStatus((previous) => ({
      ...previous,
      running: true,
      detail: 'Sending test email...',
    }));
    setError('');
    try {
      const payload = await authedRequest<PreflightEmailResponse>(getToken, '/account/preflight/email-test/', {
        method: 'POST',
      });
      const sentAt = String(payload.sent_at || new Date().toISOString());
      const recipientEmail = String(payload.recipient_email || '');
      const detail = payload.detail || `Test email sent at ${new Date(sentAt).toLocaleString()}.`;
      setEmailTestStatus({
        sent: Boolean(payload.sent),
        detail,
        recipientEmail,
        sentAt,
        running: false,
      });
      if (payload.sent) {
        notify({
          title: 'Preflight email sent',
          detail,
          variant: 'success',
        });
      }
      if (typeof window !== 'undefined' && payload.sent) {
        window.localStorage.setItem(
          PREFLIGHT_EMAIL_STORAGE_KEY,
          JSON.stringify({
            recipient_email: recipientEmail,
            sent_at: sentAt,
          })
        );
      }
      await loadDashboard({ silent: true });
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not send test email.';
      setEmailTestStatus((previous) => ({
        ...previous,
        sent: false,
        running: false,
        detail,
      }));
      notify({ title: 'Email test failed', detail, variant: 'error' });
    }
  };

  const preflightSteps: Array<{
    key: string;
    label: string;
    done: boolean;
    hint: string;
    actionLabel: string;
    route?: string;
    action?: () => void;
  }> = [
    {
      key: 'clerk_sync',
      label: 'Clerk auth and account sync',
      done: Boolean(me?.profile) && Boolean(me?.customer_account),
      hint: 'Sign in and verify `/api/me/` returns profile and customer account data.',
      actionLabel: 'Refresh check',
      action: () => {
        loadDashboard({ silent: true });
      },
    },
    {
      key: 'supabase_probe',
      label: 'Supabase bridge test',
      done: supabaseProbe.checked && supabaseProbe.ok,
      hint: supabaseProbe.detail,
      actionLabel: 'Run Supabase probe',
      action: () => {
        loadDashboard({ silent: true });
      },
    },
    {
      key: 'resend_email',
      label: 'Resend delivery test',
      done: emailTestStatus.sent,
      hint: emailTestStatus.sent
        ? `${emailTestStatus.detail}${emailTestStatus.recipientEmail ? ` Recipient: ${emailTestStatus.recipientEmail}.` : ''}`
        : emailTestStatus.detail || 'Send one test email before starting product work.',
      actionLabel: emailTestStatus.running ? 'Sending...' : 'Send test email',
      action: () => {
        if (!emailTestStatus.running) {
          void sendPreflightEmailTest();
        }
      },
    },
    {
      key: 'order_attempt',
      label: 'Order placement test',
      done: orders.length > 0,
      hint: 'Place one test order from `/products` and confirm it appears in purchases.',
      actionLabel: 'Run order test',
      route: '/products',
    },
    {
      key: 'webhook_payment',
      label: 'Webhook payment confirmation test',
      done: paidOrders > 0,
      hint: 'Complete checkout and verify order status changes to `paid` or `fulfilled`.',
      actionLabel: 'Review purchases',
      route: '/account/purchases',
    },
    {
      key: 'subscription_usage',
      label: 'Subscription and usage test',
      done: subscriptionUsageReady,
      hint: 'Run one recurring checkout and verify subscription plus usage buckets in `/app`.',
      actionLabel: 'Open subscriptions',
      route: '/account/subscriptions',
    },
  ];

  const completedPreflightCount = preflightSteps.filter((step) => step.done).length;
  const preflightComplete = completedPreflightCount === preflightSteps.length;
  const nextPreflightStep = preflightSteps.find((step) => !step.done);

  const requestAccess = async (token: string): Promise<void> => {
    setAccessingToken(token);
    setError('');
    try {
      const payload = await authedRequest<DownloadAccessResponse>(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST',
      });
      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      notify({ title: 'Download link ready', detail: 'Signed URL generated for this asset.', variant: 'success' });
      await loadDashboard({ silent: true });
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not generate download access.';
      setError(detail);
      notify({ title: 'Download generation failed', detail, variant: 'error' });
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <>
      <section className={cn(sectionClass, 'space-y-6 bg-gradient-to-br from-slate-50 to-cyan-50 dark:from-slate-900 dark:to-slate-900')}>
        <PageIntro
          eyebrow="Before You Start"
          title={`Run preflight validation before building features, ${displayName}.`}
          description="Use this checklist to prove Clerk auth, Supabase connectivity, Resend delivery, order flow, webhook payment confirmation, and subscription usage behavior."
          actions={(
            <>
              {nextPreflightStep ? (
                <button
                  type="button"
                  className={buttonPrimary}
                  onClick={() => {
                    if (nextPreflightStep.action) {
                      nextPreflightStep.action();
                      return;
                    }
                    if (nextPreflightStep.route) {
                      onNavigate(nextPreflightStep.route);
                    }
                  }}
                >
                  Continue: {nextPreflightStep.label}
                </button>
              ) : (
                <button type="button" className={buttonPrimary} onClick={() => onNavigate('/products')}>
                  Open Offers
                </button>
              )}
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
                Offers
              </button>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/pricing')}>
                Pricing
              </button>
              {BILLING_PORTAL_URL ? (
                <a className={buttonSecondary} href={BILLING_PORTAL_URL} target="_blank" rel="noreferrer">
                  Manage Billing
                </a>
              ) : (
                <SubscriptionDetailsButton>
                  <button type="button" className={buttonSecondary}>Manage Billing</button>
                </SubscriptionDetailsButton>
              )}
            </>
          )}
        />

        <TutorialBlock
          whatThisDoes="Turns integration setup into explicit preflight checks before product build work starts."
          howToTest={[
            'Run each preflight test from top to bottom',
            'Use refresh to re-check current integration status',
            'Keep notes on which step failed before debugging',
          ]}
          expectedResult="You can verify the full stack works before writing custom feature code."
        />

        <article className={cardClass}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Preflight validation</h2>
            <p className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {completedPreflightCount}/{preflightSteps.length} passing
            </p>
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            {preflightComplete
              ? 'All preflight checks passed. Start building your product-specific features.'
              : 'Resolve every failing check before starting custom product work.'}
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {preflightSteps.map((step, index) => (
              <article
                key={step.key}
                className={cn(
                  'rounded-xl border p-4',
                  step.done
                    ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20'
                    : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800'
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-900 text-xs font-semibold text-white dark:bg-cyan-400 dark:text-slate-950">
                      {index + 1}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{step.label}</h3>
                  </div>
                  <StatusPill value={step.done ? 'done' : 'next'} />
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{step.hint}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={buttonSecondary}
                    disabled={step.key === 'resend_email' && emailTestStatus.running}
                    onClick={() => {
                      if (step.action) {
                        step.action();
                        return;
                      }
                      if (step.route) {
                        onNavigate(step.route);
                      }
                    }}
                  >
                    {step.actionLabel}
                  </button>
                  {step.route ? (
                    <button type="button" className={buttonGhost} onClick={() => onNavigate(step.route!)}>
                      Open route
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </article>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Preflight"
            value={`${completedPreflightCount}/${preflightSteps.length}`}
            note={preflightComplete ? 'All checks passing' : 'Checks still pending'}
          />
          <MetricCard
            label="Supabase Probe"
            value={supabaseProbe.ok ? 'PASS' : 'FAIL'}
            note={supabaseProbe.detail}
          />
          <MetricCard
            label="Resend Test"
            value={emailTestStatus.sent ? 'SENT' : 'PENDING'}
            note={emailTestStatus.sent ? emailTestStatus.detail : 'Send one preflight email'}
          />
          <MetricCard label="Plan" value={planTier.toUpperCase()} note={`${enabledFeatures.length} features enabled`} />
          <MetricCard label="Offers" value={String(publishedProducts)} note={`${pricedProducts} with active price`} />
          <MetricCard label="Paid Orders" value={String(paidOrders)} note={`${orders.length} total purchases`} />
          <MetricCard label="Active Subs" value={String(activeSubscriptions.length)} note={`${subscriptions.length} total subscriptions`} />
          <MetricCard label="Downloads" value={String(readyDownloads)} note={`${downloads.length} total deliveries`} />
          <MetricCard label="Entitlements" value={String(currentEntitlements)} note="Current access records" />
          <MetricCard label="Work Orders" value={String(openServiceRequests)} note="Fulfillment in progress" />
          <MetricCard
            label="AI Providers"
            value={String(configuredAiProviders)}
            note={`${bucketsNearLimit} usage bucket(s) near limit`}
          />
        </div>
      </section>

      {error ? (
        <section className={cn(sectionClass, 'border-rose-300 bg-rose-50/70 dark:border-rose-700 dark:bg-rose-900/20')}>
          <p className="text-sm font-medium text-rose-700 dark:text-rose-300">{error}</p>
        </section>
      ) : null}

      <section className={cn(sectionClass, 'space-y-6')}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Recent activity</h2>
          <button
            type="button"
            className={buttonSecondary}
            onClick={() => {
              notify({ title: 'Refreshing dashboard', detail: 'Rechecking current integration state.' });
              void loadDashboard({ silent: true });
            }}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Recent purchases</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/purchases')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading purchases...</p> : null}
            {!loading && orders.length === 0 ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No purchases yet.</p> : null}
            <div className="mt-3 space-y-3">
              {orders.slice(0, 4).map((order) => (
                <article key={order.public_id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Order {String(order.public_id).slice(0, 8)}</h4>
                    <StatusPill value={order.status} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {formatCurrencyFromCents(order.total_cents, order.currency)}
                  </p>
                </article>
              ))}
            </div>
          </article>

          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Digital deliveries</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/downloads')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading downloads...</p> : null}
            {!loading && downloads.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No digital deliveries yet.</p>
            ) : null}
            <div className="mt-3 space-y-3">
              {downloads.slice(0, 4).map((grant) => (
                <article key={grant.token} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{grant.asset_title}</h4>
                    <StatusPill value={grant.can_download ? 'ready' : 'locked'} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{grant.product_name}</p>
                  <button
                    type="button"
                    className={cn(buttonPrimary, 'mt-2 w-full')}
                    disabled={!grant.can_download || accessingToken === grant.token}
                    onClick={() => requestAccess(grant.token)}
                  >
                    {accessingToken === grant.token ? 'Preparing...' : 'Download'}
                  </button>
                </article>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className={cn(sectionClass, 'space-y-6')}>
        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Subscriptions, access, and AI usage</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className={cardClass}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Subscription state</h3>
              <button type="button" className={buttonSecondary} onClick={() => onNavigate('/account/subscriptions')}>
                Open
              </button>
            </div>
            {loading ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Loading subscriptions...</p> : null}
            {!loading && activeSubscriptions.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">No active subscriptions found.</p>
            ) : null}
            <div className="mt-3 space-y-3">
              {activeSubscriptions.slice(0, 4).map((subscription) => (
                <article key={subscription.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                      {subscription.product_name || 'Subscription'}
                    </h4>
                    <StatusPill value={subscription.status} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {subscription.price_summary
                      ? `${formatCurrencyFromCents(subscription.price_summary.amount_cents, subscription.price_summary.currency)} ${subscription.price_summary.billing_period}`
                      : 'No linked local price'}
                  </p>
                </article>
              ))}
            </div>
            <h4 className="mt-4 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">Current entitlements</h4>
            <div className="mt-2 flex flex-wrap gap-2">
              {entitlements
                .filter((entitlement) => entitlement.is_current)
                .slice(0, 8)
                .map((entitlement) => (
                  <span
                    className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    key={entitlement.id}
                  >
                    {entitlement.feature_key}
                  </span>
                ))}
              {entitlements.filter((entitlement) => entitlement.is_current).length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No active entitlements yet.</p>
              ) : null}
            </div>
          </article>

          <article className={cardClass}>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">AI provider and usage scaffold</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Built-in placeholders for OpenRouter and Ollama help you wire AI products with usage-aware subscription plans.
            </p>
            <div className="mt-3 space-y-2">
              {aiProviders.map((provider) => (
                <article key={provider.key} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{provider.label}</h4>
                      <p className="text-xs text-slate-600 dark:text-slate-300">{provider.base_url}</p>
                    </div>
                    <StatusPill value={provider.enabled ? 'configured' : 'disabled'} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{provider.env_vars.join(', ')}</p>
                </article>
              ))}
              {aiProviders.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No providers detected yet.</p>
              ) : null}
            </div>
            <div className="mt-3 space-y-2">
              {aiUsage.buckets.map((bucket) => (
                <UsageBar key={bucket.key} bucket={bucket} />
              ))}
              {aiUsage.buckets.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">No usage buckets configured yet.</p>
              ) : null}
            </div>
            {aiUsage.notes.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-600 dark:text-slate-300">
                {aiUsage.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
          </article>
        </div>
      </section>

      <section className={cn(sectionClass, 'space-y-4')}>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Developer context</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          API base: <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">{apiBase}</code>
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Refresh status: {refreshing ? 'updating now' : 'automatic on load and download actions'}
        </p>
        {user ? (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Signed in as {accountIdentityLabel}
          </p>
        ) : null}
      </section>
    </>
  );
}
