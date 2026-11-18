import { type Location, matchPath, type PathMatch } from 'react-router';

import { ROUTES } from '../constants/routes';
import { isTemplateId } from '../constants/templates';

interface SignInRedirectState {
  from?: string;
}

export function signInRedirectState(location: Location): SignInRedirectState {
  return { from: `${location.pathname}${location.search}${location.hash}` };
}

export function pathAfterSignIn(location: Location): string {
  return (location.state as SignInRedirectState | null)?.from ?? ROUTES.HOME;
}

export function publicTemplateIdAfterSignIn(location: Location): string | undefined {
  const match: PathMatch<'templateId'> | null = matchPath(
    ROUTES.PUBLIC_TEMPLATE,
    pathAfterSignIn(location),
  );
  const templateId: string | undefined = match?.params.templateId;
  return templateId !== undefined && isTemplateId(templateId) ? templateId : undefined;
}
