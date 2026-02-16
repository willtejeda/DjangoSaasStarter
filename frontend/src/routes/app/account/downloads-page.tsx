import { useEffect, useState, type ReactElement } from 'react';

import { PageIntro, StatusPill, TutorialBlock } from '../../../components/layout/app-shell';
import { useToast } from '../../../components/feedback/toast';
import { authedRequest } from '../../../lib/api';
import type {
  DownloadAccessResponse,
  DownloadGrant,
  TokenNavigateProps,
} from '../../../shared/types';
import { buttonPrimary, cardClass, cn, sectionClass } from '../../../shared/ui-utils';

export function AccountDownloadsPage({ getToken, onNavigate }: TokenNavigateProps): ReactElement {
  const notify = useToast();
  const [grants, setGrants] = useState<DownloadGrant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [accessingToken, setAccessingToken] = useState('');

  const loadGrants = async (): Promise<void> => {
    setLoading(true);
    setError('');
    try {
      const payload = await authedRequest<DownloadGrant[]>(getToken, '/account/downloads/');
      setGrants(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not load downloads.';
      setError(detail);
      notify({ title: 'Download list failed', detail, variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGrants();
  }, []);

  const requestAccess = async (token: string): Promise<void> => {
    setAccessingToken(token);
    setError('');

    try {
      const payload = await authedRequest<DownloadAccessResponse>(getToken, `/account/downloads/${token}/access/`, {
        method: 'POST',
      });

      const downloadUrl = payload?.download_url || '';
      if (downloadUrl) {
        window.open(downloadUrl, '_blank', 'noopener');
      }
      notify({ title: 'Download link ready', detail: 'Signed URL generated for this asset.', variant: 'success' });
      await loadGrants();
    } catch (requestError) {
      const detail = requestError instanceof Error ? requestError.message : 'Could not generate download access.';
      setError(detail);
      notify({ title: 'Download generation failed', detail, variant: 'error' });
    } finally {
      setAccessingToken('');
    }
  };

  return (
    <section className={cn(sectionClass, 'space-y-6')}>
      <PageIntro
        eyebrow="Account"
        title="Downloads"
        description="Generate signed download links and track grant usage."
      />
      <TutorialBlock
        whatThisDoes="Lists digital delivery grants and creates temporary access links per asset."
        howToTest={[
          'Buy a digital product with attached asset',
          'Confirm grant appears as ready',
          'Generate link and verify usage count increments',
        ]}
        expectedResult="Eligible grants produce secure links and usage counters remain accurate."
      />

      {error ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600 dark:text-slate-300">Loading downloads...</p> : null}

      {!loading && grants.length === 0 ? (
        <article className={cardClass}>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">No digital deliveries yet</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Fulfillment grants appear after paid digital orders.
          </p>
          <button type="button" className={cn(buttonPrimary, 'mt-4')} onClick={() => onNavigate('/products')}>
            Browse Offers
          </button>
        </article>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {grants.map((grant) => (
          <article key={grant.token} className={cardClass}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{grant.asset_title}</h3>
              <StatusPill value={grant.can_download ? 'ready' : 'locked'} />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{grant.product_name}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {grant.download_count}/{grant.max_downloads} downloads used
            </p>
            <button
              type="button"
              className={cn(buttonPrimary, 'mt-4 w-full')}
              disabled={!grant.can_download || accessingToken === grant.token}
              onClick={() => requestAccess(grant.token)}
            >
              {accessingToken === grant.token ? 'Preparing...' : 'Get Download Link'}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
