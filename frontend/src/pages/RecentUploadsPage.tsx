import { type FormEvent, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type ListedImageStatus, type RecentUploadsFilters } from '../api/moderation';
import { DayRangeFields } from '../components/DayRangeFields';
import {
  type DayRange,
  type DayRangeBounds,
  dayRangeBounds,
  EMPTY_DAY_RANGE,
  isDayRangeSet,
} from '../components/localDays';
import { TextField } from '../components/TextField';
import { UploadGrid } from '../components/UploadGrid';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';
import { useDocumentTitle } from '../components/useDocumentTitle';

export function RecentUploadsPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('moderation.uploads.title'));
  const statusId: string = useId();
  const [authorDraft, setAuthorDraft] = useState<string>('');
  const [author, setAuthor] = useState<string | undefined>(undefined);
  const [days, setDays] = useState<DayRange>(EMPTY_DAY_RANGE);
  const [status, setStatus] = useState<ListedImageStatus | ''>('');
  const bounds: DayRangeBounds = dayRangeBounds(days);
  const filters: RecentUploadsFilters = {
    author,
    createdAfter: bounds.after,
    createdBefore: bounds.before,
    status: status === '' ? undefined : status,
  };
  const isFiltered: boolean = author !== undefined || isDayRangeSet(days) || status !== '';
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
        <DayRangeFields
          range={days}
          onChange={setDays}
          fromLabel={t('moderation.uploads.from')}
          toLabel={t('moderation.uploads.to')}
        />
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
