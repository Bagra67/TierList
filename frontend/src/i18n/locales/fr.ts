export const fr = {
  common: {
    loading: 'Chargement…',
    backendUnreachable: 'Le serveur ne répond pas. Réessayez dans un instant.',
    language: 'Langue',
    theme: 'Thème',
    imageRemoved: 'Image retirée',
  },
  home: {
    visitor: {
      title: 'Classez ensemble, en direct.',
      intro:
        'Chacun place les mêmes éléments dans sa tier list, sans voir celle des autres. À la fin, vous comparez qui a mis quoi, et où.',
      register: 'Créer un compte',
      signIn: "J'ai déjà un compte",
    },
    signedIn: {
      title: 'Prêt pour une partie, {{name}} ?',
      intro: "Entrez le code d'une salle, ou ouvrez-en une avec un de vos modèles.",
    },
    board: {
      description:
        'Exemple de tier list : trois joueurs ont classé des plats dans les tiers S, A, B et C ; la pizza est en S pour tous les trois.',
      items: {
        pizza: 'Pizza',
        crepes: 'Crêpes',
        sushi: 'Sushi',
        tacos: 'Tacos',
        ramen: 'Ramen',
        croissant: 'Croissant',
        burger: 'Burger',
        salad: 'Salade',
      },
    },
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
    recentTemplates: {
      title: 'Vos modèles',
      all: 'Tous mes modèles',
      empty: "Aucun modèle pour l'instant : préparez le premier pour ouvrir une salle.",
    },
    recentGames: {
      title: 'Vos dernières parties',
      all: "Tout l'historique",
      empty:
        'Aucune partie terminée pour le moment : les résultats de vos parties apparaîtront ici.',
    },
  },
  nav: {
    label: 'Navigation principale',
    home: 'Accueil',
    templates: 'Mes modèles',
    history: 'Historique',
    moderation: 'Modération',
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
    terms: "Conditions d'utilisation",
    legalNotice: 'Mentions légales',
  },
  privacy: {
    title: 'Politique de confidentialité',
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
        "Contenus : vos modèles, les textes de leurs tuiles et les images que vous envoyez. Les images sont réencodées sans leurs métadonnées (données EXIF, position GPS). L'empreinte de chaque fichier envoyé est gardée, pour refuser le renvoi d'une image supprimée par la modération.",
      games:
        'Parties : les salles que vous rejoignez, vos placements et les résultats des parties.',
      reports:
        "Signalements : dans l'application, le compte de la personne qui signale ou, sans compte, l'empreinte de son cookie de signalement, le contenu visé, le motif et les précisions. Par e-mail, son adresse et ce que contient son message.",
      bans: "Bannissements : quand un super admin bannit un compte, la date de fin s'il y en a une, le motif et le super admin qui l'a décidé.",
      moderation:
        "Journal de modération : pour chaque décision de modération, le super admin qui l'a prise, le contenu ou le compte visé (avec son nom au moment de la décision), le motif et la date.",
      technical:
        'Données techniques : les cookies et le stockage local décrits plus bas, et des journaux techniques (identifiants internes, jamais vos mots de passe).',
    },
    purposes: {
      title: 'Pourquoi ces données',
      service:
        "Fournir le service que vous demandez en utilisant TierList (exécution du contrat) : créer votre compte, vous connecter, faire jouer les parties, envoyer les e-mails de vérification de l'adresse et de réinitialisation du mot de passe.",
      security:
        'Assurer la sécurité et le bon fonctionnement du service (intérêt légitime) : journaux techniques, sauvegardes, suppression automatique des données expirées.',
      reports: 'Traiter les signalements de contenus illicites (obligation légale).',
      moderation:
        "Garder la trace des décisions de modération (intérêt légitime) : savoir qui a décidé quoi et pourquoi, retrouver les sanctions passées d'un compte, et refuser qu'une image supprimée par la modération soit envoyée à nouveau.",
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
      moderatedImages:
        "Images retirées par la modération : une image masquée est gardée hors ligne tant qu'elle est masquée ; une image supprimée est effacée aussitôt, et seule son empreinte est gardée, sans limite de durée, pour refuser qu'elle soit renvoyée.",
      backups: 'Sauvegardes de la base de données : 14 jours.',
      reports:
        'Signalements : le temps de les traiter, puis un an au plus pour garder la trace des décisions.',
      bans: "Bannissements : jusqu'à la suppression du compte, pour repérer une récidive.",
      moderation: 'Journal de modération : 3 ans après chaque décision.',
    },
    visibility: {
      title: 'Qui voit vos données',
      room: "Les participants d'une salle voient le modèle utilisé, les pseudos et les placements de la partie.",
      results:
        "Le lien des résultats d'une partie terminée peut être ouvert par toute personne qui le possède, sans compte.",
      moderation:
        "Seuls les super admins (les fondateurs de TierList) voient le journal de modération et, pour les modérer, les images envoyées avec le nom de leur auteur, ainsi que les comptes : le pseudo, l'adresse e-mail, la date de création, si l'adresse est confirmée et les modèles, même privés. Le propriétaire d'un modèle masqué par la modération voit le motif de la décision, et une personne bannie voit le motif de son bannissement quand elle tente de se connecter. Seuls les super admins voient les signalements : la personne signalée ne sait jamais qui l'a signalée.",
      deletedAccount:
        "Après la suppression de votre compte, les parties terminées gardent votre pseudo et une copie du modèle joué, pour que les résultats des autres joueurs restent complets. Le journal de modération garde aussi votre nom tel qu'il était au moment d'une décision, jusqu'à la fin de sa durée de conservation. Vous pouvez demander l'effacement de votre pseudo par e-mail.",
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
      banNotice:
        'Cookie de bannissement : après une connexion avec Google refusée, permet de montrer le motif (10 minutes).',
      guest: "Cookie d'invité : vous reconnaît dans une salle (30 jours au plus).",
      report:
        'Cookie de signalement : après un signalement sans compte, évite les doublons et limite leur fréquence (1 an).',
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
  legalPages: {
    updatedAt: 'Dernière mise à jour : {{date, datetime(dateStyle: long)}}',
    report: {
      title: 'Signaler un contenu',
      intro:
        "Si un contenu publié sur TierList vous semble illicite (haineux, à caractère sexuel, portant atteinte aux droits d'une personne ou contraire à la loi), utilisez le bouton « Signaler » à côté d'une image, d'un pseudo ou d'une partie, avec ou sans compte. Pour tout autre contenu, ou pour recevoir une réponse, écrivez à :",
      include: 'Pour que le signalement puisse être traité, indiquez :',
      page: 'le lien de la page où se trouve le contenu (modèle, salle ou résultats) ;',
      content: 'le contenu visé : une tuile (son texte ou son image), un modèle ou un pseudo ;',
      reason: 'le motif du signalement ;',
      reply: 'une adresse e-mail pour vous répondre.',
      next: "Chaque signalement est examiné rapidement. Un contenu illicite est retiré, et le compte qui l'a publié peut être suspendu ou supprimé. Si vous écrivez par e-mail, vous recevez une réponse avec la décision prise.",
    },
  },
  terms: {
    title: "Conditions d'utilisation",
    intro:
      "Ces conditions s'appliquent à toute personne qui utilise TierList, avec un compte ou en invité. Utiliser le service, c'est les accepter.",
    service: {
      title: 'Le service',
      body: 'TierList permet de créer des modèles de tier list et de les classer ensemble, en direct, dans une salle : chaque joueur place les éléments dans les tiers, puis les résultats de la partie sont calculés. Le service est gratuit.',
    },
    account: {
      title: 'Votre compte',
      one: 'Un compte par personne, avec une adresse e-mail qui vous appartient.',
      password:
        'Gardez votre mot de passe secret : ce qui est fait depuis votre compte est sous votre responsabilité.',
      delete: 'Vous pouvez supprimer votre compte à tout moment depuis le panneau de paramètres.',
    },
    guests: {
      title: 'Jouer en invité',
      body: 'Sans compte, vous rejoignez une salle avec un pseudo. Un lien personnel, valable 30 jours au plus, vous permet de retrouver votre place depuis un autre appareil : ne le partagez pas.',
    },
    content: {
      title: 'Vos contenus',
      rights:
        'Vous gardez vos droits sur les modèles, les textes et les images que vous créez ou envoyez. Vous autorisez TierList à les héberger et à les afficher aux participants de vos salles et aux personnes qui ont le lien des résultats, le temps nécessaire au service.',
      forbidden: 'Ne publiez que des contenus que vous avez le droit de partager. Sont interdits :',
      illegal: 'les contenus illicites ;',
      hateful: 'les contenus haineux, violents ou harcelants ;',
      sexual: 'les contenus à caractère sexuel ;',
      infringing:
        "les contenus qui portent atteinte aux droits d'une personne (droit d'auteur, droit à l'image, vie privée).",
      removal: 'Un contenu interdit peut être retiré sans préavis.',
    },
    visibility: {
      title: 'Ce que voient les autres',
      room: "Les participants d'une salle voient le modèle joué, les pseudos et les placements de la partie.",
      results:
        "Le lien des résultats d'une partie terminée peut être ouvert par toute personne qui le possède, sans compte : ne le partagez qu'avec les personnes de votre choix.",
    },
    sanctions: {
      title: 'Suspension et suppression',
      body: 'Un compte qui ne respecte pas ces conditions peut être suspendu ou supprimé, après un signalement ou une vérification.',
    },
    availability: {
      title: 'Disponibilité',
      body: "TierList est fourni tel quel, sans garantie de disponibilité. Le service peut être interrompu pour maintenance, évoluer ou s'arrêter.",
    },
    liability: {
      title: 'Responsabilité',
      body: "Chaque utilisateur est responsable des contenus qu'il publie. Dans les limites prévues par la loi, TierList ne peut être tenu responsable d'une interruption du service ou d'une perte de données.",
    },
    law: {
      title: 'Droit applicable',
      body: 'Ces conditions sont soumises au droit français. En cas de litige, une solution amiable est recherchée avant tout recours ; à défaut, les tribunaux compétents sont ceux prévus par la loi.',
    },
    changes: {
      title: 'Modifications',
      body: "Ces conditions peuvent évoluer avec le service. La date de dernière mise à jour figure en haut de la page, et un changement important sera signalé dans l'application.",
    },
    contact: {
      title: 'Contact',
      body: 'Pour toute question sur ces conditions :',
    },
  },
  legalNotice: {
    title: 'Mentions légales',
    intro:
      "Informations sur l'éditeur et l'hébergeur de TierList (loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique).",
    publisher: {
      title: 'Éditeur et directeur de la publication',
      body: 'TierList est édité à titre non professionnel par {{name}}, qui en est aussi le directeur de la publication. Contact :',
      anonymity:
        "Comme le permet l'article 6-III-2 de cette loi pour un éditeur non professionnel, son adresse n'est pas publiée : ses coordonnées ont été communiquées à l'hébergeur.",
    },
    host: {
      title: 'Hébergeur',
      body: "L'application et la base de données sont hébergées par :",
    },
    providers: {
      title: 'Autres prestataires',
      cloudflare:
        'Cloudflare, Inc. : nom de domaine, chiffrement HTTPS et acheminement du trafic (États-Unis).',
      scaleway: 'Scaleway SAS : stockage des images et envoi des e-mails (France).',
    },
    data: {
      title: 'Données personnelles',
      body: 'Le traitement de vos données personnelles est décrit dans la <privacy>politique de confidentialité</privacy>.',
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
  moderation: {
    nav: {
      label: 'Espace de modération',
      uploads: 'Derniers envois',
      accounts: 'Comptes',
      log: 'Journal',
    },
    log: {
      title: 'Journal de modération',
      intro:
        'Chaque action : qui, quand, quoi et pourquoi. Aucune entrée ne se modifie ni ne se supprime.',
      target: 'Cible',
      targetPlaceholder: 'Modèle, image, compte…',
      search: 'Rechercher',
      superAdmin: 'Super admin',
      allSuperAdmins: 'Tous',
      empty: "Aucune action de modération pour l'instant.",
      emptyFiltered: 'Aucune action ne correspond à ces filtres.',
      columns: {
        at: 'Quand',
        actor: 'Qui',
        action: 'Action',
        target: 'Cible',
        reason: 'Motif',
      },
      at: '{{date, datetime(dateStyle: medium; timeStyle: short)}}',
      targetCell: '{{type}} « {{label}} »',
      more: 'Voir plus',
    },
    actions: {
      dismiss: 'Classer sans suite',
      hide: 'Masquer',
      unhide: 'Réafficher',
      delete: 'Supprimer',
      ban: 'Bannir',
      lift_ban: 'Lever le bannissement',
    },
    targets: {
      template: 'Modèle',
      image: 'Image',
      account: 'Compte',
      nickname: 'Pseudo',
      game: 'Partie',
    },
    uploads: {
      title: 'Derniers envois',
      intro:
        "Les images envoyées, des plus récentes aux plus anciennes, pour repérer un problème avant qu'on le signale.",
      author: 'Auteur',
      authorPlaceholder: 'Nom ou e-mail',
      search: 'Rechercher',
      from: 'Du',
      to: 'Au',
      status: 'Statut',
      allStatuses: 'Toutes',
      visible: 'Visibles',
      hidden: 'Masquées',
      hiddenBadge: 'Masquée',
      empty: "Aucune image n'a encore été envoyée.",
      emptyFiltered: 'Aucune image ne correspond à ces filtres.',
      more: 'Voir plus',
      deletedAccount: 'Compte supprimé',
      at: '{{date, datetime(dateStyle: medium; timeStyle: short)}}',
      imageAlt:
        'Image envoyée par {{author}} le {{date, datetime(dateStyle: medium; timeStyle: short)}}',
      templates_one: '{{count}} modèle',
      templates_other: '{{count}} modèles',
      games_one: '{{count}} partie',
      games_other: '{{count}} parties',
      templateNames: 'Modèles : {{names, list}}',
      actionLabel: {
        hide: "Masquer l'image de {{author}} du {{date, datetime(dateStyle: medium; timeStyle: short)}}",
        unhide:
          "Réafficher l'image de {{author}} du {{date, datetime(dateStyle: medium; timeStyle: short)}}",
        delete:
          "Supprimer l'image de {{author}} du {{date, datetime(dateStyle: medium; timeStyle: short)}}",
      },
    },
    accounts: {
      title: 'Comptes',
      intro: 'Trouvez un compte par son nom ou son e-mail, puis ouvrez sa page.',
      query: 'Nom ou e-mail',
      queryPlaceholder: 'Max, max@exemple.fr…',
      search: 'Rechercher',
      empty: 'Aucun compte ne correspond.',
      more: 'Voir plus',
      createdAt: 'Créé le {{date, datetime(dateStyle: medium)}}',
      superAdmin: 'Super admin',
      banned: 'Banni',
    },
    account: {
      email: 'E-mail',
      createdAt: 'Création',
      date: '{{date, datetime(dateStyle: medium)}}',
      emailVerified: 'E-mail confirmé',
      yes: 'Oui',
      no: 'Non',
      templates: 'Modèles',
      noTemplates: "Ce compte n'a aucun modèle.",
      templateActionLabel: {
        hide: 'Masquer le modèle {{name}}',
        unhide: 'Réafficher le modèle {{name}}',
        delete: 'Supprimer le modèle {{name}}',
      },
      images: 'Images envoyées',
      noImages: "Ce compte n'a envoyé aucune image visible ou masquée.",
      hideAll: 'Masquer toutes ses images',
      hiddenCount_one: '{{count}} image masquée.',
      hiddenCount_other: '{{count}} images masquées.',
      history: 'Historique de modération',
      noHistory: "Aucune décision n'a encore été prise sur ce compte ni sur son contenu.",
    },
    templateDialog: {
      hide: {
        title: 'Masquer le modèle « {{name}} »',
        description:
          'Plus aucune salle ni partie ne pourra être lancée avec. Son propriétaire le verra, avec le motif, et pourra encore le modifier.',
        submit: 'Masquer',
        submitting: 'Masquage…',
      },
      unhide: {
        title: 'Réafficher le modèle « {{name}} »',
        description:
          'Il retrouvera son état d’avant : des parties pourront de nouveau être lancées avec.',
        submit: 'Réafficher',
        submitting: 'Réaffichage…',
      },
      delete: {
        title: 'Supprimer le modèle « {{name}} »',
        description:
          'Il sera supprimé comme si son propriétaire le faisait. Les parties déjà jouées gardent leur version.',
        submit: 'Supprimer',
        submitting: 'Suppression…',
      },
    },
    ban: {
      section: 'Bannissement',
      none: "Ce compte n'est pas banni.",
      superAdmin: 'Un super admin ne peut pas être banni.',
      open: 'Bannir ce compte',
      change: 'Modifier le bannissement',
      lift: 'Lever le bannissement',
      activePermanent: 'Banni définitivement',
      activeUntil: "Banni jusqu'au {{date, datetime(dateStyle: long; timeStyle: short)}}",
      activeReason: 'Motif : {{reason}}',
      activeBy: 'Par {{name}}, le {{date, datetime(dateStyle: medium)}}',
      pastTitle: 'Bannissements passés',
      pastLifted:
        'Banni le {{start, datetime(dateStyle: medium)}}, levé ou remplacé le {{end, datetime(dateStyle: medium)}}',
      pastEnded:
        "Banni le {{start, datetime(dateStyle: medium)}}, jusqu'au {{end, datetime(dateStyle: medium)}}",
      pastBy: 'Par {{name}}',
      title: 'Bannir {{name}}',
      hint: 'Le compte est déconnecté partout et ne peut plus se connecter avant la fin du bannissement.',
      duration: 'Durée',
      temporary: 'Temporairement',
      until: "Jusqu'au (inclus)",
      permanent: 'Définitivement',
      reason: 'Motif (visible par la personne)',
      submit: 'Bannir',
      submitting: 'Bannissement…',
    },
    liftDialog: {
      title: 'Lever le bannissement de {{name}}',
      description: 'Le compte pourra de nouveau se connecter.',
      submit: 'Lever le bannissement',
      submitting: 'Levée…',
    },
    hideAllDialog: {
      title: 'Masquer toutes les images de {{name}}',
      description:
        'Chaque image visible sera remplacée par « Image retirée » partout où elle apparaît. Vous pourrez les réafficher une à une.',
      submit: 'Tout masquer',
      submitting: 'Masquage…',
    },
    reasonDialog: {
      reason: 'Motif',
      cancel: 'Annuler',
      hide: {
        title: 'Masquer cette image',
        description:
          'Elle sera remplacée par « Image retirée » partout où elle apparaît. Vous pourrez la réafficher.',
        submit: 'Masquer',
        submitting: 'Masquage…',
      },
      unhide: {
        title: 'Réafficher cette image',
        description: 'Elle sera de nouveau affichée partout où elle est utilisée.',
        submit: 'Réafficher',
        submitting: 'Réaffichage…',
      },
      delete: {
        title: 'Supprimer cette image',
        description:
          'Son fichier sera effacé définitivement, et le même fichier ne pourra plus être envoyé. Cette action ne peut pas être annulée.',
        submit: 'Supprimer',
        submitting: 'Suppression…',
      },
    },
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
    logout: 'Se déconnecter',
    acceptTerms: {
      register:
        "En créant un compte, vous acceptez les <terms>conditions d'utilisation</terms> et la <privacy>politique de confidentialité</privacy>.",
      google:
        "En continuant avec Google, vous acceptez les <terms>conditions d'utilisation</terms> et la <privacy>politique de confidentialité</privacy>.",
    },
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
    hidden: {
      badge: 'Masqué',
      title: 'Masqué par la modération',
      reason: 'Motif : {{reason}}',
      hint: 'Vous pouvez encore le modifier, mais plus lancer de partie avec.',
    },
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
      newTileHint:
        "Un texte, une image, ou les deux. Plusieurs images d'un coup : une tuile par image.",
      addTile: 'Ajouter la tuile',
      addingTile: 'Ajout…',
      tileText: 'Texte de la tuile {{position}}',
      tileName: 'Tuile {{position}}',
      bulk: {
        progress: 'Envoi des images : {{done}} / {{total}}',
        added_one: '{{count}} tuile ajoutée.',
        added_other: '{{count}} tuiles ajoutées.',
        skipped_one: '{{count}} image ignorée :',
        skipped_other: '{{count}} images ignorées :',
        skippedImage: '{{name}} : {{reason}}',
        noRoom: 'plus de place dans le modèle ({{max_tiles}} tuiles au maximum).',
      },
      image: {
        addToNew: 'Ajouter une image à la nouvelle tuile',
        replaceNew: "Remplacer l'image de la nouvelle tuile",
        removeNew: "Retirer l'image de la nouvelle tuile",
        addTo: 'Ajouter une image à {{name}}',
        replace: "Remplacer l'image de {{name}}",
        remove: "Retirer l'image de {{name}}",
        hint: 'Glisser une image ou cliquer',
        hintMany: 'Glisser une ou plusieurs images, ou cliquer',
        drop: 'Déposer',
        uploading: "Envoi de l'image…",
      },
      moveBefore: 'Déplacer {{name}} avant',
      moveAfter: 'Déplacer {{name}} après',
      deleteTile: 'Supprimer la tuile {{name}}',
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
  report: {
    open: 'Signaler',
    openLabel: 'Signaler : {{name}}',
    title: {
      item: 'Signaler cette image',
      participant: 'Signaler ce pseudo',
      player: 'Signaler ce pseudo',
      game: 'Signaler cette partie',
    },
    anonymous: "Votre signalement est anonyme : la personne signalée ne saura pas qui l'a envoyé.",
    reason: 'Motif',
    reasons: {
      illegal: 'Contenu illégal',
      sexual: 'Contenu sexuel',
      violence_or_hate: 'Violence ou haine',
      harassment: 'Harcèlement',
      spam: 'Spam',
      other: 'Autre',
    },
    detailsOptional: 'Précisions (facultatif)',
    detailsRequired: 'Précisions',
    submit: 'Envoyer le signalement',
    submitting: 'Envoi…',
    cancel: 'Annuler',
    sent: 'Merci : votre signalement est envoyé.',
    close: 'Fermer',
  },
  results: {
    title: 'Résultats : {{name}}',
    closedAt: 'Partie terminée le {{date, datetime(dateStyle: long; timeStyle: short)}}',
    includeAbsentVotes: 'Inclure les votes absents',
    replayReveal: 'Rejouer la révélation',
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
    votes: {
      title: 'Votes : {{item}}',
      open: 'Voir les votes : {{item}}',
      count_one: '{{count}} vote',
      count_other: '{{count}} votes',
      absent: 'Absents',
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
      templateHidden:
        'Le modèle de cette salle est masqué par la modération : aucune nouvelle partie ne peut y être lancée.',
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
      progress: 'Progression de la partie',
      hostControls: "Commandes de l'hôte",
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
        dndInstructions:
          "Entrée choisit la tuile, puis « Déplacer ici » la met à la fin d'un tier. Pour la placer à une position précise, appuyez sur Espace, utilisez les flèches, puis Espace pour la déposer, ou Échap pour annuler.",
        chooseLabel: 'Choisir {{item}}',
        chooseHint:
          'Choisissez une tuile, puis « Déplacer ici » dans un tier. Vous pouvez aussi la glisser.',
        chosen: 'Tuile choisie : {{item}}',
        cancelChoice: 'Annuler le choix',
        moveHere: 'Déplacer ici',
        moveHereLabel: 'Déplacer {{item}} à la fin de {{tier}}',
        missedNone: 'Aucun : tout est placé.',
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
    api: {
      internal_error: 'Erreur interne du serveur, veuillez réessayer.',
      validation_error: 'Certains champs sont invalides.',
      http_error: 'La requête a échoué.',
      database_unavailable: 'Base de données indisponible.',
      not_authenticated: 'Authentification requise.',
      super_admin_required: 'Seul un super admin peut faire cela.',
      account_not_found: 'Ce compte est introuvable.',
      account_banned: 'Ce compte est banni définitivement : {{reason}}.',
      account_banned_until:
        "Ce compte est banni jusqu'au {{ends_at, datetime(dateStyle: long; timeStyle: short)}} : {{reason}}.",
      cannot_ban_super_admin: 'Un super admin ne peut pas être banni.',
      account_not_banned: "Ce compte n'est pas banni.",
      ban_end_in_past: 'La fin du bannissement doit être dans le futur.',
      email_already_registered: 'Cet e-mail est déjà utilisé',
      invalid_credentials: 'E-mail ou mot de passe incorrect',
      session_expired: 'Session expirée, veuillez vous reconnecter.',
      incorrect_password: 'Mot de passe incorrect',
      reauthentication_required: 'Reconnectez-vous avec Google pour confirmer la suppression',
      invalid_token: 'Ce lien est invalide ou a expiré.',
      template_not_found: 'Ce modèle est introuvable.',
      template_has_no_tiles: 'Ajoutez au moins une tuile à ce modèle pour jouer avec.',
      template_hidden:
        'Ce modèle est masqué par la modération : plus aucune partie ne peut être lancée avec.',
      template_moderation_conflict:
        "Cette action ne s'applique pas au modèle dans son état actuel : il est peut-être déjà masqué, visible ou supprimé.",
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
      report_target_not_found:
        'Ce contenu ne peut pas être signalé : il a peut-être déjà été retiré.',
      report_already_open: 'Vous avez déjà signalé ce contenu : il sera bientôt examiné.',
      report_details_required: 'Précisez votre signalement pour le motif « Autre ».',
      reports_not_open:
        "Ce contenu n'a plus de signalement ouvert : la file a peut-être déjà été traitée.",
      nickname_not_found:
        'Ce pseudo est introuvable : la personne a peut-être supprimé son compte.',
      game_not_found: 'Cette partie est introuvable.',
      game_moderation_conflict:
        "Cette action ne s'applique pas à la partie dans son état actuel : elle est peut-être déjà masquée ou visible.",
      report_limit_reached:
        "Vous avez envoyé {{max_reports}} signalements dans l'heure : réessayez un peu plus tard.",
      image_moderation_conflict:
        "Cette action ne s'applique pas à l'image dans son état actuel : elle est peut-être déjà masquée, visible ou supprimée.",
    },
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
    google: {
      google_cancelled: 'Connexion avec Google annulée.',
      google_email_not_verified:
        "Votre adresse Google n'est pas vérifiée : elle ne peut pas servir à vous connecter.",
      google_unavailable: "La connexion avec Google n'est pas disponible pour le moment.",
      google_failed: 'La connexion avec Google a échoué, veuillez réessayer.',
      google_account_banned: 'Ce compte est banni. Écrivez-nous pour en savoir plus.',
    },
  },
} as const;

type Widen<T> = { readonly [K in keyof T]: T[K] extends string ? string : Widen<T[K]> };
export type Translation = Widen<typeof fr>;
