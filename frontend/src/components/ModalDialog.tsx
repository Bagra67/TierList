import { type ReactNode, type RefObject, useId } from 'react';

import { Button } from './ui/button';

interface ModalDialogProps {
  // Ouvert par le parent avec dialogRef.current.showModal(), fermé avec close()
  dialogRef: RefObject<HTMLDialogElement | null>;
  title: string;
  // Texte sous le titre (avertissement, conséquences)
  description?: string;
  onClose?: () => void;
  children: ReactNode;
}

// <dialog> natif ouvert avec showModal() : le navigateur piège le focus dedans et le ferme avec
// Échap. Le titre nomme le dialogue pour les lecteurs d'écran.
export function ModalDialog({
  dialogRef,
  title,
  description,
  onClose,
  children,
}: ModalDialogProps) {
  const titleId: string = useId();
  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClose={onClose}
      className="m-auto w-full max-w-md rounded-xl bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {title}
      </h2>
      {description !== undefined && <p className="mt-2 text-muted-foreground">{description}</p>}
      {children}
    </dialog>
  );
}

interface DialogActionsProps {
  cancelLabel: string;
  onCancel: () => void;
  // Libellé du bouton d'envoi, déjà choisi selon l'état (« Supprimer » / « Suppression… »)
  submitLabel: string;
  submitVariant?: 'default' | 'destructive';
  submitDisabled: boolean;
}

// Pied d'un formulaire de dialogue : Annuler à gauche, l'action à droite
export function DialogActions({
  cancelLabel,
  onCancel,
  submitLabel,
  submitVariant = 'default',
  submitDisabled,
}: DialogActionsProps) {
  return (
    <div className="flex justify-end gap-2">
      <Button type="button" variant="outline" onClick={onCancel}>
        {cancelLabel}
      </Button>
      <Button type="submit" variant={submitVariant} disabled={submitDisabled}>
        {submitLabel}
      </Button>
    </div>
  );
}
