import { CircleAlert } from 'lucide-react';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from 'cn';

import { useCurrentUser } from '../api/auth';
import {
  type Template,
  type TemplateChange,
  type TemplateVisibility,
  useSetTemplateVisibility,
} from '../api/templates';
import { ApiError, translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { ResendVerificationEmailButton } from './ResendVerificationEmailButton';

const EMAIL_NOT_VERIFIED_CODE: string = 'email_not_verified';
const VISIBILITIES: readonly TemplateVisibility[] = ['private', 'public'];

function isEmailNotVerified(error: Error | null): boolean {
  return error instanceof ApiError && error.code === EMAIL_NOT_VERIFIED_CODE;
}

interface TemplateVisibilityFieldProps {
  template: Template;
}

export function TemplateVisibilityField({ template }: TemplateVisibilityFieldProps) {
  const { t } = useTranslation();
  const { data: user, refetch: refetchUser } = useCurrentUser({ refreshUntilEmailVerified: true });
  const visibilityMutation: TemplateChange<TemplateVisibility> = useSetTemplateVisibility(
    template.id,
  );
  const fieldId: string = useId();
  const publicHintId: string = `${fieldId}-public-hint`;
  const emailNoticeId: string = `${fieldId}-email-notice`;

  const isPublic: boolean = template.visibility === 'public';
  const isHidden: boolean = template.moderation === 'hidden';
  const emailCachedAsVerified: boolean = user?.email_verified ?? false;
  const emailRefused: boolean = isEmailNotVerified(visibilityMutation.error);
  const publicBlockedHint: string | null = isPublic ? null : publicBlockedReason();
  const showsEmailNotice: boolean =
    !isPublic && publicBlockedHint === null && !emailCachedAsVerified;

  function publicBlockedReason(): string | null {
    if (isHidden) return t('templates.visibility.hiddenCannotBePublic');
    if (template.tiles.length === 0) return t('templates.visibility.needsTiles');
    return null;
  }

  function choose(visibility: TemplateVisibility) {
    visibilityMutation.mutate(visibility, {
      onSuccess: () => {
        if (!emailCachedAsVerified) void refetchUser();
      },
      onError: (error: Error) => {
        if (emailCachedAsVerified && isEmailNotVerified(error)) void refetchUser();
      },
    });
  }

  function descriptionId(visibility: TemplateVisibility): string {
    return `${fieldId}-${visibility}-description`;
  }

  function describedBy(visibility: TemplateVisibility): string {
    if (visibility === 'private') return descriptionId(visibility);
    if (publicBlockedHint !== null) return `${descriptionId(visibility)} ${publicHintId}`;
    if (showsEmailNotice) return `${descriptionId(visibility)} ${emailNoticeId}`;
    return descriptionId(visibility);
  }

  return (
    <fieldset className="flex min-w-0 flex-col gap-1.5">
      <legend className="mb-1 text-sm leading-none font-medium">
        {t('templates.visibility.legend')}
      </legend>
      <div className="flex flex-wrap gap-2">
        {VISIBILITIES.map((visibility) => {
          const isBlocked: boolean = visibility === 'public' && publicBlockedHint !== null;
          const optionId: string = `${fieldId}-${visibility}`;
          return (
            <label
              key={visibility}
              htmlFor={optionId}
              className={cn(
                'flex h-9 items-center gap-2 rounded-lg border-2 bg-card px-3 text-sm font-medium',
                'has-checked:border-foreground',
                isBlocked ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
              )}
            >
              <input
                id={optionId}
                type="radio"
                name={fieldId}
                value={visibility}
                checked={template.visibility === visibility}
                disabled={isBlocked}
                aria-describedby={describedBy(visibility)}
                onChange={() => choose(visibility)}
                className="size-4 shrink-0 accent-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              />
              {t(`templates.visibility.${visibility}.label`)}
            </label>
          );
        })}
      </div>
      <p className="text-sm text-muted-foreground">
        {VISIBILITIES.map((visibility) => (
          <span
            key={visibility}
            id={descriptionId(visibility)}
            className={cn(template.visibility !== visibility && 'sr-only')}
          >
            {t(`templates.visibility.${visibility}.description`)}
          </span>
        ))}
        {isPublic && !isHidden && template.first_made_public_at !== null && (
          <>
            {' '}
            <time dateTime={template.first_made_public_at}>
              {t('templates.visibility.firstMadePublicAt', {
                date: new Date(template.first_made_public_at),
              })}
            </time>
          </>
        )}
      </p>
      {isPublic && isHidden && (
        <p className="text-sm">{t('templates.visibility.hiddenWhilePublic')}</p>
      )}
      {publicBlockedHint !== null && (
        <p id={publicHintId} className="text-sm text-muted-foreground">
          {publicBlockedHint}
        </p>
      )}
      {showsEmailNotice && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-l-2 border-warning pl-2 text-sm">
          <p id={emailNoticeId} className="flex items-center gap-1.5">
            <CircleAlert aria-hidden="true" className="size-4 shrink-0" />
            {t('templates.visibility.emailNotVerified')}
          </p>
          <ResendVerificationEmailButton size="xs" />
        </div>
      )}
      {visibilityMutation.isError && !emailRefused && (
        <ErrorMessage>{translateError(t, visibilityMutation.error)}</ErrorMessage>
      )}
    </fieldset>
  );
}
