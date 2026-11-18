import { QueryCache, QueryClient, type DefaultOptions } from '@tanstack/react-query';

import { ApiError } from '../errors/apiError';
import { NetworkError } from '../errors/networkError';
import { reportError } from '../monitoring/sentry';

const RETRIES_BEFORE_SHOWING_ERROR: number = 1;

function isClientError(error: Error): boolean {
  return error instanceof ApiError && error.status < 500;
}

function isApiOrNetworkError(error: Error): boolean {
  return error instanceof ApiError || error instanceof NetworkError;
}

export function createQueryClient(defaultOptions?: DefaultOptions): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        if (isClientError(error)) return;
        console.error(`Échec de la requête ${JSON.stringify(query.queryKey)}`, error);
        if (!isApiOrNetworkError(error)) {
          reportError(error);
        }
      },
    }),
    defaultOptions: {
      ...defaultOptions,
      queries: { retry: RETRIES_BEFORE_SHOWING_ERROR, ...defaultOptions?.queries },
    },
  });
}

export function retryUnlessClientError(failureCount: number, error: Error): boolean {
  return !isClientError(error) && failureCount < RETRIES_BEFORE_SHOWING_ERROR;
}
