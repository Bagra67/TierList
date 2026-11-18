import { Heart } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { MarketplaceTemplate } from '../api/marketplace';
import { publicTemplatePath } from '../constants/routes';
import { RemovedImage } from './RemovedImage';
import { TemplateTagList } from './TemplateTagList';

const TIER_BAR_WIDTH_STEP_PERCENT = 12;
const TIER_BAR_MIN_WIDTH_PERCENT = 28;

function tierBarWidth(index: number): string {
  return `${Math.max(100 - index * TIER_BAR_WIDTH_STEP_PERCENT, TIER_BAR_MIN_WIDTH_PERCENT)}%`;
}

function CardPreview({ template }: { template: MarketplaceTemplate }) {
  if (template.preview_image_url !== null) {
    return <img src={template.preview_image_url} alt="" className="size-full object-cover" />;
  }
  if (template.preview_image_removed) {
    return <RemovedImage className="size-full" showLabel />;
  }
  return (
    <div aria-hidden="true" className="flex size-full flex-col justify-center gap-1.5 bg-muted p-4">
      {template.tier_colors.map((color: string, index: number) => (
        <span
          key={`${index}-${color}`}
          className="h-2.5 rounded-full"
          style={{ backgroundColor: color, width: tierBarWidth(index) }}
        />
      ))}
    </div>
  );
}

export function MarketplaceCard({ template }: { template: MarketplaceTemplate }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <li className="relative flex flex-col overflow-hidden rounded-panel border bg-card focus-within:ring-3 focus-within:ring-ring">
      <div className="aspect-[2/1] w-full overflow-hidden border-b">
        <CardPreview template={template} />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="font-semibold break-words">
          <Link
            to={publicTemplatePath(template.id)}
            className="outline-none after:absolute after:inset-0 hover:underline"
          >
            {template.name}
          </Link>
        </h3>
        <p className="text-sm text-muted-foreground">
          {t('marketplace.card.byline', {
            owner: template.owner_name,
            count: template.tile_count,
          })}
        </p>
        <TemplateTagList tags={template.tags} />
        <p className="mt-auto flex items-center justify-end gap-1.5 text-sm font-medium text-primary tabular-nums">
          <Heart aria-hidden="true" className="size-4" />
          {t('publicTemplate.like.count', { count: template.like_count })}
        </p>
      </div>
    </li>
  );
}
