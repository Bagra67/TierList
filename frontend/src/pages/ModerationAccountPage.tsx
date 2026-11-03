import { type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';

import {
  type Account,
  type TemplateModerationAction,
  useAccount,
  useHideAllImages,
  useLiftBan,
  useModerateTemplate,
} from '../api/moderation';
import type { TemplateSummary } from '../api/templates';
import { BanAccountDialog } from '../components/BanAccountDialog';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ModerationLogTable } from '../components/ModerationLogTable';
import { ModerationReasonDialog } from '../components/ModerationReasonDialog';
import { TemplateHiddenBadge } from '../components/TemplateHiddenBadge';
import { UploadGrid } from '../components/UploadGrid';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { translateError } from '../errors/apiError';

export function ModerationAccountPage() {
  const { t } = useTranslation();
  const { accountId = '' } = useParams();
  const { data: account, isPending, isError, error } = useAccount(accountId);

  return (
    <div className="flex flex-col items-start gap-8">
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {account !== undefined && (
        <>
          <AccountDetails account={account} />
          <AccountBan account={account} />
          <AccountTemplates account={account} />
          <AccountImages account={account} />
          <section className="flex w-full flex-col items-start gap-3">
            <h2 className="text-lg font-semibold">{t('moderation.account.history')}</h2>
            <ModerationLogTable
              filters={{ accountId: account.id }}
              emptyMessage={t('moderation.account.noHistory')}
            />
          </section>
        </>
      )}
    </div>
  );
}

