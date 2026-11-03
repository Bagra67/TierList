import { ImageIcon, LoaderCircle, X } from 'lucide-react';
import {
  type ChangeEvent,
  type DragEvent,
  type RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';
import { ACCEPTED_IMAGE_TYPES } from '../constants/images';
import { isAcceptedImageFile } from './imageFiles';
import { RemovedImage } from './RemovedImage';

interface ImageDropZoneProps {
  label: string;
  imageUrl: string | null;
  imageRemoved?: boolean;
  isUploading: boolean;
  disabled?: boolean;
  size: 'addFormThumbnail' | 'fullWidthSquare';
  removeLabel?: string;
  onSelect: (file: File) => void;
  onSelectMany?: (files: File[]) => void;
  onRemove?: () => void;
  onRefuse: () => void;
}

const SIZE_CLASSES = {
  addFormThumbnail: {
    zone: 'size-24',
    icon: 'size-7',
    hint: 'text-[0.7rem]',
    remove: '-top-1.5 -right-1.5 size-5',
    removeIcon: 'size-3',
  },
  fullWidthSquare: {
    zone: 'aspect-square w-full',
    icon: 'size-10',
    hint: 'text-xs',
    remove: 'top-1.5 right-1.5 size-7',
    removeIcon: 'size-4',
  },
} as const;

function draggedFiles(event: DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes('Files');
}

function allowChoosingSameFileAgain(input: HTMLInputElement): void {
  input.value = '';
}

function allowDropping(event: DragEvent<HTMLDivElement>): void {
  event.preventDefault();
}

export function ImageDropZone({
  label,
  imageUrl,
  imageRemoved = false,
  isUploading,
  disabled = false,
  size,
  removeLabel,
  onSelect,
  onSelectMany,
  onRemove,
  onRefuse,
}: ImageDropZoneProps) {
  const inputRef: RefObject<HTMLInputElement | null> = useRef<HTMLInputElement>(null);
  const [isDraggingOver, setIsDraggingOver] = useState<boolean>(false);
  const dragEntersIncludingChildren: RefObject<number> = useRef<number>(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const sizeClasses: (typeof SIZE_CLASSES)[ImageDropZoneProps['size']] = SIZE_CLASSES[size];
  const shownUrl: string | null = isUploading && previewUrl !== null ? previewUrl : imageUrl;
  const showRemovedImage: boolean = shownUrl === null && imageRemoved;

  useEffect(() => {
    return () => {
      if (previewUrl !== null) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function handleFile(file: File | undefined) {
    if (file === undefined || disabled) return;
    if (!isAcceptedImageFile(file)) {
      onRefuse();
      return;
    }
    setPreviewUrl(URL.createObjectURL(file));
    onSelect(file);
  }

  function handleFiles(fileList: FileList | null) {
    const files: File[] = fileList === null ? [] : Array.from(fileList);
    if (onSelectMany !== undefined && files.length > 1) {
      if (!disabled) onSelectMany(files);
      return;
    }
    handleFile(files[0]);
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    handleFiles(event.target.files);
    allowChoosingSameFileAgain(event.target);
  }

  function handleDragEnter(event: DragEvent<HTMLDivElement>) {
    if (disabled || !draggedFiles(event)) return;
    event.preventDefault();
    dragEntersIncludingChildren.current += 1;
    setIsDraggingOver(true);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    if (disabled || !draggedFiles(event)) return;
    allowDropping(event);
    event.dataTransfer.dropEffect = 'copy';
  }

  function handleDragLeave() {
    dragEntersIncludingChildren.current = Math.max(0, dragEntersIncludingChildren.current - 1);
    if (dragEntersIncludingChildren.current === 0) setIsDraggingOver(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    if (disabled) return;
    event.preventDefault();
    dragEntersIncludingChildren.current = 0;
    setIsDraggingOver(false);
    handleFiles(event.dataTransfer.files);
  }

  const showRemove: boolean =
    removeLabel !== undefined &&
    onRemove !== undefined &&
    (imageUrl !== null || imageRemoved) &&
    !isUploading;

  return (
    <div
      className={cn('relative shrink-0', sizeClasses.zone)}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <button
        type="button"
        aria-label={label}
        aria-busy={isUploading}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'flex size-full cursor-pointer items-center justify-center overflow-hidden rounded-lg border-2 text-muted-foreground transition-colors outline-none',
          'hover:border-primary/60 hover:bg-muted/60 hover:text-foreground',
          'focus-visible:ring-3 focus-visible:ring-ring',
          'disabled:cursor-not-allowed disabled:opacity-50',
          shownUrl === null && !showRemovedImage
            ? 'border-dashed border-border bg-muted/30'
            : 'border-border bg-card',
          isDraggingOver && 'border-solid border-primary bg-primary/10 ring-3 ring-primary/30',
        )}
      >
        {shownUrl !== null ? (
          <img src={shownUrl} alt="" className="size-full bg-muted object-contain" />
        ) : showRemovedImage ? (
          <RemovedImage className="size-full" showLabel />
        ) : (
          <span className="flex flex-col items-center gap-1 px-1 text-center" aria-hidden="true">
            <ImageIcon className={sizeClasses.icon} />
            <span className={cn('leading-tight', sizeClasses.hint)}>
              {onSelectMany === undefined
                ? t('templates.editor.image.hint')
                : t('templates.editor.image.hintMany')}
            </span>
          </span>
        )}
        {isDraggingOver && (
          <span
            className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/90 text-xs font-semibold text-foreground"
            aria-hidden="true"
          >
            {t('templates.editor.image.drop')}
          </span>
        )}
        {isUploading && (
          <span className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/60">
            <LoaderCircle className="size-5 animate-spin text-primary" />
            <span role="status" className="sr-only">
              {t('templates.editor.image.uploading')}
            </span>
          </span>
        )}
      </button>
      {showRemove && (
        <button
          type="button"
          aria-label={removeLabel}
          onClick={onRemove}
          disabled={disabled}
          className={cn(
            'absolute flex cursor-pointer items-center justify-center rounded-full border bg-background text-muted-foreground shadow-sm transition-colors outline-none hover:bg-destructive hover:text-background focus-visible:ring-3 focus-visible:ring-ring',
            sizeClasses.remove,
          )}
        >
          <X className={sizeClasses.removeIcon} />
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(',')}
        multiple={onSelectMany !== undefined}
        tabIndex={-1}
        aria-hidden="true"
        className="sr-only"
        onChange={handleChange}
      />
    </div>
  );
}
