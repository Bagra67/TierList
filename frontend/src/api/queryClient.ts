import { QueryCache, QueryClient, type DefaultOptions } from '@tanstack/react-query';

import { ApiError } from '../errors/apiError';

export function createQueryClient(defaultOptions?: DefaultOptions): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        console.error(`Échec de la requête ${JSON.stringify(query.queryKey)}`, error);
      },
    }),
    defaultOptions: {
      ...defaultOptions,
      // 1 seul nouvel essai : les 3 par défaut retardent l'affichage de l'erreur de plusieurs secondes
      queries: { retry: 1, ...defaultOptions?.queries },
    },
  });
}

export function retryUnlessClientError(failureCount: number, error: Error): boolean {
  return !(error instanceof ApiError && error.status < 500) && failureCount < 1;
}
