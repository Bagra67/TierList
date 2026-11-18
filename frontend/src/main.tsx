import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';

import { createQueryClient } from './api/queryClient';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { initMonitoring } from './monitoring/sentry';
import './index.css';
import './i18n';
import './theme';

initMonitoring().catch((error: unknown) => {
  console.warn('Suivi des erreurs non démarré', error);
});

const queryClient = createQueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
