// Codes d'erreur du retour de Google (backend : /auth/google/callback → /login?error=<code>)
export const GOOGLE_ERROR_MESSAGES: Readonly<Record<string, string>> = {
  google_cancelled: 'Connexion avec Google annulée.',
  google_email_not_verified:
    "Votre adresse Google n'est pas vérifiée : elle ne peut pas servir à vous connecter.",
  google_unavailable: "La connexion avec Google n'est pas disponible pour le moment.",
  google_failed: 'La connexion avec Google a échoué, veuillez réessayer.',
};

// Affiché pour un code inconnu
export const GOOGLE_GENERIC_ERROR_MESSAGE = GOOGLE_ERROR_MESSAGES.google_failed;
