import { useAuth } from '@clerk/clerk-react';
import type { ReactElement, ReactNode } from 'react';

import type { SignedAppProps } from '../shared/types';
import { buttonSecondary, cn, sectionClass } from '../shared/ui-utils';
import { Header, PageIntro, Sidebar } from '../components/layout/app-shell';
import { ExamplesPage } from '../components/examples/examples-page';
import {
  CheckoutState,
  MarketingHome,
  PricingPage,
  ProductCatalog,
  ProductDetail,
} from './public/routes';
import {
  AccountDashboard,
  BookingsPage,
  DownloadsPage,
  PurchasesPage,
  SubscriptionsPage,
} from './app/routes';

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
        <div className="hidden border-r border-slate-200/90 bg-white/70 lg:block dark:border-slate-800 dark:bg-slate-950/40">
          <div className="sticky top-0 h-screen overflow-y-auto p-5">
            <Sidebar pathname={pathname} onNavigate={onNavigate} signedIn={signedIn} />
          </div>
        </div>
        <section className="min-w-0 px-4 pt-6 sm:px-6 lg:px-10 lg:pt-7 xl:px-12">
          <Header
            pathname={pathname}
            onNavigate={onNavigate}
            signedIn={signedIn}
            themeLabel={themeLabel}
            onToggleTheme={onToggleTheme}
          />
          <div className="mt-6 space-y-6">{content}</div>
        </section>
      </div>
    </main>
  );
}

export function SignedOutApp({ pathname, onNavigate, themeLabel, onToggleTheme }: SignedAppProps): ReactElement {
  const hiddenCatalogPath = pathname === '/pricing' || pathname === '/products' || pathname.startsWith('/products/');
  const normalizedPath = hiddenCatalogPath ? '/' : pathname;
  const content = pathname === '/examples' ? (
    <ExamplesPage onNavigate={onNavigate} />
  ) : hiddenCatalogPath ? (
    <>
      <section className={cn(sectionClass, 'border-amber-300 bg-amber-50/70 dark:border-amber-700 dark:bg-amber-900/20')}>
        <PageIntro
          eyebrow="Template preview"
          title="Catalog and pricing are locked while signed out"
          description="Sign in to configure offers and verify checkout plus fulfillment from account routes."
        />
      </section>
      <MarketingHome />
    </>
  ) : (
    <MarketingHome />
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
    content = <ProductCatalog onNavigate={onNavigate} />;
  } else if (pathname === '/examples') {
    content = <ExamplesPage onNavigate={onNavigate} />;
  } else if (isProductDetail && productSlug) {
    content = <ProductDetail slug={productSlug} signedIn onNavigate={onNavigate} getToken={getToken} />;
  } else if (pathname === '/account/purchases') {
    content = <PurchasesPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/subscriptions') {
    content = <SubscriptionsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/downloads') {
    content = <DownloadsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/account/bookings') {
    content = <BookingsPage getToken={getToken} onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/success') {
    content = <CheckoutState state="success" onNavigate={onNavigate} />;
  } else if (pathname === '/checkout/cancel') {
    content = <CheckoutState state="cancel" onNavigate={onNavigate} />;
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
