import type { MarketplaceTemplate } from '../../api/marketplace';

export function marketplaceCard(
  id: string,
  name: string,
  overrides: Partial<MarketplaceTemplate> = {},
): MarketplaceTemplate {
  return {
    id,
    name,
    owner_name: 'Camille',
    featured: false,
    tags: ['Apéro'],
    tile_count: 8,
    like_count: 3,
    preview_image_url: null,
    preview_image_removed: false,
    tier_colors: ['#FF3B6B', '#FF8A2A'],
    ...overrides,
  };
}
