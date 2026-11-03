import type { ReactNode } from 'react';

import { Card, CardContent, CardFooter, CardHeader } from './ui/card';
import { PageContainer } from './PageContainer';

interface CenteredCardPageProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function CenteredCardPage({ title, children, footer }: CenteredCardPageProps) {
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
