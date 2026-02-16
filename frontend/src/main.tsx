import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';

import { App } from './app';
import './globals.css';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const rootElement = document.getElementById('app');

if (!rootElement) {
  throw new Error('Root element #app was not found.');
}

function MissingConfig() {
  return (
    <main className="mx-auto grid w-full max-w-3xl gap-6 px-4 pb-16 pt-10 sm:px-6">
      <section className="rounded-2xl border border-rose-300 bg-rose-50 p-6 dark:border-rose-700 dark:bg-rose-900/20">
        <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Missing Clerk config</h1>
        <p className="mt-3 text-sm text-slate-700 dark:text-slate-200">
          Set <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">VITE_CLERK_PUBLISHABLE_KEY</code>{' '}
          in <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">frontend/.env</code> and restart the dev server.
        </p>
      </section>
    </main>
  );
}

createRoot(rootElement).render(
  <StrictMode>
    {publishableKey ? (
      <ClerkProvider publishableKey={publishableKey}>
        <App />
      </ClerkProvider>
    ) : (
      <MissingConfig />
    )}
  </StrictMode>
);
