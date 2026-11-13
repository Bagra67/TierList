import { LoaderCircle, X } from 'lucide-react';
import { type KeyboardEvent, type RefObject, useEffect, useId, useRef, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';

import { type Template, type TemplateChange, useSetTemplateTags } from '../api/templates';
import { TAG_MAX_LENGTH, TEMPLATE_MAX_TAGS } from '../constants/templates';
import {
  type FieldError,
  getFieldErrors,
  translateError,
  translateFieldError,
} from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { tagPillClassName } from './TemplateTagList';

interface TemplateTagsFieldProps {
  template: Template;
}

interface PendingRemoval {
  label: string;
  index: number;
}

function tagsFieldError(error: unknown): FieldError | undefined {
  return Object.entries(getFieldErrors(error)).find(
    ([field]) => field === 'tags' || field.startsWith('tags.'),
  )?.[1];
}

export function TemplateTagsField({ template }: TemplateTagsFieldProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tagsMutation: TemplateChange<string[]> = useSetTemplateTags(template.id);
  const [draft, setDraft] = useState<string>('');
  const [isDuplicate, setIsDuplicate] = useState<boolean>(false);
  const listRef: RefObject<HTMLUListElement | null> = useRef<HTMLUListElement>(null);
  const inputRef: RefObject<HTMLInputElement | null> = useRef<HTMLInputElement>(null);
  const pendingRemoval: RefObject<PendingRemoval | null> = useRef<PendingRemoval>(null);
  const hintId: string = useId();
  const errorId: string = useId();

  const tags: string[] = template.tags;
  const isFull: boolean = tags.length >= TEMPLATE_MAX_TAGS;
  const fieldError: FieldError | undefined = tagsFieldError(tagsMutation.error);
  const errorMessage: string | undefined = tagsMutation.isError
    ? (translateFieldError(t, fieldError) ?? translateError(t, tagsMutation.error))
    : undefined;

  useEffect(() => {
    const removal: PendingRemoval | null = pendingRemoval.current;
    if (removal === null || tags.includes(removal.label)) return;
    pendingRemoval.current = null;
    const removeButtons: NodeListOf<HTMLButtonElement> | undefined =
      listRef.current?.querySelectorAll('button');
    (removeButtons?.[removal.index] ?? inputRef.current)?.focus();
  }, [tags]);

  function addDraft() {
    const label: string = draft.trim();
    if (label === '' || isFull || tagsMutation.isPending) return;
    const countBefore: number = tags.length;
    tagsMutation.mutate([...tags, label], {
      onSuccess: (saved: Template) => {
        setDraft('');
        setIsDuplicate(saved.tags.length === countBefore);
      },
    });
  }

  function remove(index: number) {
    if (tagsMutation.isPending) return;
    setIsDuplicate(false);
    pendingRemoval.current = { label: tags[index], index };
    tagsMutation.mutate(
      tags.filter((_tag, tagIndex) => tagIndex !== index),
      {
        onError: () => {
          pendingRemoval.current = null;
        },
      },
    );
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
      event.preventDefault();
      addDraft();
    }
    if (event.key === 'Escape') setDraft('');
  }

  return (
    <fieldset className="flex min-w-0 flex-col gap-1.5">
      <legend className="mb-1 flex w-full items-baseline justify-between gap-2 text-sm leading-none font-medium">
        <span>{t('templates.tags.legend')}</span>
        <span className="font-normal text-muted-foreground tabular-nums">
          {t('templates.tags.count', { count: tags.length, max: TEMPLATE_MAX_TAGS })}
        </span>
      </legend>
      <div
        className={cn(
          'flex min-h-9 flex-wrap items-center gap-1.5 rounded-lg border border-input px-1.5 py-1 transition-colors',
          'has-[input:focus-visible]:border-ring has-[input:focus-visible]:ring-3 has-[input:focus-visible]:ring-ring',
          errorMessage !== undefined && 'border-destructive',
        )}
      >
        {tags.length > 0 && (
          <ul
            ref={listRef}
            aria-label={t('templates.tags.listLabel')}
            className="flex max-w-full flex-wrap gap-1.5"
          >
            {tags.map((tag, index) => (
              <li
                key={tag}
                className={cn(tagPillClassName, 'min-h-7 gap-0.5 py-0.5 pr-0.5 pl-2.5 text-sm')}
              >
                <span className="min-w-0 break-words">{tag}</span>
                <button
                  type="button"
                  aria-label={t('templates.tags.remove', { label: tag })}
                  aria-disabled={tagsMutation.isPending}
                  onClick={() => remove(index)}
                  className="flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors outline-none hover:bg-destructive hover:text-background focus-visible:ring-3 focus-visible:ring-ring aria-disabled:cursor-not-allowed"
                >
                  <X aria-hidden="true" className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {!isFull && (
          <span className="flex min-w-32 flex-1 items-center gap-1">
            <input
              ref={inputRef}
              type="text"
              value={draft}
              maxLength={TAG_MAX_LENGTH}
              readOnly={tagsMutation.isPending}
              aria-busy={tagsMutation.isPending}
              aria-label={t('templates.tags.add')}
              aria-invalid={errorMessage !== undefined}
              aria-describedby={errorMessage === undefined ? hintId : `${hintId} ${errorId}`}
              placeholder={t('templates.tags.add')}
              onChange={(event) => {
                setDraft(event.target.value);
                setIsDuplicate(false);
              }}
              onKeyDown={handleKeyDown}
              onBlur={addDraft}
              className="h-7 w-full min-w-0 bg-transparent px-1 text-base outline-none placeholder:text-muted-foreground md:text-sm"
            />
            {tagsMutation.isPending && (
              <LoaderCircle
                aria-hidden="true"
                className="size-4 shrink-0 animate-spin text-muted-foreground"
              />
            )}
          </span>
        )}
      </div>
      {isFull && (
        <p className="text-sm text-muted-foreground">
          {t('templates.tags.limitReached', { max: TEMPLATE_MAX_TAGS })}
        </p>
      )}
      <p id={hintId} className="text-sm text-muted-foreground">
        {t('templates.tags.hint')}
      </p>
      <p aria-live="polite" className="text-sm empty:hidden">
        {isDuplicate ? t('templates.tags.duplicate') : null}
      </p>
      {errorMessage !== undefined && (
        <ErrorMessage className="text-sm">{errorMessage}</ErrorMessage>
      )}
    </fieldset>
  );
}
