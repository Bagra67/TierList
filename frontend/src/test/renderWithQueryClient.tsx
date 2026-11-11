import { QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

import type { User } from '../api/auth';
import { createQueryClient } from '../api/queryClient';
import { CURRENT_USER_QUERY_KEY } from '../constants/auth';

interface RenderOptions {
  currentUser?: User;
}

export function renderWithQueryClient(ui: ReactElement, { currentUser }: RenderOptions = {}) {
  const queryClient = createQueryClient({ queries: { retry: false } });
  if (currentUser !== undefined) {
    queryClient.setQueryData(CURRENT_USER_QUERY_KEY, currentUser, { updatedAt: 0 });
  }
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
