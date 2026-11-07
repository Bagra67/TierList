import { type QueryClient, useQuery, useQueryClient } from '@tanstack/react-query';

import { CLOSED_GAME_RESULTS_NEVER_STALE } from '../constants/results';
import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type GameResults = components['schemas']['GameResultsResponse'];
export type TierItems = components['schemas']['TierItemsResponse'];
export type ItemDistribution = components['schemas']['ItemDistributionResponse'];
export type PlayerResults = components['schemas']['PlayerResultsResponse'];

function resultsQueryKey(token: string, includeAbsentVotes: boolean) {
  return ['results', token, includeAbsentVotes] as const;
}

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
  results: GameResults | undefined;
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
    staleTime: CLOSED_GAME_RESULTS_NEVER_STALE,
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
