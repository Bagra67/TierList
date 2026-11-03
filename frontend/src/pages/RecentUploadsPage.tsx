import { type FormEvent, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type ListedImageStatus, type RecentUploadsFilters } from '../api/moderation';
import { startOfDay, startOfNextDay } from '../components/localDays';
import { TextField } from '../components/TextField';
import { UploadGrid } from '../components/UploadGrid';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';

export function RecentUploadsPage() {
  const { t } = useTranslation();
  const fromId: string = useId();
  const toId: string = useId();
  const statusId: string = useId();
  const [authorDraft, setAuthorDraft] = useState<string>('');
  const [author, setAuthor] = useState<string | undefined>(undefined);
  const [fromDay, setFromDay] = useState<string>('');
  const [toDay, setToDay] = useState<string>('');
  const [status, setStatus] = useState<ListedImageStatus | ''>('');
  const filters: RecentUploadsFilters = {
    author,
    createdAfter: fromDay === '' ? undefined : startOfDay(fromDay),
    createdBefore: toDay === '' ? undefined : startOfNextDay(toDay),
    status: status === '' ? undefined : status,
  };
  const isFiltered: boolean =
    author !== undefined || fromDay !== '' || toDay !== '' || status !== '';
  function applyAuthor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const searched: string = authorDraft.trim();
    setAuthor(searched === '' ? undefined : searched);
  }

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.uploads.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.uploads.intro')}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={applyAuthor} className="flex flex-wrap items-end gap-3">
          <TextField
            label={t('moderation.uploads.author')}
            name="author"
            placeholder={t('moderation.uploads.authorPlaceholder')}
            value={authorDraft}
            onChange={(event) => setAuthorDraft(event.target.value)}
          />
          <Button type="submit" variant="outline">
            {t('moderation.uploads.search')}
          </Button>
        </form>
        <div className="flex flex-col gap-2">
          <Label htmlFor={fromId}>{t('moderation.uploads.from')}</Label>
          <Input
            id={fromId}
            type="date"
            value={fromDay}
            max={toDay === '' ? undefined : toDay}
            onChange={(event) => setFromDay(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={toId}>{t('moderation.uploads.to')}</Label>
          <Input
            id={toId}
            type="date"
            value={toDay}
            min={fromDay === '' ? undefined : fromDay}
            onChange={(event) => setToDay(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={statusId}>{t('moderation.uploads.status')}</Label>
          <NativeSelect
            id={statusId}
            value={status}
            onChange={(event) => setStatus(event.target.value as ListedImageStatus | '')}
          >
            <option value="">{t('moderation.uploads.allStatuses')}</option>
            <option value="visible">{t('moderation.uploads.visible')}</option>
            <option value="hidden">{t('moderation.uploads.hidden')}</option>
          </NativeSelect>
        </div>
      </div>

      <UploadGrid
        filters={filters}
        emptyMessage={
          isFiltered ? t('moderation.uploads.emptyFiltered') : t('moderation.uploads.empty')
        }
      />
    </div>
  );
}
