import { QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

import { createQueryClient } from '../api/queryClient';

// Un QueryClient neuf par test : aucun cache partagé entre tests, et pas de nouvel essai qui ralentirait les cas d'erreur
export function renderWithQueryClient(ui: ReactElement) {
  const queryClient = createQueryClient({ queries: { retry: false } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
