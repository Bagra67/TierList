import { type QueryClient, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type GameResults = components['schemas']['GameResultsResponse'];
export type TierItems = components['schemas']['TierItemsResponse'];
export type ItemDistribution = components['schemas']['ItemDistributionResponse'];
export type PlayerResults = components['schemas']['PlayerResultsResponse'];

// La case fait partie de la clé : basculer relit une fois, puis chaque variante reste en cache
function resultsQueryKey(token: string, includeAbsentVotes: boolean) {
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

export interface GameResultsState {
  // Les résultats avec la case choisie ; undefined pendant leur lecture ou après un échec
  results: GameResults | undefined;
  // Ce qui ne dépend pas de la case (template, date, tiers, items) : ces résultats, ou ceux de
  // l'autre variante déjà lus. La page garde ainsi sa case et ses onglets pendant une lecture ou
  // après un échec, sans montrer des statistiques qui ne correspondent pas à la case
  anyVariant: GameResults | undefined;
  isPending: boolean;
  error: Error | null;
}

export function useGameResults(token: string, includeAbsentVotes: boolean): GameResultsState {
  const queryClient: QueryClient = useQueryClient();
  const query = useQuery({
    queryKey: resultsQueryKey(token, includeAbsentVotes),
    queryFn: ({ signal }) => getGameResults(token, includeAbsentVotes, signal),
    retry: retryUnlessClientError,
    // Les résultats d'une partie close ne changent plus (invariant 9)
    staleTime: Infinity,
  });
  const otherVariant: GameResults | undefined = queryClient.getQueryData<GameResults>(
    resultsQueryKey(token, !includeAbsentVotes),
  );
  return {
    results: query.data,
    anyVariant: query.data ?? otherVariant,
    isPending: query.isPending,
    error: query.error,
  };
}
