import { type FormEvent, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  type ModerationLogEntry,
  type ModerationLogFilters,
  type SuperAdmin,
  useModerationLog,
  useSuperAdmins,
} from '../api/moderation';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';
import { translateError } from '../errors/apiError';

// Journal de modération (US-1.9) : chaque action d'un super admin, de la plus récente à la plus
// ancienne, filtrable par cible et par super admin. Rien ne s'y modifie ni ne s'y supprime
export function ModerationLogPage() {
  const { t } = useTranslation();
  const superAdminSelectId = useId();
  // Le texte cherché n'est appliqué qu'à l'envoi du formulaire : une requête par recherche, pas
  // une par lettre tapée
  const [targetDraft, setTargetDraft] = useState('');
  const [filters, setFilters] = useState<ModerationLogFilters>({});
  const superAdmins = useSuperAdmins();
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useModerationLog(filters);
  const entries: ModerationLogEntry[] = data?.pages.flatMap((page) => page.entries) ?? [];
  const isFiltered = filters.actorId !== undefined || filters.target !== undefined;

  function applyTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = targetDraft.trim();
    setFilters({ ...filters, target: target === '' ? undefined : target });
  }

  function applyActor(actorId: string) {
    setFilters({ ...filters, actorId: actorId === '' ? undefined : actorId });
  }

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.log.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.log.intro')}</p>
      </div>

      <form onSubmit={applyTarget} className="flex flex-wrap items-end gap-3">
        <TextField
          label={t('moderation.log.target')}
          name="target"
          placeholder={t('moderation.log.targetPlaceholder')}
          value={targetDraft}
          onChange={(event) => setTargetDraft(event.target.value)}
        />
        <Button type="submit" variant="outline">
          {t('moderation.log.search')}
        </Button>
        <div className="flex flex-col gap-2">
          <Label htmlFor={superAdminSelectId}>{t('moderation.log.superAdmin')}</Label>
          <NativeSelect
            id={superAdminSelectId}
            value={filters.actorId ?? ''}
            onChange={(event) => applyActor(event.target.value)}
          >
            <option value="">{t('moderation.log.allSuperAdmins')}</option>
            {superAdmins.data?.map((superAdmin: SuperAdmin) => (
              <option key={superAdmin.id} value={superAdmin.id}>
                {superAdmin.display_name}
              </option>
            ))}
          </NativeSelect>
        </div>
      </form>

      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && entries.length === 0 && (
        <EmptyState
          message={isFiltered ? t('moderation.log.emptyFiltered') : t('moderation.log.empty')}
        />
      )}
      {entries.length > 0 && (
        // Le tableau défile seul sur un petit écran, pas la page
        <div className="w-full overflow-x-auto rounded-panel border bg-card">
          <table className="w-full text-sm">
            <caption className="sr-only">{t('moderation.log.title')}</caption>
            <thead>
              <tr className="border-b bg-muted/50 text-left">
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.at')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.actor')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.action')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.target')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.reason')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {entries.map((entry: ModerationLogEntry) => (
                <tr key={entry.id} className="align-top">
                  <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                    {t('moderation.log.at', { date: new Date(entry.created_at) })}
                  </td>
                  <td className="px-3 py-2">{entry.actor_name}</td>
                  <td className="px-3 py-2">{t(`moderation.actions.${entry.action}`)}</td>
                  <td className="px-3 py-2">
                    {t('moderation.log.targetCell', {
                      type: t(`moderation.targets.${entry.target_type}`),
                      label: entry.target_label,
                    })}
                  </td>
                  <td className="px-3 py-2">{entry.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {hasNextPage && (
        <Button
          type="button"
          variant="outline"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          {isFetchingNextPage ? t('common.loading') : t('moderation.log.more')}
        </Button>
      )}
    </div>
  );
}
