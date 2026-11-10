import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { reportError } from '../monitoring/sentry';
import { CenteredCardPage } from './CenteredCardPage';
import { Button } from './ui/button';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    reportError(error, info.componentStack ?? undefined);
  }

  render() {
    return this.state.hasError ? <RenderErrorFallback /> : this.props.children;
  }
}

function RenderErrorFallback() {
  const { t } = useTranslation();

  return (
    <CenteredCardPage title={t('renderError.title')}>
      <p>{t('renderError.message')}</p>
      <Button type="button" className="w-full" onClick={() => window.location.reload()}>
        {t('renderError.reload')}
      </Button>
    </CenteredCardPage>
  );
}
