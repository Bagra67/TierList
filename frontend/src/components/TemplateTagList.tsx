import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';

export const tagPillClassName: string =
  'inline-flex max-w-full items-center rounded-full bg-secondary text-secondary-foreground';

interface TemplateTagListProps {
  tags: string[];
}

export function TemplateTagList({ tags }: TemplateTagListProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  if (tags.length === 0) return null;
  return (
    <ul aria-label={t('templates.tags.listLabel')} className="flex flex-wrap gap-1">
      {tags.map((tag) => (
        <li
          key={tag}
          className={cn(
            tagPillClassName,
            'px-2 py-0.5 text-xs font-medium break-words text-muted-foreground',
          )}
        >
          {tag}
        </li>
      ))}
    </ul>
  );
}
