import { render } from 'preact';
import { ClerkProvider } from '@clerk/clerk-react';

import { App } from './app';
import './styles.css';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

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

render(
  publishableKey ? (
    <ClerkProvider publishableKey={publishableKey}>
      <App />
    </ClerkProvider>
  ) : (
    <MissingConfig />
  ),
  document.getElementById('app')
);
