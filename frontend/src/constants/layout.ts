// Largeurs des pages (docs/technical/architecture.md, « Page widths ») : une seule largeur pour
// toute l'application, pour que rien ne saute d'une page à l'autre ni au démarrage d'une partie
export const PAGE_WIDTH_CLASS = {
  // Pages de l'application : accueil, modèles, historique, salle (avant et pendant la partie),
  // résultats, éditeur. L'en-tête et le pied de page, eux, prennent toute la fenêtre
  app: 'max-w-6xl',
  // Pages de texte (pages légales) : des lignes courtes, lisibles
  reading: 'max-w-3xl',
  // Formulaires seuls (connexion, inscription, mot de passe, page introuvable)
  form: 'max-w-sm',
} as const;

export type PageWidth = keyof typeof PAGE_WIDTH_CLASS;

// Colonne étroite à l'intérieur d'une page app : listes et salon, alignés à gauche sur le titre
export const CONTENT_COLUMN_CLASS = 'w-full max-w-2xl';
