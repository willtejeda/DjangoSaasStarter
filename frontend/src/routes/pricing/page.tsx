import { PricingTable } from '@clerk/clerk-react';
import type { ReactElement } from 'react';

import { PageIntro, TutorialBlock } from '../../components/layout/app-shell';
import { cardClass, cn, sectionClass } from '../../shared/ui-utils';
import type { PricingPageProps } from '../../shared/types';

export function PricingPage({ signedIn }: PricingPageProps): ReactElement {
  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Pricing"
        title="Live plans from Clerk Billing"
        description="No hardcoded frontend prices. Configure plans in Clerk and this page updates immediately."
      />
      <TutorialBlock
        whatThisDoes="Renders your active Clerk plans so buyers can start subscription checkout without manual frontend edits."
        howToTest={[
          'Create a plan in Clerk Billing',
          'Refresh this page and confirm it appears',
          'Run checkout and confirm webhook updates subscriptions',
        ]}
        expectedResult="Pricing is source-of-truth from Clerk and account subscription data stays in sync."
      />
      <div className={cardClass}>
        <PricingTable />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {signedIn
          ? 'Signed in users can manage plans from subscriptions and billing portal.'
          : 'Sign in first to subscribe and test billing flow.'}
      </p>
    </section>
  );
}
