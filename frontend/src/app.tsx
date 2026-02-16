import {
  SignedIn,
  SignedOut,
} from '@clerk/clerk-react';
import { useSignalEffect } from '@preact/signals-react';
import { useSignals } from '@preact/signals-react/runtime';
import { type ReactElement } from 'react';

import {
  THEME_STORAGE_KEY,
  nextThemeLabelSignal,
  themeSignal,
  toggleThemeSignal,
} from './lib/signals';
import { ToastProvider } from './components/feedback/toast';
import { usePathname } from './components/layout/app-shell';
import { SignedInApp, SignedOutApp } from './routes';

export function App(): ReactElement {
  useSignals();

  const { pathname, navigate } = usePathname();

  useSignalEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const themeValue = themeSignal.value;
    document.documentElement.classList.toggle('dark', themeValue === 'dark');
    document.documentElement.dataset.theme = themeValue;
    window.localStorage.setItem(THEME_STORAGE_KEY, themeValue);
  });

  const themeLabel = nextThemeLabelSignal.value;

  return (
    <ToastProvider>
      <SignedOut>
        <SignedOutApp
          pathname={pathname}
          onNavigate={navigate}
          themeLabel={themeLabel}
          onToggleTheme={toggleThemeSignal}
        />
      </SignedOut>
      <SignedIn>
        <SignedInApp
          pathname={pathname}
          onNavigate={navigate}
          themeLabel={themeLabel}
          onToggleTheme={toggleThemeSignal}
        />
      </SignedIn>
    </ToastProvider>
  );
}
