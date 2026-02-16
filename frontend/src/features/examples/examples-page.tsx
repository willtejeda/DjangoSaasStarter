import type { ReactElement } from 'react';

import { FrontendBackendExamples } from './frontend-backend-examples';
import { SignalSandboxExample } from './signal-sandbox-example';
import { buttonSecondary, cardClass, sectionClass } from '../app-shell/ui-utils';

interface ExamplesPageProps {
  onNavigate: (nextPath: string) => void;
}

export function ExamplesPage({ onNavigate }: ExamplesPageProps): ReactElement {
  return (
    <section className={`${sectionClass} space-y-8`}>
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700 dark:text-cyan-300">Examples</p>
        <h1 className="max-w-4xl text-3xl font-black tracking-tight text-slate-900 dark:text-white sm:text-4xl">
          Starter examples you can keep, edit, or delete
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-300 sm:text-base">
          This route stores non-essential demos and snippets so production surfaces stay focused on monetization and stack validation.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonSecondary} onClick={() => onNavigate('/app')}>
            Open Dashboard
          </button>
          <button type="button" className={buttonSecondary} onClick={() => onNavigate('/products')}>
            Open Offers
          </button>
        </div>
      </header>

      <SignalSandboxExample />

      <FrontendBackendExamples />

      <article className={cardClass}>
        <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Email template scaffold</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          See backend email utilities in <code>backend/api/tools/email/resend.py</code> for Tailwind-like utility classes with Premailer CSS inlining.
        </p>
      </article>
    </section>
  );
}
