import type { ReactElement } from 'react';

import { PageIntro, TutorialBlock } from '../../components/layout/app-shell';
import type { CheckoutStateProps } from '../../shared/types';
import { buttonPrimary, buttonSecondary, cn, sectionClass } from '../../shared/ui-utils';

export function CheckoutStatePage({ state, onNavigate }: CheckoutStateProps): ReactElement {
  const isSuccess = state === 'success';
  return (
    <section
      className={cn(
        sectionClass,
        'space-y-6',
        isSuccess
          ? 'border-emerald-300 bg-emerald-50/60 dark:border-emerald-700 dark:bg-emerald-900/10'
          : 'border-rose-300 bg-rose-50/60 dark:border-rose-700 dark:bg-rose-900/10'
      )}
    >
      <PageIntro
        eyebrow="Checkout"
        title={isSuccess ? 'Checkout Successful' : 'Checkout Canceled'}
        description={
          isSuccess
            ? 'Payment completed. Fulfillment is now available in your account routes.'
            : 'No charge was made. Return to offers and retry checkout when ready.'
        }
      />
      <TutorialBlock
        whatThisDoes="Confirms checkout outcome and routes users to the next high-value step."
        howToTest={[
          'Complete checkout once for success route',
          'Cancel checkout once for cancel route',
          'Follow CTA and verify downstream pages match state',
        ]}
        expectedResult="Users always land on a clear next action after checkout."
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" className={buttonPrimary} onClick={() => onNavigate('/account/purchases')}>
          View Purchases
        </button>
        <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
          Browse Offers
        </button>
      </div>
    </section>
  );
}
