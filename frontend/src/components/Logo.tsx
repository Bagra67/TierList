import { Link } from 'react-router';

import { LOGO_BAR_COLORS } from '../constants/brand';
import { ROUTES } from '../constants/routes';

// Largeur de chaque barre (sur 24) : de plus en plus courtes, comme le haut d'une tier list
const LOGO_BAR_WIDTHS = [22, 16, 10] as const;

// Logo de l'en-tête : trois barres empilées aux couleurs des tiers S, A et B, puis le nom du
// produit. Le dessin est décoratif : le nom suffit comme intitulé du lien vers l'accueil.
export function Logo() {
  return (
    <Link
      to={ROUTES.HOME}
      className="flex items-center gap-2 rounded-md font-heading text-xl font-black [font-stretch:125%]"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6 shrink-0">
        {LOGO_BAR_COLORS.map((color, index) => (
          <rect
            key={color}
            x={1}
            y={2 + index * 7}
            width={LOGO_BAR_WIDTHS[index]}
            height={6}
            rx={1.5}
            fill={color}
          />
        ))}
      </svg>
      TierList
    </Link>
  );
}
