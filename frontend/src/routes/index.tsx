import { useAuth } from '@clerk/clerk-react';
import type { ReactElement, ReactNode } from 'react';

import type { SignedAppProps } from '../shared/types';
import { buttonSecondary, cn, sectionClass } from '../shared/ui-utils';
import { PageIntro, PrimaryNavigation } from '../components/layout/app-shell';
import { ExamplesRoutePage } from './examples';
import { LandingPage } from './landing';
import { PricingPage } from './pricing';
import { ProductCatalogPage, ProductDetailPage } from './products';
import { CheckoutStatePage } from './checkout';
import { AccountDashboard } from './app/dashboard';
import {
  AccountBookingsPage,
  AccountDownloadsPage,
  AccountPurchasesPage,
  AccountSubscriptionsPage,
} from './app/account';

function AppFrame({
  pathname,
  onNavigate,
  signedIn,
  themeLabel,
  onToggleTheme,
  content,
}: SignedAppProps & { signedIn: boolean; content: ReactNode }): ReactElement {
  return (
    <main className="w-full pb-20 lg:pb-24">
      <div className="lg:grid lg:min-h-screen lg:grid-cols-[280px,minmax(0,1fr)]">
        <PrimaryNavigation
          pathname={pathname}
          onNavigate={onNavigate}
          signedIn={signedIn}
          themeLabel={themeLabel}
          onToggleTheme={onToggleTheme}
        />
        <section className="min-w-0 px-4 pt-20 sm:px-6 lg:px-10 lg:pt-7 xl:px-12">
          <div className="space-y-6">{content}</div>
        </section>
      </div>
    </main>
  );
}

export function SignedOutApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const hiddenCatalogPath = pathname === '/pricing' || pathname === '/products' || pathname.startsWith('/products/');
  const normalizedPath = hiddenCatalogPath ? '/' : pathname;
  const content = pathname === '/examples' ? (
    <ExamplesRoutePage onNavigate={onNavigate} />
  ) : hiddenCatalogPath ? (
    <>
      <section className={cn(sectionClass, 'border-amber-300 bg-amber-50/70 dark:border-amber-700 dark:bg-amber-900/20')}>
        <PageIntro
          eyebrow="Template preview"
          title="Catalog and pricing are locked while signed out"
          description="Sign in to configure offers and verify checkout plus fulfillment from account routes."
        />
      </section>
      <LandingPage />
    </>
  ) : (
    <LandingPage />
  );

  return (
    <AppFrame
      pathname={normalizedPath}
      onNavigate={onNavigate}
      signedIn={false}
      themeLabel={themeLabel}
      onToggleTheme={onToggleTheme}
      content={content}
    />
  );
}

export function SignedInApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const { getToken } = useAuth();
  const isProductDetail = pathname.startsWith('/products/');
  const productSlug = isProductDetail ? pathname.replace('/products/', '') : '';
  let content: ReactNode = <AccountDashboard onNavigate={onNavigate} getToken={getToken} />;

  if (pathname === '/pricing') {
    content = <PricingPage signedIn />;
  } else if (pathname === '/products') {
    content = <ProductCatalogPage onNavigate={onNavigate} />;
  } else if (pathname === '/examples') {
    content = <ExamplesRoutePage onNavigate={onNavigate} />;
  } else if (isProductDetail && productSlug) {
    content = <ProductDetailPage slug={productSlug} signedIn onNavigate={onNavigate} getToken={getToken} />;
  } else if (pathname === '/account/purchases') {
    content = <AccountPurchasesPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/subscriptions') {
    content = <AccountSubscriptionsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/downloads') {
    content = <AccountDownloadsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/bookings') {
    content = <AccountBookingsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/success') {
    content = <CheckoutStatePage state="success" onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/cancel') {
    content = <CheckoutStatePage state="cancel" onNavigate={onNavigate} />;
  } else if (pathname !== '/' && pathname !== '/app') {
    content = (
      <section className={sectionClass}>
        <PageIntro
          eyebrow="404"
          title="Page not found"
          description="This route is not part of the current app map."
          actions={
            <button type="button" className={buttonSecondary} onClick={() => onNavigate('/app')}>
              Back to Dashboard
            </button>
          }
        />
      </section>
    );
  }

  return (
    <AppFrame
      pathname={pathname}
      onNavigate={onNavigate}
      signedIn
      themeLabel={themeLabel}
      onToggleTheme={onToggleTheme}
      content={content}
    />
  );
}
