import { useTranslation } from 'react-i18next';

interface TemplateHiddenNoticeProps {
  // Motif écrit par le super admin, null si le backend n'en a pas (ne devrait pas arriver)
  reason: string | null;
}

// Bandeau de l'éditeur d'un modèle masqué par la modération (US-1.5) : le propriétaire sait
// pourquoi, et ce qui lui reste possible (le modifier, mais plus lancer de partie avec).
export function TemplateHiddenNotice({ reason }: TemplateHiddenNoticeProps) {
  const { t } = useTranslation();
  return (
    <section
      role="status"
      className="flex w-full flex-col gap-1 rounded-lg border border-destructive/40 bg-muted/50 p-4 text-sm"
    >
      <h2 className="font-semibold">{t('templates.hidden.title')}</h2>
      {reason !== null && <p>{t('templates.hidden.reason', { reason })}</p>}
      <p className="text-muted-foreground">{t('templates.hidden.hint')}</p>
    </section>
  );
}
