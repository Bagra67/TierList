// Langue de référence : ses clés définissent le type Translation, que chaque autre langue doit
// respecter exactement (une clé absente ou en trop fait échouer pnpm typecheck).
export const fr = {
  common: {
    loading: 'Chargement…',
    backendUnreachable: 'Le serveur ne répond pas. Réessayez dans un instant.',
    language: 'Langue',
    theme: 'Thème',
  },
  home: {
    title: 'Accueil',
    intro:
      'Classez ensemble, en direct : chacun place les mêmes éléments dans sa tier list, puis vous comparez les résultats.',
    steps: {
      title: 'Comment ça marche',
      template: 'Préparez un modèle : ses tiers et ses tuiles, en texte ou en image.',
      room: 'Ouvrez une salle et partagez son lien ou son code.',
      play: "À chaque manche, tout le monde place l'élément. À la fin, découvrez les résultats.",
    },
    prepareTemplate: 'Préparer un modèle',
    joinRoom: {
      title: 'Rejoindre une salle',
      code: 'Code de la salle',
      submit: 'Rejoindre',
    },
  },
  nav: {
    label: 'Navigation principale',
    home: 'Accueil',
    templates: 'Mes modèles',
    history: 'Historique',
  },
  settings: {
    open: 'Paramètres',
    title: 'Paramètres',
    close: 'Fermer',
    display: 'Affichage',
    account: 'Compte',
    about: 'Informations',
  },
  footer: {
    privacy: 'Politique de confidentialité',
  },
  privacy: {
    title: 'Politique de confidentialité',
    updatedAt: 'Dernière mise à jour : {{date, datetime(dateStyle: long)}}',
    intro:
      'Cette page explique quelles données personnelles TierList collecte, pourquoi, combien de temps elles sont gardées, qui les traite et comment exercer vos droits.',
    controller: {
      title: 'Responsable du traitement',
      body: 'TierList est édité par {{name}}, responsable du traitement de vos données personnelles. Pour toute question ou demande sur vos données :',
    },
    data: {
      title: 'Données collectées',
      account:
        "Compte : adresse e-mail, pseudo, mot de passe (jamais stocké en clair, seulement sous forme hachée) et langue de l'interface.",
      google:
        "Connexion avec Google, si vous la choisissez : l'identifiant et l'adresse e-mail de votre compte Google.",
      guest:
        'Invités : le pseudo choisi pour rejoindre une salle, et un cookie qui vous reconnaît dans cette salle.',
      content:
        'Contenus : vos modèles, les textes de leurs tuiles et les images que vous envoyez. Les images sont réencodées sans leurs métadonnées (données EXIF, position GPS).',
      games:
        'Parties : les salles que vous rejoignez, vos placements et les résultats des parties.',
      technical:
        'Données techniques : les cookies et le stockage local décrits plus bas, et des journaux techniques (identifiants internes, jamais vos mots de passe).',
    },
    purposes: {
      title: 'Pourquoi ces données',
      service:
        "Fournir le service que vous demandez en utilisant TierList (exécution du contrat) : créer votre compte, vous connecter, faire jouer les parties, envoyer les e-mails de vérification de l'adresse et de réinitialisation du mot de passe.",
      security:
        'Assurer la sécurité et le bon fonctionnement du service (intérêt légitime) : journaux techniques, sauvegardes, suppression automatique des données expirées.',
      noAds: 'Vos données ne sont ni vendues, ni utilisées pour de la publicité ou du profilage.',
    },
    retention: {
      title: 'Durées de conservation',
      account:
        "Compte, modèles et salles que vous avez créés : jusqu'à la suppression de votre compte.",
      sessions: 'Session de connexion : 30 jours sans utilisation.',
      links:
        "Liens envoyés par e-mail : 24 heures pour la vérification de l'adresse, 30 minutes pour un nouveau mot de passe.",
      guests:
        "Lien personnel d'un invité : 30 jours. Une salle inactive est fermée après 24 heures.",
      deleted:
        'Modèles supprimés : effacés définitivement après 30 jours. Images qui ne sont plus utilisées : effacées après 7 jours.',
      backups: 'Sauvegardes de la base de données : 14 jours.',
    },
    visibility: {
      title: 'Qui voit vos données',
      room: "Les participants d'une salle voient le modèle utilisé, les pseudos et les placements de la partie.",
      results:
        "Le lien des résultats d'une partie terminée peut être ouvert par toute personne qui le possède, sans compte.",
      deletedAccount:
        "Après la suppression de votre compte, les parties terminées gardent votre pseudo et une copie du modèle joué, pour que les résultats des autres joueurs restent complets. Vous pouvez demander l'effacement de votre pseudo par e-mail.",
    },
    processors: {
      title: 'Prestataires',
      intro:
        'Vos données sont traitées par les prestataires suivants, uniquement pour faire fonctionner le service :',
      minestrator: "MineStrator : hébergement de l'application et de la base de données (France).",
      scaleway:
        'Scaleway : stockage des images, envoi des e-mails et stockage des sauvegardes (France).',
      cloudflare:
        'Cloudflare : nom de domaine, chiffrement HTTPS et acheminement du trafic (États-Unis).',
      google: 'Google : connexion avec un compte Google, si vous la choisissez (États-Unis).',
      github: "GitHub : déploiement de l'application et transfert des sauvegardes (États-Unis).",
      transfers:
        'Les transferts vers les États-Unis reposent sur les garanties prévues par le RGPD, comme les clauses contractuelles types de la Commission européenne.',
    },
    cookies: {
      title: 'Cookies et stockage local',
      intro:
        "TierList n'utilise que des cookies strictement nécessaires à son fonctionnement, sans mesure d'audience ni publicité : aucun consentement n'est donc demandé.",
      session: 'Cookie de session : garde votre connexion (30 jours).',
      google: 'Cookie de connexion avec Google : le temps de la connexion (10 minutes).',
      guest: "Cookie d'invité : vous reconnaît dans une salle (30 jours au plus).",
      local: 'Stockage local du navigateur : le thème et la langue choisis.',
    },
    security: {
      title: 'Sécurité',
      body: "Les échanges sont chiffrés (HTTPS), les mots de passe ne sont jamais stockés en clair, les cookies de session sont inaccessibles aux scripts de la page, et l'accès aux serveurs est limité.",
    },
    rights: {
      title: 'Vos droits',
      body: 'Vous pouvez accéder à vos données, les rectifier, les effacer, limiter leur traitement, vous opposer à ce traitement et demander leur portabilité.',
      delete: 'Vous pouvez supprimer votre compte à tout moment depuis le panneau de paramètres.',
      request:
        'Pour toute autre demande, écrivez à {{email}} : une réponse vous sera apportée sous un mois.',
      cnil: 'Vous pouvez aussi adresser une réclamation à la CNIL :',
      cnilLink: 'déposer une plainte sur cnil.fr',
    },
    changes: {
      title: 'Modifications',
      body: "Cette politique peut évoluer avec le service. La date de dernière mise à jour figure en haut de la page, et un changement important sera signalé dans l'application.",
    },
  },
  history: {
    title: 'Historique',
    empty: "Aucune partie terminée pour l'instant. Vos parties apparaîtront ici une fois closes.",
    emptyAction: 'Créer ou rejoindre une partie',
    closedAt: '{{date, datetime(dateStyle: medium; timeStyle: short)}}',
    players_one: '{{count}} joueur',
    players_other: '{{count}} joueurs',
    open: 'Voir les résultats',
    openLabel: 'Voir les résultats de la partie {{name}}',
    more: 'Voir plus',
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
    email: 'E-mail',
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
      title: 'Confirmer votre adresse e-mail',
      intro: "Confirmez l'adresse de votre compte TierList.",
      submit: 'Confirmer mon adresse',
      submitting: 'Confirmation…',
      success: 'Votre adresse e-mail est confirmée.',
      missingToken: 'Ce lien est incomplet : ouvrez le lien reçu par e-mail.',
      continue: 'Continuer',
    },
    forgotPassword: {
      title: 'Mot de passe oublié',
      intro:
        "Indiquez l'adresse de votre compte : vous recevrez un lien pour choisir un nouveau mot de passe.",
      submit: 'Envoyer le lien',
      submitting: 'Envoi…',
      sent: "Si un compte existe pour cette adresse, un e-mail vient d'être envoyé. Pensez à vérifier vos courriers indésirables.",
      backToLogin: 'Retour à la connexion',
    },
    resetPassword: {
      title: 'Choisir un nouveau mot de passe',
      newPassword: 'Nouveau mot de passe',
      submit: 'Changer le mot de passe',
      submitting: 'Enregistrement…',
      success: 'Votre mot de passe a été changé. Connectez-vous avec le nouveau.',
      signIn: 'Se connecter',
      missingToken: 'Ce lien est incomplet : ouvrez le lien reçu par e-mail.',
    },
  },
  account: {
    verification: {
      pending: 'Confirmez votre adresse : un lien a été envoyé à {{email}}.',
      resend: "Renvoyer l'e-mail",
      resending: 'Envoi…',
      resent:
        'E-mail envoyé. Pensez à vérifier vos courriers indésirables (un envoi par minute au plus).',
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
  templates: {
    title: 'Mes modèles',
    empty: "Vous n'avez encore aucun modèle : créez-en un pour commencer.",
    tileCount_one: '{{count}} tuile',
    tileCount_other: '{{count}} tuiles',
    updatedAt: 'Modifié le {{date, datetime(dateStyle: long)}}',
    create: {
      open: 'Nouveau modèle',
      title: 'Nouveau modèle',
      name: 'Nom',
      cancel: 'Annuler',
      submit: 'Créer',
      submitting: 'Création…',
    },
    delete: {
      open: 'Supprimer',
      openLabel: 'Supprimer {{name}}',
      title: 'Supprimer « {{name}} » ?',
      warning: 'Le modèle disparaîtra de votre liste.',
      cancel: 'Annuler',
      submit: 'Supprimer',
      submitting: 'Suppression…',
    },
    editor: {
      back: 'Retour à mes modèles',
      name: 'Nom du modèle',
      tiers: 'Tiers',
      addTier: 'Ajouter un tier',
      tierName: 'Nom du tier {{position}}',
      tierColor: 'Couleur du tier {{name}}',
      // Sélecteur de couleur d'un tier (react-colorful)
      color: {
        area: 'Saturation et luminosité',
        areaValue: 'Saturation {{saturation}} %, luminosité {{brightness}} %',
        hue: 'Teinte',
        presets: 'Couleurs proposées',
        preset: 'Choisir {{color}}',
        hex: 'Code hexadécimal',
        done: 'OK',
      },
      moveUp: 'Monter {{name}}',
      moveDown: 'Descendre {{name}}',
      deleteTier: 'Supprimer le tier {{name}}',
      dragHandle: 'Déplacer {{name}}',
      tiles: 'Tuiles',
      tileCount: '{{count}} / {{max}} tuiles',
      newTileText: 'Texte de la nouvelle tuile',
      newTileHint: 'Un texte, une image, ou les deux.',
      addTile: 'Ajouter la tuile',
      addingTile: 'Ajout…',
      tileText: 'Texte de la tuile {{position}}',
      // Nom d'une tuile qui n'a qu'une image, dans les libellés des boutons
      tileName: 'Tuile {{position}}',
      // Vignette d'image : clic pour choisir un fichier, ou glisser-déposer
      image: {
        addToNew: 'Ajouter une image à la nouvelle tuile',
        replaceNew: "Remplacer l'image de la nouvelle tuile",
        removeNew: "Retirer l'image de la nouvelle tuile",
        addTo: 'Ajouter une image à {{name}}',
        replace: "Remplacer l'image de {{name}}",
        remove: "Retirer l'image de {{name}}",
        hint: 'Glisser une image ou cliquer',
        drop: 'Déposer',
        uploading: "Envoi de l'image…",
      },
      moveBefore: 'Déplacer {{name}} avant',
      moveAfter: 'Déplacer {{name}} après',
      deleteTile: 'Supprimer la tuile {{name}}',
      // Annonces des lecteurs d'écran pendant un glisser-déposer au clavier
      dnd: {
        instructions:
          'Pour déplacer un élément, appuyez sur Espace ou Entrée, utilisez les flèches, puis Espace ou Entrée pour le déposer, ou Échap pour annuler.',
        pickedUp: '{{item}} saisi, position {{position}} sur {{count}}.',
        movedOver: '{{item}} déplacé en position {{position}} sur {{count}}.',
        dropped: '{{item}} déposé en position {{position}} sur {{count}}.',
        cancelled: 'Déplacement de {{item}} annulé.',
      },
    },
  },
  results: {
    title: 'Résultats : {{name}}',
    closedAt: 'Partie terminée le {{date, datetime(dateStyle: long; timeStyle: short)}}',
    includeAbsentVotes: 'Inclure les votes absents',
    publicLink: 'Lien public des résultats',
    tabsLabel: 'Vues des résultats',
    tabs: {
      median: 'Médian',
      overall: 'Global',
      players: 'Par joueur',
    },
    emptyTier: 'Aucun élément',
    itemImage: "Image de l'élément {{number}}",
    backToRoom: 'Retour à la salle',
    playAgain: 'Rejouer',
    playAgainSubmitting: 'Lancement…',
    median: {
      unranked: 'Non classés',
    },
    overall: {
      caption: 'Nombre de joueurs qui ont mis chaque élément dans chaque tier',
      item: 'Élément',
      absent: 'Absents',
    },
    players: {
      select: 'Joueur',
      unplaced: 'Jamais placés',
      none: "Personne n'a joué cette partie.",
    },
  },
  rooms: {
    create: {
      open: 'Créer une salle',
      openLabel: 'Créer une salle avec {{name}}',
      submitting: 'Création…',
    },
    lobby: {
      title: 'Salle {{code}}',
      template: 'Modèle : {{name}}',
      templateDeleted:
        'Le modèle de cette salle a été supprimé : aucune nouvelle partie ne peut y démarrer.',
      code: 'Code de la salle',
      link: 'Lien de la salle',
      copyLink: 'Copier le lien',
      linkCopied: 'Lien copié',
      copyFailed: 'Impossible de copier le lien : sélectionnez-le et copiez-le à la main.',
      participants: 'Participants ({{count}})',
      admin: 'hôte',
      online: 'en ligne',
      offline: 'hors ligne',
      liveUnavailable: 'Mises à jour en direct indisponibles : rechargez la page.',
      guest: 'invité',
      removed: "L'hôte vous a retiré de cette salle.",
      banned: "L'hôte vous a banni de cette salle.",
      comeBack: 'Revenir dans la salle',
      closed: "L'hôte a fermé cette salle.",
      pastGames: {
        title: 'Parties passées ({{count}})',
        closedAt: '{{date, datetime(dateStyle: medium; timeStyle: short)}}',
        players_one: '{{count}} joueur',
        players_other: '{{count}} joueurs',
        open: 'Voir les résultats',
        openLabel:
          'Voir les résultats de la partie du {{date, datetime(dateStyle: medium; timeStyle: short)}}',
      },
      backHome: "Retour à l'accueil",
      close: {
        open: 'Fermer la salle',
        title: 'Fermer la salle ?',
        warning:
          'La salle est supprimée avec son lien et son code ; les liens personnels des invités ne fonctionnent plus. Ses parties terminées restent dans les historiques.',
        gameWarning:
          'Une partie est en cours : elle est close d’abord, avec les classements du moment, puis la salle est supprimée avec son lien et son code.',
        cancel: 'Annuler',
        submit: 'Fermer la salle',
        submitting: 'Fermeture…',
      },
      remove: {
        open: 'Retirer',
        openLabel: 'Retirer {{name}}',
        title: 'Retirer {{name}} ?',
        warning:
          "Sa place est supprimée. Il pourra revenir avec le lien ou le code, sauf s'il est banni.",
        ban: 'Bannir : ne pourra plus revenir dans cette salle',
        guestWarning:
          'Un invité peut contourner le bannissement (fenêtre privée, cookies effacés). Verrouillez les arrivées pour l’en empêcher vraiment.',
        cancel: 'Annuler',
        submit: 'Retirer',
        submitBan: 'Bannir',
        submitting: 'Retrait…',
      },
      start: {
        submit: 'Lancer la partie',
        replay: 'Rejouer',
        submitting: 'Lancement…',
      },
      bans: {
        title: 'Bannis ({{count}})',
        unban: 'Débannir',
        unbanLabel: 'Débannir {{name}}',
      },
    },
    game: {
      title: 'Partie en cours',
      itemProgress: 'Élément {{number}} sur {{total}}',
      timeLeft: 'Temps restant',
      currentItemImage: "Image de l'élément en cours",
      placedItemImage: "Image d'un élément placé",
      placedCount_one: 'Placé {{placed}} / {{count}} connecté',
      placedCount_other: 'Placé {{placed}} / {{count}} connectés',
      nameYou: '{{name}} (vous)',
      status: {
        placed: 'a placé',
        waiting: 'en attente',
        disconnected: 'déconnecté',
      },
      board: 'Mon classement',
      dock: "Glissez l'élément dans un tier, à la position voulue, ou utilisez les boutons « Placer dans ».",
      dragHandle: 'Glisser dans un tier',
      dragHandleLabel: 'Glisser dans un tier : {{item}}',
      dragLabel: 'Déplacer {{item}}',
      placeIn: 'Placer dans {{tier}}',
      placeInLabel: "Placer dans {{tier}} : l'élément en cours, à la fin",
      imageItemAt: 'Image en {{tier}}, position {{position}}',
      moveEarlier: 'Avancer {{item}} dans son tier',
      moveLater: 'Reculer {{item}} dans son tier',
      next: 'Élément suivant',
      nexting: 'Passage…',
      auto: {
        none: 'Passage automatique : désactivé',
        timer: 'Passage automatique : minuteur de {{seconds}} s',
        everyone_placed: 'Passage automatique : quand tout le monde a placé',
      },
      lateArrivals: 'Arrivées ouvertes',
      cooldown: {
        title: 'Retouches finales',
        timeLeft: 'Fin des retouches',
        hint: "Déplacez n'importe quelle tuile. Placez vos éléments manqués avant la fin.",
        waiting: 'Les participants finalisent leur classement.',
        missed: 'Éléments manqués',
        missedImage: "Image d'un élément manqué, {{position}}",
        absent: 'Absent',
        placeInLabel: 'Tier où placer {{item}}',
        place: 'Placer',
        placeLabel: 'Placer {{item}} à la fin du tier choisi',
        moveUp: 'Monter {{item}} au tier du dessus',
        moveDown: 'Descendre {{item}} au tier du dessous',
        end: {
          open: 'Terminer maintenant',
          title: 'Terminer les retouches ?',
          warning:
            'Les classements de tous les participants deviennent définitifs et la partie est close.',
          cancel: 'Annuler',
          submit: 'Terminer',
          submitting: 'Fin…',
        },
      },
      // Annonces des lecteurs d'écran pendant un glisser-déposer
      dnd: {
        instructions:
          "Pour placer l'élément, appuyez sur Espace ou Entrée, utilisez les flèches, puis Espace ou Entrée pour le déposer, ou Échap pour annuler.",
        pickedUp: '{{item}} saisi.',
        unchanged: '{{item}} reste à sa place.',
        over: '{{item}} au-dessus de {{tier}}, position {{position}}.',
        dropped: '{{item}} déposé dans {{tier}}, position {{position}}.',
        cancelled: 'Déplacement de {{item}} annulé.',
      },
    },
    join: {
      title: 'Rejoindre la salle',
      withAccount: 'Avec un compte',
      withAccountHint:
        'Gardez cette partie dans votre historique. Vous revenez dans cette salle après la connexion.',
      signIn: 'Se connecter',
      asGuest: 'En invité',
      nickname: 'Pseudo',
      asGuestHint:
        "Pas d'historique. Ce navigateur se souvient de vous, et votre lien personnel fonctionne sur tous les appareils.",
      submit: 'Rejoindre en invité',
      submitting: 'Arrivée…',
    },
    guestLink: {
      title: 'Votre lien personnel',
      hint: "Gardez-le : il vous ramène à votre place depuis n'importe quel appareil, jusqu'au {{date, datetime(dateStyle: long)}}. Il ne pourra pas être retrouvé.",
      label: 'Lien personnel',
      renew: 'Obtenir un nouveau lien personnel',
      renewHint:
        "Vous avez perdu votre lien personnel ? Un nouveau lien remplace l'ancien, qui ne fonctionne plus.",
      renewing: 'Création du lien…',
    },
    settings: {
      title: 'Réglages',
      edit: 'Modifier',
      dialogTitle: 'Réglages de la salle',
      itemOrder: {
        label: 'Ordre des éléments',
        template: 'Ordre du modèle',
        random: 'Aléatoire',
      },
      autoAdvance: {
        label: 'Élément suivant',
        none: 'Manuel uniquement',
        timer: 'Minuteur par élément',
        everyone_placed: 'Quand tout le monde a placé',
      },
      timerSeconds: 'Durée du minuteur (secondes)',
      manualNote: "L'hôte peut toujours passer à l'élément suivant à la main.",
      cooldownSeconds: 'Retouches finales (secondes)',
      adminPlays: 'Je joue aussi',
      lateArrivals: 'Autoriser les arrivées pendant la partie',
      lockedNote: 'Une partie est en cours : seules les arrivées peuvent être modifiées.',
      cancel: 'Annuler',
      submit: 'Enregistrer',
      submitting: 'Enregistrement…',
      // Résumé affiché dans le lobby, à tous les participants
      summary: {
        itemOrder: {
          template: 'Ordre du modèle',
          random: 'Ordre aléatoire',
        },
        autoAdvance: {
          none: 'Élément suivant à la main',
          timer: 'Minuteur de {{seconds}} s par élément',
          everyone_placed: 'Élément suivant quand tout le monde a placé',
        },
        cooldown: 'Retouches finales de {{seconds}} s',
        adminPlays: "L'hôte joue",
        adminDoesNotPlay: "L'hôte ne joue pas",
        lateArrivalsAllowed: 'Arrivées autorisées pendant la partie',
        lateArrivalsLocked: 'Arrivées bloquées pendant la partie',
      },
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
      email_already_registered: 'Cet e-mail est déjà utilisé',
      invalid_credentials: 'E-mail ou mot de passe incorrect',
      session_expired: 'Session expirée, veuillez vous reconnecter.',
      incorrect_password: 'Mot de passe incorrect',
      reauthentication_required: 'Reconnectez-vous avec Google pour confirmer la suppression',
      invalid_token: 'Ce lien est invalide ou a expiré.',
      template_not_found: 'Ce modèle est introuvable.',
      template_has_no_tiles: 'Ajoutez au moins une tuile à ce modèle pour jouer avec.',
      room_not_found: 'Cette salle est introuvable ou a été fermée.',
      room_admin_required: "Seul l'hôte peut faire cela.",
      room_settings_locked: 'Pendant une partie, seules les arrivées peuvent être modifiées.',
      game_in_progress: 'Une partie est déjà en cours dans cette salle.',
      no_placing_participant:
        'Il faut au moins un participant qui place les éléments : invitez un joueur ou jouez vous-même.',
      round_not_in_progress: "Aucun tour n'est en cours : l'élément ne peut plus être placé.",
      not_a_placing_participant:
        'Vous ne jouez pas cette partie : vous avez seulement les commandes.',
      item_not_current: "Cet élément n'est plus l'élément en cours : le tour est passé.",
      item_not_in_game: 'Cet élément ne fait pas partie de la partie.',
      cooldown_not_in_progress: 'Les retouches finales ne sont pas en cours.',
      cooldown_over: 'Les retouches finales sont terminées : plus rien ne peut être placé.',
      results_not_found: 'Ce lien de résultats ne correspond à aucune partie terminée.',
      room_full: 'Cette salle est pleine : {{max_participants}} participants au plus.',
      room_locked: 'Une partie est en cours et la salle est verrouillée.',
      nickname_taken: 'Ce pseudo est déjà pris dans cette salle.',
      guest_link_invalid: 'Ce lien personnel a expiré, ou la salle a été fermée.',
      participant_not_found: "Ce participant n'est plus dans la salle.",
      cannot_remove_room_admin: "L'hôte ne peut pas se retirer de sa salle.",
      room_banned: 'Vous avez été banni de cette salle.',
      ban_not_found: "Ce bannissement n'existe plus.",
      removed_from_room: "L'hôte vous a retiré de cette salle.",
      room_closed: 'Cette salle a été fermée.',
      invalid_message: 'Message inattendu sur le canal de la salle.',
      heartbeat_timeout: 'La connexion à la salle ne répondait plus.',
      tier_not_found: 'Ce tier est introuvable.',
      last_tier: 'Un modèle garde au moins un tier.',
      tile_not_found: 'Cette tuile est introuvable.',
      tile_limit_reached: 'Un modèle a au plus {{max_tiles}} tuiles.',
      tile_empty: "Une tuile a besoin d'un texte ou d'une image.",
      image_unsupported_format: "Ce fichier n'est pas une image JPEG, PNG ou WebP.",
      image_too_large: "L'image est trop lourde : {{max_bytes, megabytes}} au maximum.",
      image_too_many_pixels: "L'image est trop grande : réduisez sa définition puis réessayez.",
      image_upload_limit_reached:
        "Vous avez envoyé {{max_uploads}} images dans l'heure : réessayez un peu plus tard.",
      image_not_found: 'Cette image est introuvable.',
    },
    // Une clé par code d'erreur de champ de la 422 (type Pydantic ou code dédié), avec ses params
    field: {
      invalid: 'Valeur invalide.',
      missing: 'Ce champ est obligatoire.',
      string_too_short: 'Au moins {{min_length}} caractères.',
      string_too_long: 'Au plus {{max_length}} caractères.',
      value_error: 'Valeur invalide.',
      string_pattern_mismatch: 'Format invalide.',
      greater_than_equal: 'Au moins {{ge}}.',
      less_than_equal: 'Au plus {{le}}.',
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
