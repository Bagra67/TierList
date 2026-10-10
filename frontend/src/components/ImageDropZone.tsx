import {
  type ChangeEvent,
  type DragEvent,
  type RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from '@/lib/utils';
import { ACCEPTED_IMAGE_TYPES } from '../constants/images';

interface ImageDropZoneProps {
  // Nom accessible de la vignette : ce que fait un clic (ajouter ou remplacer l'image)
  label: string;
  // Image enregistrée, null s'il n'y en a pas
  imageUrl: string | null;
  isUploading: boolean;
  disabled?: boolean;
  // large : formulaire d'ajout, avec une consigne ; small : vignette d'une tuile
  size: 'large' | 'small';
  // Bouton pour retirer l'image, affiché seulement s'il y a une image et un libellé
  removeLabel?: string;
  onSelect: (file: File) => void;
  onRemove?: () => void;
  // Fichier qui n'est pas une image JPEG, PNG ou WebP : refusé sans être envoyé
  onRefuse: () => void;
}

function draggedFiles(event: DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes('Files');
}

// Vignette d'image d'une tuile : un clic (ou Entrée, Espace) ouvre le sélecteur de fichier, et
// on peut y déposer un fichier. Pendant l'envoi, l'image choisie s'affiche aussitôt, voilée,
// avec un indicateur ; l'image compressée par le backend la remplace ensuite. Le parent envoie
// le fichier et affiche les erreurs.
export function ImageDropZone({
  label,
  imageUrl,
  isUploading,
  disabled = false,
  size,
  removeLabel,
  onSelect,
  onRemove,
  onRefuse,
}: ImageDropZoneProps) {
  const inputRef: RefObject<HTMLInputElement | null> = useRef<HTMLInputElement>(null);
  const [isDraggingOver, setIsDraggingOver] = useState<boolean>(false);
  // dragenter et dragleave se déclenchent aussi en passant sur les éléments enfants : on compte
  // les entrées pour savoir quand le fichier quitte vraiment la vignette
  const dragDepth: RefObject<number> = useRef<number>(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const shownUrl: string | null = isUploading && previewUrl !== null ? previewUrl : imageUrl;

  // L'aperçu local occupe de la mémoire tant que son URL existe : libérée quand il change
  useEffect(() => {
    return () => {
      if (previewUrl !== null) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function handleFile(file: File | undefined) {
    if (file === undefined || disabled) return;
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      onRefuse();
      return;
    }
    setPreviewUrl(URL.createObjectURL(file));
    onSelect(file);
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    handleFile(event.target.files?.[0]);
    // Permet de choisir à nouveau le même fichier (ex. après une erreur)
    event.target.value = '';
  }

  function handleDragEnter(event: DragEvent<HTMLDivElement>) {
    if (disabled || !draggedFiles(event)) return;
    event.preventDefault();
    dragDepth.current += 1;
    setIsDraggingOver(true);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    if (disabled || !draggedFiles(event)) return;
    // Sans preventDefault, le navigateur refuse le dépôt (et ouvrirait le fichier)
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }

  function handleDragLeave() {
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setIsDraggingOver(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    if (disabled) return;
    event.preventDefault();
    dragDepth.current = 0;
    setIsDraggingOver(false);
    handleFile(event.dataTransfer.files[0]);
  }

  const showRemove: boolean =
    removeLabel !== undefined && onRemove !== undefined && imageUrl !== null && !isUploading;

  return (
    <div
      className={cn('relative shrink-0', size === 'large' ? 'size-24' : 'size-12')}
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
          'focus-visible:ring-3 focus-visible:ring-ring/50',
          'disabled:cursor-not-allowed disabled:opacity-50',
          shownUrl === null ? 'border-dashed border-border bg-muted/30' : 'border-border bg-card',
          isDraggingOver && 'border-solid border-primary bg-primary/10 ring-3 ring-primary/30',
        )}
      >
        {shownUrl !== null ? (
          <img src={shownUrl} alt="" className="size-full object-cover" />
        ) : (
          <span className="flex flex-col items-center gap-1 px-1 text-center" aria-hidden="true">
            <ImageIcon className={size === 'large' ? 'size-7' : 'size-5'} />
            {size === 'large' && (
              <span className="text-[0.7rem] leading-tight">
                {t('templates.editor.image.hint')}
              </span>
            )}
          </span>
        )}
        {isDraggingOver && (
          <span
            className="absolute inset-0 flex items-center justify-center rounded-lg bg-primary/20 text-xs font-medium text-primary"
            aria-hidden="true"
          >
            {t('templates.editor.image.drop')}
          </span>
        )}
        {isUploading && (
          <span className="absolute inset-0 flex items-center justify-center rounded-lg bg-background/60">
            <span
              className="size-5 animate-spin rounded-full border-2 border-primary border-t-transparent"
              aria-hidden="true"
            />
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
          className="absolute -top-1.5 -right-1.5 flex size-5 cursor-pointer items-center justify-center rounded-full border bg-background text-[0.65rem] text-muted-foreground shadow-sm transition-colors outline-none hover:bg-destructive hover:text-white focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <span aria-hidden="true">✕</span>
        </button>
      )}
      {/* Le vrai champ fichier est caché : la vignette ci-dessus le remplace, au clavier aussi */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(',')}
        tabIndex={-1}
        aria-hidden="true"
        className="sr-only"
        onChange={handleChange}
      />
    </div>
  );
}

// Icône « image » (cadre, soleil, montagne), dessinée ici : le projet n'a pas de bibliothèque
// d'icônes
function ImageIcon({ className }: { className: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <circle cx="9" cy="9" r="2" />
      <path d="m21 15-4.5-4.5L5 21" />
    </svg>
  );
}
