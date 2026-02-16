import { useAuth } from '@clerk/clerk-react';
import type { ReactNode } from 'react';

export type Id = number | string;
export type NavigateFn = (nextPath: string) => void;
export type CheckoutStateValue = 'success' | 'cancel';
export type PlanTier = 'free' | 'pro' | 'enterprise';
export type GetTokenFn = ReturnType<typeof useAuth>['getToken'];

export interface ActivePrice {
  amount_cents: number;
  currency: string;
}

export interface ProductPrice {
  id: Id;
  name?: string | null;
  billing_period: string;
  amount_cents: number;
  currency: string;
}

export interface ProductAsset {
  id: Id;
  title: string;
}

export interface ServiceOffer {
  session_minutes: number;
  delivery_days: number;
  revision_count: number;
}

export interface ProductRecord {
  id: Id;
  slug: string;
  name: string;
  product_type: string;
  tagline?: string | null;
  description?: string | null;
  active_price?: ActivePrice | null;
  prices?: ProductPrice[];
  assets?: ProductAsset[];
  service_offer?: ServiceOffer | null;
}

export interface OrderRecord {
  public_id: string;
  status: string;
  total_cents: number;
  currency: string;
  items?: unknown[];
}

export interface OrderCreateResponse {
  checkout?: {
    checkout_url?: string | null;
  } | null;
  order?: {
    public_id?: string | null;
  } | null;
}

export interface PriceSummary {
  amount_cents: number;
  currency: string;
  billing_period: string;
}

export interface SubscriptionRecord {
  id: Id;
  product_name?: string | null;
  status: string;
  price_summary?: PriceSummary | null;
}

export interface DownloadGrant {
  token: string;
  asset_title: string;
  can_download: boolean;
  product_name: string;
  download_count: number;
  max_downloads: number;
}

export interface DownloadAccessResponse {
  download_url?: string | null;
}

export interface BookingRecord {
  id: Id;
  product_name?: string | null;
  status: string;
  customer_notes?: string | null;
}

export interface EntitlementRecord {
  id: Id;
  feature_key: string;
  is_current: boolean;
}

export interface MeResponse {
  customer_account?: {
    full_name?: string | null;
    metadata?: Record<string, unknown> | null;
  } | null;
  profile?: {
    plan_tier?: string | null;
    first_name?: string | null;
  } | null;
  billing_features?: string[] | null;
}

export interface BillingFeaturesResponse {
  enabled_features: string[];
}

export interface AiProviderRecord {
  key: string;
  label: string;
  kind: string;
  enabled: boolean;
  base_url: string;
  model_hint?: string | null;
  docs_url: string;
  env_vars: string[];
}

export interface AiUsageBucketRecord {
  key: string;
  label: string;
  used: number;
  limit: number | null;
  unit: string;
  reset_window: string;
  percent_used: number | null;
  near_limit: boolean;
}

export interface AiUsageSummaryResponse {
  period: string;
  plan_tier: string;
  buckets: AiUsageBucketRecord[];
  notes: string[];
}

export interface NavLinkProps {
  to: string;
  currentPath: string;
  onNavigate: NavigateFn;
  children: ReactNode;
}

export interface HeaderProps {
  pathname: string;
  onNavigate: NavigateFn;
  signedIn: boolean;
  expandedNav: boolean;
  themeLabel: string;
  onToggleTheme: () => void;
}

export interface PricingPageProps {
  signedIn: boolean;
}

export interface ProductCatalogProps {
  onNavigate: NavigateFn;
}

export interface ProductDetailProps {
  slug: string;
  signedIn: boolean;
  onNavigate: NavigateFn;
  getToken: GetTokenFn;
}

export interface TokenProps {
  getToken: GetTokenFn;
}

export interface TokenNavigateProps extends TokenProps {
  onNavigate: NavigateFn;
}

export interface CheckoutStateProps {
  state: CheckoutStateValue;
  onNavigate: NavigateFn;
}

export interface MetricCardProps {
  label: string;
  value: string;
  note: string;
}

export interface NavigateProps {
  onNavigate: NavigateFn;
}

export interface DashboardProps extends NavigateProps {
  getToken: GetTokenFn;
}

export interface PreflightEmailResponse {
  sent: boolean;
  detail: string;
  recipient_email?: string;
  sent_at?: string;
}

export interface SignedAppProps {
  pathname: string;
  onNavigate: NavigateFn;
  themeLabel: string;
  onToggleTheme: () => void;
}

export interface PageIntroProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

export interface TutorialBlockProps {
  whatThisDoes: string;
  howToTest: string[];
  expectedResult: string;
}
