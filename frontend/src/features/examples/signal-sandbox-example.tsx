import { computed, signal } from '@preact/signals-react';
import { useSignals } from '@preact/signals-react/runtime';
import type { ReactElement } from 'react';

import { buttonGhost, buttonSecondary } from '../app-shell/ui-utils';

const launchCounterSignal = signal(1);
const launchCounterDoubleSignal = computed(() => launchCounterSignal.value * 2);
const launchCounterMomentumSignal = computed(() => {
  if (launchCounterSignal.value >= 8) {
    return 'high';
  }
  if (launchCounterSignal.value >= 4) {
    return 'building';
  }
  return 'starting';
});

function incrementLaunchCounterSignal(): void {
  launchCounterSignal.value += 1;
}

function resetLaunchCounterSignal(): void {
  launchCounterSignal.value = 1;
}

export function SignalSandboxExample(): ReactElement {
  useSignals();

  return (
    <article className="space-y-3 rounded-2xl border border-cyan-200 bg-cyan-50/80 p-6 dark:border-cyan-800 dark:bg-cyan-900/20">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-700 dark:text-cyan-200">Signals example</p>
      <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Signal counter sandbox</h3>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Keep this in the examples route so it does not distract from production UX while still showing reactive primitives.
      </p>
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-white px-2 py-1 dark:bg-slate-900">Launch Count: {launchCounterSignal.value}</span>
        <span className="rounded-full bg-white px-2 py-1 dark:bg-slate-900">Double: {launchCounterDoubleSignal.value}</span>
        <span className="rounded-full bg-white px-2 py-1 capitalize dark:bg-slate-900">
          Momentum: {launchCounterMomentumSignal.value}
        </span>
      </div>
      <div className="flex gap-2">
        <button type="button" className={buttonSecondary} onClick={incrementLaunchCounterSignal}>
          Push
        </button>
        <button type="button" className={buttonGhost} onClick={resetLaunchCounterSignal}>
          Reset
        </button>
      </div>
    </article>
  );
}
