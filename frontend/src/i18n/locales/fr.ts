// Langue de référence : ses clés définissent le type Translation, que chaque autre langue doit
// respecter exactement (une clé absente ou en trop fait échouer pnpm typecheck).
export const fr = {
  common: {
    loading: 'Chargement…',
    backendUnreachable: 'Impossible de joindre le backend : est-il lancé ?',
    language: 'Langue',
    theme: 'Thème',
  },
  home: {
    title: 'Accueil',
  },
  renderError: {
    title: 'Une erreur est survenue',
    message:
      "La page n'a pas pu s'afficher. Rechargez-la ; si le problème persiste, réessayez plus tard.",
    reload: 'Recharger la page',
  },
  notFound: {
    title: 'Page introuvable',
    message: "Cette page n'existe pas ou n'existe plus.",
    backHome: "Retour à l'accueil",
  },
  theme: {
    system: 'Système',
    light: 'Clair',
    dark: 'Sombre',
  },
  auth: {
    email: 'Email',
    password: 'Mot de passe',
    displayName: 'Nom affiché',
    continueWithGoogle: 'Continuer avec Google',
    signedInAs: 'Connecté en tant que {{name}}',
    logout: 'Se déconnecter',
    login: {
      title: 'Connexion',
      submit: 'Se connecter',
      submitting: 'Connexion…',
      noAccount: 'Pas encore de compte ?',
      registerLink: 'Créer un compte',
      forgotPassword: 'Mot de passe oublié ?',
    },
    register: {
      title: 'Créer un compte',
      submit: 'Créer mon compte',
      submitting: 'Création…',
      hasAccount: 'Déjà un compte ?',
      loginLink: 'Se connecter',
    },
    verifyEmail: {
      title: 'Confirmer votre adresse email',
      intro: "Confirmez l'adresse de votre compte TierList.",
      submit: 'Confirmer mon adresse',
      submitting: 'Confirmation…',
      success: 'Votre adresse email est confirmée.',
      missingToken: 'Ce lien est incomplet : ouvrez le lien reçu par email.',
      continue: 'Continuer',
    },
    forgotPassword: {
      title: 'Mot de passe oublié',
      intro:
        "Indiquez l'adresse de votre compte : vous recevrez un lien pour choisir un nouveau mot de passe.",
      submit: 'Envoyer le lien',
      submitting: 'Envoi…',
      sent: "Si un compte existe pour cette adresse, un email vient d'être envoyé. Pensez à regarder vos spams.",
      backToLogin: 'Retour à la connexion',
    },
    resetPassword: {
      title: 'Choisir un nouveau mot de passe',
      newPassword: 'Nouveau mot de passe',
      submit: 'Changer le mot de passe',
      submitting: 'Enregistrement…',
      success: 'Votre mot de passe a été changé. Connectez-vous avec le nouveau.',
      signIn: 'Se connecter',
      missingToken: 'Ce lien est incomplet : ouvrez le lien reçu par email.',
    },
  },
  account: {
    verification: {
      pending: 'Confirmez votre adresse : un lien a été envoyé à {{email}}.',
      resend: "Renvoyer l'email",
      resending: 'Envoi…',
      resent: 'Email envoyé. Pensez à regarder vos spams (un envoi par minute au plus).',
    },
    delete: {
      open: 'Supprimer mon compte',
      title: 'Supprimer mon compte',
      warning: 'Cette action est définitive : votre compte et toutes ses données seront effacés.',
      googleLinked: "Votre compte est relié à Google : aucune saisie n'est nécessaire.",
      signInAgainWithGoogle: 'Se reconnecter avec Google',
      cancel: 'Annuler',
      submit: 'Supprimer définitivement',
      submitting: 'Suppression…',
    },
  },
  errors: {
    unknown: 'Une erreur est survenue, veuillez réessayer.',
    // Une clé par code d'erreur de l'API (backend/app/constants/error_codes.py)
    api: {
      internal_error: 'Erreur interne du serveur, veuillez réessayer.',
      validation_error: 'Certains champs sont invalides.',
      http_error: 'La requête a échoué.',
      database_unavailable: 'Base de données indisponible.',
      not_authenticated: 'Authentification requise.',
      email_already_registered: 'Cet email est déjà utilisé',
      invalid_credentials: 'Email ou mot de passe incorrect',
      session_expired: 'Session expirée, veuillez vous reconnecter.',
      incorrect_password: 'Mot de passe incorrect',
      reauthentication_required: 'Reconnectez-vous avec Google pour confirmer la suppression',
      invalid_token: 'Ce lien est invalide ou a expiré.',
    },
    // Une clé par code d'erreur de champ de la 422 (type Pydantic ou code dédié), avec ses params
    field: {
      invalid: 'Valeur invalide.',
      missing: 'Ce champ est obligatoire.',
      string_too_short: 'Au moins {{min_length}} caractères.',
      string_too_long: 'Au plus {{max_length}} caractères.',
      value_error: 'Valeur invalide.',
      password_too_short: 'Le mot de passe doit contenir au moins {{min_length}} caractères',
    },
    // Codes du retour de Google (backend : /auth/google/callback → /login?error=<code>)
    google: {
      google_cancelled: 'Connexion avec Google annulée.',
      google_email_not_verified:
        "Votre adresse Google n'est pas vérifiée : elle ne peut pas servir à vous connecter.",
      google_unavailable: "La connexion avec Google n'est pas disponible pour le moment.",
      google_failed: 'La connexion avec Google a échoué, veuillez réessayer.',
    },
  },
} as const;

// Même forme que fr, avec des textes quelconques
type Widen<T> = { readonly [K in keyof T]: T[K] extends string ? string : Widen<T[K]> };
export type Translation = Widen<typeof fr>;
