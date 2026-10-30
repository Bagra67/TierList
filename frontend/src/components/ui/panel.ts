import { cva } from 'class-variance-authority';

// Encadrés de l'interface, au rayon « panneau » de la charte (16 px) :
// - solid : une section ou un formulaire (inviter, rejoindre, commandes de l'hôte) ;
// - dashed : une zone à remplir ou vide (dépôt de l'élément, éléments manqués, liste vide) ;
// - list : une liste de lignes séparées (participants, modèles, historique) ;
// - muted : un bandeau d'information (élément en cours)
export const panelVariants = cva('flex w-full flex-col rounded-panel', {
  variants: {
    variant: {
      solid: 'gap-2 border bg-card p-4',
      dashed: 'gap-2 border-2 border-dashed p-4',
      list: 'divide-y overflow-hidden border bg-card',
      muted: 'gap-2 bg-muted p-4',
    },
  },
  defaultVariants: {
    variant: 'solid',
  },
});
