import { fireEvent, render, type RenderResult, screen } from '@testing-library/react';
import { describe, expect, it, type Mock, vi } from 'vitest';

import { fileDataTransfer } from '../test/fileDataTransfer';
import { ImageDropZone } from './ImageDropZone';

const pngFile: File = new File(['png'], 'photo.png', { type: 'image/png' });

interface Handlers {
  onSelect: Mock<(file: File) => void>;
  onRemove: Mock<() => void>;
  onRefuse: Mock<() => void>;
}

function renderZone(
  props: Partial<{ imageUrl: string | null; isUploading: boolean; disabled: boolean }> = {},
): Handlers {
  const handlers: Handlers = { onSelect: vi.fn(), onRemove: vi.fn(), onRefuse: vi.fn() };
  render(
    <ImageDropZone
      label="Ajouter une image"
      removeLabel="Retirer l'image"
      size="large"
      imageUrl={props.imageUrl ?? null}
      isUploading={props.isUploading ?? false}
      disabled={props.disabled ?? false}
      {...handlers}
    />,
  );
  return handlers;
}

function zone(): HTMLElement {
  return screen.getByRole('button', { name: 'Ajouter une image' });
}

function fileInput(): HTMLInputElement {
  const input: HTMLInputElement | null = document.querySelector('input[type="file"]');
  if (input === null) throw new Error('no file input');
  return input;
}

describe('ImageDropZone', () => {
  it('shows the hint when empty', () => {
    renderZone();
    expect(zone()).toHaveTextContent('Glisser une image ou cliquer');
    expect(zone().querySelector('img')).toBeNull();
  });

  it('opens the file picker on click, which only proposes JPEG, PNG and WebP', () => {
    renderZone();
    const click: Mock<() => void> = vi.fn();
    fileInput().click = click;

    fireEvent.click(zone());

    expect(click).toHaveBeenCalledOnce();
    expect(fileInput()).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp');
    // Le champ caché n'est pas atteignable au clavier : la vignette, un vrai bouton, l'est
    expect(fileInput()).toHaveAttribute('tabindex', '-1');
  });

  it('sends the chosen file', () => {
    const { onSelect }: Handlers = renderZone();

    fireEvent.change(fileInput(), { target: { files: [pngFile] } });

    expect(onSelect).toHaveBeenCalledWith(pngFile);
  });

  it('highlights while a file is dragged over it, then sends the dropped file', () => {
    const { onSelect }: Handlers = renderZone();

    fireEvent.dragEnter(zone(), { dataTransfer: fileDataTransfer(pngFile) });

    expect(zone()).toHaveTextContent('Déposer');
    expect(zone()).toHaveClass('border-primary');

    fireEvent.drop(zone(), { dataTransfer: fileDataTransfer(pngFile) });

    expect(zone()).not.toHaveTextContent('Déposer');
    expect(onSelect).toHaveBeenCalledWith(pngFile);
  });

  it('stops highlighting when the file leaves without being dropped', () => {
    const { onSelect }: Handlers = renderZone();

    fireEvent.dragEnter(zone(), { dataTransfer: fileDataTransfer(pngFile) });
    fireEvent.dragLeave(zone(), { dataTransfer: fileDataTransfer(pngFile) });

    expect(zone()).not.toHaveTextContent('Déposer');
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('refuses a file that is not an accepted image without sending it', () => {
    const { onSelect, onRefuse }: Handlers = renderZone();

    fireEvent.drop(zone(), {
      dataTransfer: fileDataTransfer(new File(['gif'], 'anim.gif', { type: 'image/gif' })),
    });

    expect(onRefuse).toHaveBeenCalledOnce();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('shows the chosen file at once while it is uploading', () => {
    const handlers: Handlers = { onSelect: vi.fn(), onRemove: vi.fn(), onRefuse: vi.fn() };
    const { rerender }: RenderResult = render(
      <ImageDropZone
        label="Ajouter une image"
        size="large"
        imageUrl={null}
        isUploading={false}
        {...handlers}
      />,
    );

    fireEvent.change(fileInput(), { target: { files: [pngFile] } });
    rerender(
      <ImageDropZone
        label="Ajouter une image"
        size="large"
        imageUrl={null}
        isUploading
        {...handlers}
      />,
    );

    expect(zone()).toHaveAttribute('aria-busy', 'true');
    expect(zone().querySelector('img')?.getAttribute('src')).toMatch(/^blob:/);
    expect(screen.getByRole('status')).toHaveTextContent("Envoi de l'image…");
  });

  it('removes the image with its own button, reachable with the keyboard', () => {
    const { onRemove }: Handlers = renderZone({ imageUrl: 'https://images.example.com/a.webp' });
    const removeButton: HTMLElement = screen.getByRole('button', { name: "Retirer l'image" });

    removeButton.focus();
    fireEvent.click(removeButton);

    expect(removeButton).toHaveFocus();
    expect(onRemove).toHaveBeenCalledOnce();
    expect(zone().querySelector('img')).toHaveAttribute('src', 'https://images.example.com/a.webp');
  });

  it('ignores drops and clicks when disabled', () => {
    const { onSelect }: Handlers = renderZone({ disabled: true });

    fireEvent.drop(zone(), { dataTransfer: fileDataTransfer(pngFile) });

    expect(zone()).toBeDisabled();
    expect(onSelect).not.toHaveBeenCalled();
  });
});
