import type { Tile } from '../api/templates';

export function hasImageEvenIfRemoved(tile: Tile): boolean {
  return tile.image_url !== null || tile.image_removed;
}
