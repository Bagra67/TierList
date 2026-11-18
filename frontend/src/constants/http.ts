export const HTTP_STATUS = {
  NO_CONTENT: 204,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
} as const;

export const GATEWAY_ERROR_STATUSES: ReadonlySet<number> = new Set([502, 503, 504]);
