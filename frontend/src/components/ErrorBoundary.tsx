import { Component, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { AuthPageShell } from './AuthPageShell';
import { Button } from './ui/button';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

// Une erreur pendant le rendu laisserait sinon une page blanche. React journalise déjà l'erreur
// dans la console (onCaughtError) : rien à ajouter ici.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    return this.state.hasError ? <RenderErrorFallback /> : this.props.children;
  }
}

function RenderErrorFallback() {
  const { t } = useTranslation();

  return (
    <AuthPageShell title={t('renderError.title')}>
      <p>{t('renderError.message')}</p>
      <Button type="button" className="w-full" onClick={() => window.location.reload()}>
        {t('renderError.reload')}
      </Button>
    </AuthPageShell>
  );
}
