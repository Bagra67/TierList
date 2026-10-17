import { screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';

import { ResultsPage } from '../pages/ResultsPage';
import { RoomPage } from '../pages/RoomPage';
import { aliceRoom } from './fixtures/rooms';
import { LocationHash } from './LocationHash';
import { renderWithQueryClient } from './renderWithQueryClient';

// Page de la salle ouverte par son lien (path peut porter un fragment, ex. le lien perso) ;
// /login et l'accueil affichent un simple titre ; les résultats ouverts depuis le lobby sont la
// vraie page
export function renderRoomPage(path: string = aliceRoom.code) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/r/${path}`]}>
      <Routes>
        <Route
          path="/r/:code"
          element={
            <>
              <RoomPage />
              <LocationHash />
            </>
          }
        />
        <Route path="/login" element={<h1>Connexion</h1>} />
        <Route path="/" element={<h1>Accueil</h1>} />
        <Route path="/results/:token" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// Résumé des réglages du lobby (le formulaire, fermé, contient les mêmes libellés)
export function settingsSummary(): HTMLElement {
  const section: HTMLElement | null = screen
    .getByRole('heading', { name: 'Réglages' })
    .closest('section');
  if (section === null) throw new Error('No settings section');
  return within(section).getByRole('list');
}
