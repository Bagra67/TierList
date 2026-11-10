export const MODERATION_REASON_MAX_LENGTH: number = 500;
export const REPORT_DETAILS_MAX_LENGTH: number = 500;

export const MODERATION_LOG_QUERY_KEY = ['moderation', 'log'] as const;
export const SUPER_ADMINS_QUERY_KEY = ['moderation', 'super-admins'] as const;
export const RECENT_UPLOADS_QUERY_KEY = ['moderation', 'images'] as const;
export const REPORT_QUEUE_QUERY_KEY = ['moderation', 'reports'] as const;
export const OPEN_REPORT_COUNT_QUERY_KEY = ['moderation', 'reports-count'] as const;
export const HIDDEN_GAMES_QUERY_KEY = ['moderation', 'hidden-games'] as const;
export const REVIEWED_TEMPLATE_QUERY_KEY = ['moderation', 'templates'] as const;
export const ACCOUNT_SEARCH_QUERY_KEY = ['moderation', 'accounts', 'search'] as const;
export const ACCOUNT_QUERY_KEY = ['moderation', 'accounts', 'detail'] as const;
