import { type FormEvent, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type ModerationLogFilters, type SuperAdmin, useSuperAdmins } from '../api/moderation';
import { ModerationLogTable } from '../components/ModerationLogTable';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';

export function ModerationLogPage() {
  const { t } = useTranslation();
  const superAdminSelectId = useId();
  const [targetDraft, setTargetDraft] = useState('');
  const [filters, setFilters] = useState<ModerationLogFilters>({});
  const superAdmins = useSuperAdmins();
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

      <ModerationLogTable
        filters={filters}
        emptyMessage={isFiltered ? t('moderation.log.emptyFiltered') : t('moderation.log.empty')}
      />
    </div>
  );
}
