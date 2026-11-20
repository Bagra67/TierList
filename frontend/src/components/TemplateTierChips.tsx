import { tierColorStyle } from './boardStyles';

export interface TierChip {
  id: string;
  name: string;
  color: string;
}

export function TemplateTierChips({ tiers }: { tiers: TierChip[] }) {
  return (
    <ol className="flex flex-wrap gap-2">
      {tiers.map((tier: TierChip) => (
        <li
          key={tier.id}
          style={tierColorStyle(tier.color)}
          className="rounded-md px-2 py-1 font-semibold break-words"
        >
          {tier.name}
        </li>
      ))}
    </ol>
  );
}
