import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CooldownFrame } from './CooldownFrame';

const NOW: Date = new Date('2026-11-10T12:00:00.000Z');

describe('CooldownFrame', () => {
  it('counts down each second without drawing its content again', () => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    let contentRenders: number = 0;
    function Content() {
      contentRenders += 1;
      return <p>Plateau final</p>;
    }
    render(
      <CooldownFrame endsAt={new Date(NOW.getTime() + 60_000).toISOString()} hint="Indice">
        <Content />
      </CooldownFrame>,
    );

    act(() => vi.advanceTimersByTime(3_000));

    expect(screen.getByRole('timer', { name: 'Fin des retouches' })).toHaveTextContent('0:57');
    expect(contentRenders).toBe(1);
  });

  it('shows no countdown without an end', () => {
    render(
      <CooldownFrame endsAt={null} hint="Indice">
        <p>Plateau final</p>
      </CooldownFrame>,
    );

    expect(screen.queryByRole('timer')).not.toBeInTheDocument();
  });
});
