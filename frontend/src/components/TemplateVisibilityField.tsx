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

interface TemplateVisibilityFieldProps {
  template: Template;
}

export function TemplateVisibilityField({ template }: TemplateVisibilityFieldProps) {
  const { t } = useTranslation();
  const { data: user, refetch: refetchUser } = useCurrentUser();
  const visibilityMutation: TemplateChange<TemplateVisibility> = useSetTemplateVisibility(
    template.id,
  );
  const fieldId: string = useId();
  const publicHintId: string = `${fieldId}-public-hint`;
  const emailNoticeId: string = `${fieldId}-email-notice`;

  const isPublic: boolean = template.visibility === 'public';
  const isHidden: boolean = template.moderation === 'hidden';
  const emailCachedAsVerified: boolean = user?.email_verified ?? false;
  const emailRefused: boolean =
    visibilityMutation.error instanceof ApiError &&
    visibilityMutation.error.code === EMAIL_NOT_VERIFIED_CODE;
  const publicBlockedHint: string | null = isPublic ? null : publicBlockedReason();
  const showsEmailNotice: boolean =
    !isPublic && publicBlockedHint === null && (!emailCachedAsVerified || emailRefused);

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
    });
  }

  function describedBy(visibility: TemplateVisibility): string {
    const descriptionId: string = `${fieldId}-${visibility}-description`;
    if (visibility === 'private') return descriptionId;
    if (publicBlockedHint !== null) return `${descriptionId} ${publicHintId}`;
    if (showsEmailNotice) return `${descriptionId} ${emailNoticeId}`;
    return descriptionId;
  }

  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-1 text-sm leading-none font-medium">
        {t('templates.visibility.legend')}
      </legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {VISIBILITIES.map((visibility) => {
          const isBlocked: boolean = visibility === 'public' && publicBlockedHint !== null;
          const optionId: string = `${fieldId}-${visibility}`;
          return (
            <label
              key={visibility}
              htmlFor={optionId}
              className={cn(
                'flex items-start gap-3 rounded-lg border-2 bg-card p-3',
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
                aria-labelledby={`${optionId}-label`}
                aria-describedby={describedBy(visibility)}
                onChange={() => choose(visibility)}
                className="mt-0.5 size-4 shrink-0 accent-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              />
              <span className="flex flex-col gap-0.5 text-sm font-medium">
                <span id={`${optionId}-label`}>
                  {t(`templates.visibility.${visibility}.label`)}
                </span>
                <span
                  id={`${fieldId}-${visibility}-description`}
                  className="font-normal text-muted-foreground"
                >
                  {t(`templates.visibility.${visibility}.description`)}
                </span>
              </span>
            </label>
          );
        })}
      </div>
      {isPublic && isHidden && (
        <p className="text-sm">{t('templates.visibility.hiddenWhilePublic')}</p>
      )}
      {isPublic && !isHidden && template.first_made_public_at !== null && (
        <p className="text-sm text-muted-foreground">
          <time dateTime={template.first_made_public_at}>
            {t('templates.visibility.firstMadePublicAt', {
              date: new Date(template.first_made_public_at),
            })}
          </time>
        </p>
      )}
      {publicBlockedHint !== null && (
        <p id={publicHintId} className="text-sm text-muted-foreground">
          {publicBlockedHint}
        </p>
      )}
      {showsEmailNotice && (
        <div className="flex flex-col gap-2 rounded-lg border border-warning bg-muted p-3 text-sm">
          <p id={emailNoticeId} className="flex items-start gap-2">
            <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {t('templates.visibility.emailNotVerified')}
          </p>
          <ResendVerificationEmailButton />
        </div>
      )}
      {visibilityMutation.isError && !emailRefused && (
        <ErrorMessage>{translateError(t, visibilityMutation.error)}</ErrorMessage>
      )}
    </fieldset>
  );
}