function AccountDetails({ account }: { account: Account }) {
  const { t } = useTranslation();
  const details: [string, string][] = [
    [t('moderation.account.email'), account.email],
    [
      t('moderation.account.createdAt'),
      t('moderation.account.date', { date: new Date(account.created_at) }),
    ],
    [
      t('moderation.account.emailVerified'),
      account.email_verified ? t('moderation.account.yes') : t('moderation.account.no'),
    ],
  ];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-semibold">{account.display_name}</h1>
        {account.role === 'super_admin' && (
          <span className="rounded-md border px-2 py-0.5 text-xs font-semibold">
            {t('moderation.accounts.superAdmin')}
          </span>
        )}
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {details.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function AccountBan({ account }: { account: Account }) {
  const { t } = useTranslation();
  const banDialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const liftDialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const liftMutation = useLiftBan();

  async function lift(reason: string): Promise<boolean> {
    try {
      await liftMutation.mutateAsync({ accountId: account.id, reason });
    } catch {
      return false;
    }
    return true;
  }

  if (account.role === 'super_admin') {
    return <p className="text-sm text-muted-foreground">{t('moderation.ban.superAdmin')}</p>;
  }
  const ban = account.ban;
  return (
    <section className="flex w-full flex-col items-start gap-3">
      <h2 className="text-lg font-semibold">{t('moderation.ban.section')}</h2>
      {ban === null ? (
        <>
          <p className="text-sm text-muted-foreground">{t('moderation.ban.none')}</p>
          <Button
            type="button"
            variant="destructive"
            onClick={() => banDialogRef.current?.showModal()}
          >
            {t('moderation.ban.open')}
          </Button>
        </>
      ) : (
        <div className="flex w-full flex-col items-start gap-2 rounded-lg border border-destructive/40 p-4 text-sm">
          <p className="font-semibold">
            {ban.ends_at === null
              ? t('moderation.ban.activePermanent')
              : t('moderation.ban.activeUntil', { date: new Date(ban.ends_at) })}
          </p>
          <p>{t('moderation.ban.activeReason', { reason: ban.reason })}</p>
          <p className="text-muted-foreground">
            {t('moderation.ban.activeBy', { name: ban.actor_name, date: new Date(ban.created_at) })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => liftDialogRef.current?.showModal()}
            >
              {t('moderation.ban.lift')}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => banDialogRef.current?.showModal()}
            >
              {t('moderation.ban.change')}
            </Button>
          </div>
        </div>
      )}
      <BanAccountDialog
        dialogRef={banDialogRef}
        accountId={account.id}
        displayName={account.display_name}
      />
      <ModerationReasonDialog
        dialogRef={liftDialogRef}
        title={t('moderation.liftDialog.title', { name: account.display_name })}
        description={t('moderation.liftDialog.description')}
        submitLabel={t('moderation.liftDialog.submit')}
        submittingLabel={t('moderation.liftDialog.submitting')}
        destructive={false}
        isPending={liftMutation.isPending}
        error={liftMutation.isError ? translateError(t, liftMutation.error) : null}
        onSubmit={lift}
        onClose={() => liftMutation.reset()}
      />
    </section>
  );
}

interface PendingTemplateAction {
  template: TemplateSummary;
  action: TemplateModerationAction;
}

function AccountTemplates({ account }: { account: Account }) {
  const { t } = useTranslation();
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState<PendingTemplateAction | null>(null);
  const moderateMutation = useModerateTemplate();
  const action: TemplateModerationAction = pending?.action ?? 'hide';

  function openDialog(template: TemplateSummary, templateAction: TemplateModerationAction) {
    setPending({ template, action: templateAction });
    dialogRef.current?.showModal();
  }

  async function moderate(reason: string): Promise<boolean> {
    if (pending === null) return false;
    try {
      await moderateMutation.mutateAsync({
        templateId: pending.template.id,
        action: pending.action,
        reason,
      });
    } catch {
      return false;
    }
    return true;
  }

  return (
    <section className="flex w-full flex-col items-start gap-3">
      <h2 className="text-lg font-semibold">{t('moderation.account.templates')}</h2>
      {account.templates.length === 0 ? (
        <EmptyState message={t('moderation.account.noTemplates')} />
      ) : (
        <ul className={panelVariants({ variant: 'list', className: 'w-full' })}>
          {account.templates.map((template: TemplateSummary) => {
            const actions: TemplateModerationAction[] =
              template.moderation === 'hidden' ? ['unhide', 'delete'] : ['hide', 'delete'];
            return (
              <li key={template.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="font-medium">{template.name}</span>
                <span className="text-sm text-muted-foreground">
                  {t('templates.tileCount', { count: template.tile_count })}
                </span>
                {template.moderation === 'hidden' && <TemplateHiddenBadge />}
                <div className="ml-auto flex gap-2">
                  {actions.map((templateAction: TemplateModerationAction) => (
                    <Button
                      key={templateAction}
                      type="button"
                      size="sm"
                      variant={templateAction === 'delete' ? 'destructive' : 'secondary'}
                      aria-label={t(`moderation.account.templateActionLabel.${templateAction}`, {
                        name: template.name,
                      })}
                      onClick={() => openDialog(template, templateAction)}
                    >
                      {t(`moderation.actions.${templateAction}`)}
                    </Button>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t(`moderation.templateDialog.${action}.title`, {
          name: pending?.template.name ?? '',
        })}
        description={t(`moderation.templateDialog.${action}.description`)}
        submitLabel={t(`moderation.templateDialog.${action}.submit`)}
        submittingLabel={t(`moderation.templateDialog.${action}.submitting`)}
        destructive={action === 'delete'}
        isPending={moderateMutation.isPending}
        error={moderateMutation.isError ? translateError(t, moderateMutation.error) : null}
        onSubmit={moderate}
        onClose={() => {
          moderateMutation.reset();
          setPending(null);
        }}
      />
    </section>
  );
}

function AccountImages({ account }: { account: Account }) {
  const { t } = useTranslation();
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const hideAllMutation = useHideAllImages();

  async function hideAll(reason: string): Promise<boolean> {
    try {
      await hideAllMutation.mutateAsync({ accountId: account.id, reason });
    } catch {
      return false;
    }
    return true;
  }

  return (
    <section className="flex w-full flex-col items-start gap-3">
      <div className="flex w-full flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{t('moderation.account.images')}</h2>
        <Button type="button" variant="secondary" onClick={() => dialogRef.current?.showModal()}>
          {t('moderation.account.hideAll')}
        </Button>
      </div>
      {hideAllMutation.isSuccess && (
        <p role="status" className="text-sm">
          {t('moderation.account.hiddenCount', { count: hideAllMutation.data })}
        </p>
      )}
      <UploadGrid
        filters={{ ownerId: account.id }}
        emptyMessage={t('moderation.account.noImages')}
      />
      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t('moderation.hideAllDialog.title', { name: account.display_name })}
        description={t('moderation.hideAllDialog.description')}
        submitLabel={t('moderation.hideAllDialog.submit')}
        submittingLabel={t('moderation.hideAllDialog.submitting')}
        destructive={false}
        isPending={hideAllMutation.isPending}
        error={hideAllMutation.isError ? translateError(t, hideAllMutation.error) : null}
        onSubmit={hideAll}
        onClose={() => {
          if (hideAllMutation.isError) hideAllMutation.reset();
        }}
      />
    </section>
  );
}
