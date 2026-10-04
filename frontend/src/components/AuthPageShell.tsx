import type { ReactNode } from 'react';

import { Card, CardContent, CardFooter, CardHeader } from './ui/card';

interface AuthPageShellProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

// Mise en page commune des pages de compte (connexion, inscription, liens reçus par email)
export function AuthPageShell({ title, children, footer }: AuthPageShellProps) {
  return (
    <main className="mx-auto w-full max-w-sm px-4 py-10">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">{title}</h1>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">{children}</CardContent>
        {footer !== undefined && <CardFooter className="justify-center">{footer}</CardFooter>}
      </Card>
    </main>
  );
}
