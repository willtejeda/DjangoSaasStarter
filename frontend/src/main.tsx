import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';

import { App } from './app';
import './styles.css';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const rootElement = document.getElementById('app');

if (!rootElement) {
  throw new Error('Root element #app was not found.');
}

function MissingConfig() {
  return (
    <main className="shell centered">
      <section className="panel warning-panel">
        <h1>Missing Clerk config</h1>
        <p>
          Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> in <code>frontend/.env</code> and restart the dev server.
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
