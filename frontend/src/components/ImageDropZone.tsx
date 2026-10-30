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

interface ImageDropZoneProps {
  // Nom accessible de la vignette : ce que fait un clic (ajouter ou remplacer l'image)
  label: string;
  // Image enregistrée, null s'il n'y en a pas
  imageUrl: string | null;
  isUploading: boolean;
  disabled?: boolean;
  // large : vignette du formulaire d'ajout ; fill : carré sur toute la largeur du parent (carte
  // d'une tuile). Les deux affichent la consigne quand il n'y a pas d'image.
  size: 'large' | 'fill';
  // Bouton pour retirer l'image, affiché seulement s'il y a une image et un libellé
  removeLabel?: string;
  onSelect: (file: File) => void;
  // Plusieurs fichiers d'un coup (sélecteur ou dépôt) : sans cette prop, seul le premier compte.
  // Avec elle, deux fichiers ou plus lui sont passés tels quels (le parent les trie), un seul
  // suit le chemin habituel (onSelect ou onRefuse)
  onSelectMany?: (files: File[]) => void;
  onRemove?: () => void;
  // Fichier d'un type connu autre que JPEG, PNG ou WebP : refusé sans être envoyé (un type
  // inconnu, vide, part au backend)
  onRefuse: () => void;
}

// Classes de chaque taille de vignette. Le bouton de retrait : sur la petite vignette (large), il
// déborde de son coin ; sur la carte d'une tuile (fill), il est posé dans le coin de l'image, plus
// grand pour être facile à viser
const SIZE_CLASSES = {
  large: {
    zone: 'size-24',
    icon: 'size-7',
    hint: 'text-[0.7rem]',
    remove: '-top-1.5 -right-1.5 size-5',
    removeIcon: 'size-3',
  },
  fill: {
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
  onSelectMany,
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
  const sizeClasses: (typeof SIZE_CLASSES)[ImageDropZoneProps['size']] = SIZE_CLASSES[size];
  const shownUrl: string | null = isUploading && previewUrl !== null ? previewUrl : imageUrl;

  // L'aperçu local occupe de la mémoire tant que son URL existe : libérée quand il change
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
    handleFiles(event.dataTransfer.files);
  }

  const showRemove: boolean =
    removeLabel !== undefined && onRemove !== undefined && imageUrl !== null && !isUploading;

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
          shownUrl === null ? 'border-dashed border-border bg-muted/30' : 'border-border bg-card',
          isDraggingOver && 'border-solid border-primary bg-primary/10 ring-3 ring-primary/30',
        )}
      >
        {shownUrl !== null ? (
          // contain : l'image entière est visible, sans recadrage, sur le fond de la vignette
          <img src={shownUrl} alt="" className="size-full bg-muted object-contain" />
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
      {/* Le vrai champ fichier est caché : la vignette ci-dessus le remplace, au clavier aussi */}
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
