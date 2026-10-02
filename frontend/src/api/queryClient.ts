import { QueryCache, QueryClient, type DefaultOptions } from '@tanstack/react-query';

export function createQueryClient(defaultOptions?: DefaultOptions): QueryClient {
  return new QueryClient({
    // Un seul endroit pour journaliser les échecs de requête, quel que soit le composant
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
