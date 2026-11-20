import { cn } from 'cn';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import {
  type DeletedTemplate,
  type DeletedTemplateAction,
  type DeletedTemplatesFilters,
  useDeletedTemplates,
} from '../api/moderation';
import { DayRangeFields } from '../components/DayRangeFields';
import { DeletionDetails } from '../components/DeletionDetails';
import { EmptyState } from '../components/EmptyState';
import { eraseCountdown, isEraseUrgent } from '../components/eraseCountdown';
import {
  type DayRange,
  type DayRangeBounds,
  dayRangeBounds,
  EMPTY_DAY_RANGE,
  isDayRangeSet,
} from '../components/localDays';
import { PagedList } from '../components/PagedList';
import {
  type TemplateModerationDialog,
  useTemplateModerationDialog,
} from '../components/TemplateModerationDialog';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { textLinkClassName } from '../components/ui/text-link';
import { useDocumentTitle } from '../components/useDocumentTitle';
import { moderationAccountPath, moderationTemplatePath } from '../constants/routes';

function optionalText(value: string): string | undefined {
  const trimmed: string = value.trim();
  return trimmed === '' ? undefined : trimmed;
}

export function ModerationDeletedTemplatesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('moderation.deletedTemplates.title'));
  const [ownerDraft, setOwnerDraft] = useState<string>('');
  const [nameDraft, setNameDraft] = useState<string>('');
  const [owner, setOwner] = useState<string | undefined>(undefined);
  const [name, setName] = useState<string | undefined>(undefined);
  const [days, setDays] = useState<DayRange>(EMPTY_DAY_RANGE);
  const bounds: DayRangeBounds = dayRangeBounds(days);
  const filters: DeletedTemplatesFilters = {
    owner,
    name,
    deletedAfter: bounds.after,
    deletedBefore: bounds.before,
  };
  const isFiltered: boolean = owner !== undefined || name !== undefined || isDayRangeSet(days);

  function applyText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOwner(optionalText(ownerDraft));
    setName(optionalText(nameDraft));
  }

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.deletedTemplates.title')}</h1>
        <p className="max-w-prose text-muted-foreground">
          {t('moderation.deletedTemplates.intro')}
        </p>
      </div>

      <div className="flex w-full flex-wrap items-end gap-3">
        <form onSubmit={applyText} className="flex w-full flex-wrap items-end gap-3 sm:w-auto">
          <TextField
            label={t('moderation.deletedTemplates.owner')}
            name="owner"
            placeholder={t('moderation.deletedTemplates.ownerPlaceholder')}
            value={ownerDraft}
            onChange={(event) => setOwnerDraft(event.target.value)}
          />
          <TextField
            label={t('moderation.deletedTemplates.name')}
            name="name"
            placeholder={t('moderation.deletedTemplates.namePlaceholder')}
            value={nameDraft}
            onChange={(event) => setNameDraft(event.target.value)}
          />
          <Button type="submit" variant="outline">
            {t('moderation.deletedTemplates.search')}
          </Button>
        </form>
        <DayRangeFields
          range={days}
          onChange={setDays}
          fromLabel={t('moderation.deletedTemplates.from')}
          toLabel={t('moderation.deletedTemplates.to')}
        />
      </div>

      <DeletedTemplateList
        filters={filters}
        emptyMessage={
          isFiltered
            ? t('moderation.deletedTemplates.emptyFiltered')
            : t('moderation.deletedTemplates.empty')
        }
      />
    </div>
  );
}

interface DeletedTemplateListProps {
  filters: DeletedTemplatesFilters;
  emptyMessage: string;
}

function DeletedTemplateList({ filters, emptyMessage }: DeletedTemplateListProps) {
  const { t } = useTranslation();
  const query = useDeletedTemplates(filters);
  const templates: DeletedTemplate[] = query.data?.pages.flatMap((page) => page.templates) ?? [];
  const moderation: TemplateModerationDialog = useTemplateModerationDialog();

  return (
    <>
      <PagedList
        query={query}
        itemCount={templates.length}
        empty={<EmptyState message={emptyMessage} />}
        moreLabel={t('moderation.deletedTemplates.more')}
      >
        <ul className={panelVariants({ variant: 'list', className: 'w-full' })}>
          {templates.map((template: DeletedTemplate) => (
            <DeletedTemplateRow
              key={template.id}
              template={template}
              onAction={(action: DeletedTemplateAction) =>
                moderation.open(template.id, template.name, action)
              }
            />
          ))}
        </ul>
      </PagedList>

      {moderation.dialog}
    </>
  );
}

interface DeletedTemplateRowProps {
  template: DeletedTemplate;
  onAction: (action: DeletedTemplateAction) => void;
}

function DeletedTemplateRow({ template, onAction }: DeletedTemplateRowProps) {
  const { t } = useTranslation();
  const urgent: boolean = isEraseUrgent(template.erase_at);
  return (
    <li
      className={cn(
        'grid gap-x-4 gap-y-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto]',
        urgent && 'bg-warning/10 shadow-[inset_4px_0_0_var(--warning)]',
      )}
    >
      <div className="flex min-w-0 flex-col gap-1">
        <Link
          to={moderationTemplatePath(template.id)}
          className={cn(textLinkClassName, 'font-medium break-words')}
        >
          {template.name}
        </Link>
        <p className="text-sm text-muted-foreground">
          <Link to={moderationAccountPath(template.owner_id)} className={textLinkClassName}>
            {template.owner_name}
          </Link>
          {' · '}
          {t('moderation.deletedTemplates.tileCount', { count: template.tile_count })}
        </p>
        <DeletionDetails
          deletedAt={template.deleted_at}
          deletionReason={template.deletion_reason}
        />
      </div>
      <div className="flex flex-col gap-2 sm:items-end">
        <time
          dateTime={template.erase_at}
          title={t('moderation.deletedTemplates.eraseAt', { date: new Date(template.erase_at) })}
          className={cn('text-sm tabular-nums', urgent ? 'font-bold' : 'font-medium')}
        >
          {eraseCountdown(t, template.erase_at)}
        </time>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="outline" onClick={() => onAction('restore')}>
            {t('moderation.actions.restore')}
          </Button>
          <Button type="button" size="sm" variant="destructive" onClick={() => onAction('purge')}>
            {t('moderation.actions.purge')}
          </Button>
        </div>
      </div>
    </li>
  );
}
