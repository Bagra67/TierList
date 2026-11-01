import { useTranslation } from 'react-i18next';

// Remplace le bouton « Lancer une salle » d'un modèle masqué par la modération (US-1.5) : le
// statut est écrit, pas seulement suggéré par une couleur. Le motif est dans l'éditeur.
export function TemplateHiddenBadge() {
  const { t } = useTranslation();
  return (
    <span className="shrink-0 rounded-md border border-destructive/40 px-2 py-1 text-xs font-semibold">
      {t('templates.hidden.badge')}
    </span>
  );
}
