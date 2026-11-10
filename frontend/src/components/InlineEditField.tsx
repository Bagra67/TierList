import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from 'react';

import { cn } from 'cn';
import { Input, inputClassName } from './ui/input';
import { Label } from './ui/label';

interface InlineEditFieldProps {
  label: string;
  hideLabel?: boolean;
  value: string;
  maxLength: number;
  required?: boolean;
  wrapsLongValue?: boolean;
  error?: string;
  onSave: (value: string) => void;
  className?: string;
}

interface SharedFieldProps {
  id: string;
  value: string;
  maxLength: number;
  required: boolean;
  'aria-invalid': boolean;
  'aria-describedby': string | undefined;
  onBlur: () => void;
}

export function InlineEditField({
  label,
  hideLabel = false,
  value,
  maxLength,
  required = true,
  wrapsLongValue = false,
  error,
  onSave,
  className,
}: InlineEditFieldProps) {
  const [draft, setDraft] = useState<string>(value);
  const draftSentWithEnter: RefObject<string | null> = useRef<string | null>(null);
  const textAreaRef: RefObject<HTMLTextAreaElement | null> = useRef<HTMLTextAreaElement>(null);
  const id: string = useId();
  const errorId: string = `${id}-error`;

  useTextAreaHeightFollowingItsText(textAreaRef, draft);

  function save() {
    const trimmedDraft: string = draft.trim();
    if (trimmedDraft === value) return;
    onSave(draft);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    draftSentWithEnter.current = draft;
    save();
  }

  function handleBlur() {
    if (draft === draftSentWithEnter.current) return;
    save();
  }

  function handleChange(newDraft: string) {
    draftSentWithEnter.current = null;
    setDraft(newDraft.replace(/\r?\n/g, ' '));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
    if (event.key === 'Escape') {
      setDraft(value);
      return;
    }
    const enterConfirmsImeCharacter: boolean = event.nativeEvent.isComposing;
    if (wrapsLongValue && event.key === 'Enter' && !enterConfirmsImeCharacter) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const fieldProps: SharedFieldProps = {
    id,
    value: draft,
    maxLength,
    required,
    'aria-invalid': error !== undefined,
    'aria-describedby': error === undefined ? undefined : errorId,
    onBlur: handleBlur,
  };

  return (
    <form onSubmit={handleSubmit} className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={id} className={cn(hideLabel && 'sr-only')}>
        {label}
      </Label>
      {wrapsLongValue ? (
        <textarea
          ref={textAreaRef}
          rows={1}
          {...fieldProps}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
          className={cn(inputClassName, 'min-h-8 resize-none overflow-hidden break-words')}
        />
      ) : (
        <Input
          {...fieldProps}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
      )}
      {error !== undefined && (
        <span id={errorId} className="text-sm text-destructive">
          {error}
        </span>
      )}
    </form>
  );
}

function useTextAreaHeightFollowingItsText(
  textAreaRef: RefObject<HTMLTextAreaElement | null>,
  text: string,
): void {
  useLayoutEffect(() => {
    const textArea: HTMLTextAreaElement | null = textAreaRef.current;
    if (textArea === null) return;
    textArea.style.height = 'auto';
    textArea.style.height = `${textArea.scrollHeight}px`;
  }, [textAreaRef, text]);
}
