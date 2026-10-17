import { type UseQueryResult, useQuery } from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type GameResults = components['schemas']['GameResultsResponse'];
export type TierItems = components['schemas']['TierItemsResponse'];
export type ItemDistribution = components['schemas']['ItemDistributionResponse'];
export type PlayerResults = components['schemas']['PlayerResultsResponse'];

// La case fait partie de la clé : basculer relit une fois, puis chaque variante reste en cache
export function resultsQueryKey(token: string, includeAbsentVotes: boolean) {
  return ['results', token, includeAbsentVotes] as const;
}

// Résultats d'une partie close, lus par son lien, sans compte (US-5.2, US-5.3)
async function getGameResults(
  token: string,
  includeAbsentVotes: boolean,
  signal: AbortSignal,
): Promise<GameResults> {
  return dataOrThrow(
    await apiClient.GET('/results/{public_token}', {
      params: {
        path: { public_token: token },
        query: { include_absent_votes: includeAbsentVotes },
      },
      signal,
    }),
  );
}

export function useGameResults(
  token: string,
  includeAbsentVotes: boolean,
): UseQueryResult<GameResults> {
  return useQuery({
    queryKey: resultsQueryKey(token, includeAbsentVotes),
    queryFn: ({ signal }) => getGameResults(token, includeAbsentVotes, signal),
    retry: retryUnlessClientError,
    // Les résultats d'une partie close ne changent plus (invariant 9)
    staleTime: Infinity,
    // La case cochée ou décochée garde l'affichage précédent pendant la lecture
    placeholderData: (previous) => previous,
  });
}
