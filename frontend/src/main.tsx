import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';

import { createQueryClient } from './api/queryClient';
import App from './App';
import './index.css';
// Initialise les traductions avant le premier rendu
import './i18n';
// Applique le thème mémorisé et suit celui du système en mode « system »
import './theme';

const queryClient = createQueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
