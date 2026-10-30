import type { ReactNode } from 'react';

import { Card, CardContent, CardFooter, CardHeader } from './ui/card';
import { PageContainer } from './PageContainer';

interface AuthPageShellProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

// Mise en page commune des pages en carte centrée : compte (connexion, inscription, liens reçus
// par email) et page introuvable
export function AuthPageShell({ title, children, footer }: AuthPageShellProps) {
  return (
    <PageContainer width="form">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">{title}</h1>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">{children}</CardContent>
        {footer !== undefined && <CardFooter className="justify-center">{footer}</CardFooter>}
      </Card>
    </PageContainer>
  );
}
