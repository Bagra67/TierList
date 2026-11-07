import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { REPORT_DETAILS_MAX_LENGTH } from '../constants/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';
import { ReportButton } from './ReportButton';

const TARGET_ID: string = '3f0a1b2c-0000-4000-8000-000000000001';

function openDialog(routes: Parameters<typeof stubBackend>[0]) {
  const fetchMock: BackendMock = stubBackend(routes);
  renderWithQueryClient(
    <ReportButton targetKind="game" targetId={TARGET_ID} contentName="Épices" />,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Signaler : Épices' }));
  const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Signaler cette partie' });
  return { fetchMock, dialog };
}

function submitButton(dialog: HTMLElement): HTMLElement {
  return within(dialog).getByRole('button', { name: 'Envoyer le signalement' });
}

describe('ReportButton', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends the chosen reason and the trimmed details, then confirms', async () => {
    const { fetchMock, dialog } = openDialog({
      'POST /reports': () => Response.json({ id: TARGET_ID }, { status: 201 }),
    });
    expect(within(dialog).getByText(/la personne signalée ne saura pas/)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('radio', { name: 'Harcèlement' }));
    fireEvent.change(within(dialog).getByLabelText('Précisions (facultatif)'), {
      target: { value: '  Insultes  ' },
    });
    fireEvent.click(submitButton(dialog));

    expect(await within(dialog).findByRole('status')).toHaveTextContent('Merci');
    const request: Request = fetchMock.mock.calls[0][0];
    await expect(request.json()).resolves.toEqual({
      target_kind: 'game',
      target_id: TARGET_ID,
      reason: 'harassment',
      details: 'Insultes',
    });
  });

  it('asks for a reason before sending', () => {
    const { dialog } = openDialog({});

    expect(submitButton(dialog)).toBeDisabled();
  });

  it('asks for details when the reason is other', () => {
    const { dialog } = openDialog({});

    fireEvent.click(within(dialog).getByRole('radio', { name: 'Autre' }));
    const details: HTMLElement = within(dialog).getByLabelText('Précisions');
    expect(details).toBeRequired();
    expect(details).toHaveAttribute('maxlength', String(REPORT_DETAILS_MAX_LENGTH));
    expect(submitButton(dialog)).toBeDisabled();

    fireEvent.change(details, { target: { value: '   ' } });
    expect(submitButton(dialog)).toBeDisabled();

    fireEvent.change(details, { target: { value: 'Une copie' } });
    expect(submitButton(dialog)).toBeEnabled();
  });

  it('says that the content is already reported as an information, not as an error', async () => {
    const { dialog } = openDialog({
      'POST /reports': () => errorResponse(409, 'report_already_open'),
    });

    fireEvent.click(within(dialog).getByRole('radio', { name: 'Spam' }));
    fireEvent.click(submitButton(dialog));

    expect(await within(dialog).findByRole('status')).toHaveTextContent(
      'Vous avez déjà signalé ce contenu',
    );
    expect(within(dialog).queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a refused report and keeps the form', async () => {
    const { dialog } = openDialog({
      'POST /reports': () =>
        errorResponse(429, 'report_limit_reached', { params: { max_reports: 20 } }),
    });

    fireEvent.click(within(dialog).getByRole('radio', { name: 'Spam' }));
    fireEvent.click(submitButton(dialog));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      "20 signalements dans l'heure",
    );
    expect(submitButton(dialog)).toBeEnabled();
  });

  it('starts again empty when reopened', async () => {
    const { dialog } = openDialog({
      'POST /reports': () => Response.json({ id: TARGET_ID }, { status: 201 }),
    });
    fireEvent.click(within(dialog).getByRole('radio', { name: 'Spam' }));
    fireEvent.click(submitButton(dialog));
    await within(dialog).findByRole('status');

    fireEvent.click(within(dialog).getByRole('button', { name: 'Fermer' }));
    fireEvent.click(screen.getByRole('button', { name: 'Signaler : Épices' }));

    await waitFor(() => expect(submitButton(dialog)).toBeDisabled());
    expect(within(dialog).getByRole('radio', { name: 'Spam' })).not.toBeChecked();
  });
});
