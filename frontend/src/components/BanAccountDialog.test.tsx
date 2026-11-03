import { fireEvent, screen, waitFor } from '@testing-library/react';
import { createRef, type RefObject } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { BanAccountDialog } from './BanAccountDialog';

const banRoute = 'POST /moderation/accounts/max-id/ban';

function renderDialog(): RefObject<HTMLDialogElement | null> {
  const dialogRef: RefObject<HTMLDialogElement | null> = createRef<HTMLDialogElement>();
  renderWithQueryClient(
    <BanAccountDialog dialogRef={dialogRef} accountId="max-id" displayName="Max" />,
  );
  dialogRef.current?.showModal();
  return dialogRef;
}

function stubBan(answer: () => Response = () => new Response(null, { status: 204 })): unknown[] {
  const bodies: unknown[] = [];
  stubBackend({
    [banRoute]: async (request: Request) => {
      bodies.push(await request.json());
      return answer();
    },
  });
  return bodies;
}

describe('BanAccountDialog', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('bans until the end of the chosen day, with the reason', async () => {
    const bodies: unknown[] = stubBan();
    const dialogRef = renderDialog();
    const close = vi.fn();
    (dialogRef.current as HTMLDialogElement).close = close;
    const submit = screen.getByRole('button', { name: 'Bannir' });

    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Jusqu'au (inclus)"), {
      target: { value: '2099-11-15' },
    });
    fireEvent.change(screen.getByLabelText('Motif (visible par la personne)'), {
      target: { value: ' Spam ' },
    });
    fireEvent.click(submit);

    await waitFor(() => expect(close).toHaveBeenCalledOnce());
    // Le jour choisi est inclus : le bannissement finit au début du jour suivant, en heure locale
    expect(bodies).toEqual([
      { reason: 'Spam', ends_at: new Date('2099-11-16T00:00:00').toISOString() },
    ]);
  });

  it('bans for good without an end date', async () => {
    const bodies: unknown[] = stubBan();
    renderDialog();

    fireEvent.click(screen.getByLabelText('Définitivement'));
    expect(screen.queryByLabelText("Jusqu'au (inclus)")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Motif (visible par la personne)'), {
      target: { value: 'Spam' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Bannir' }));

    await waitFor(() => expect(bodies).toEqual([{ reason: 'Spam' }]));
  });

  it('shows why the ban was refused', async () => {
    stubBan(() => errorResponse(409, 'cannot_ban_super_admin'));
    renderDialog();

    fireEvent.click(screen.getByLabelText('Définitivement'));
    fireEvent.change(screen.getByLabelText('Motif (visible par la personne)'), {
      target: { value: 'Spam' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Bannir' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Un super admin ne peut pas être banni.',
    );
  });
});
