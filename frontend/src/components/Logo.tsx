import { Link } from 'react-router';

import { LOGO_BARS } from '../constants/brand';
import { ROUTES } from '../constants/routes';

// Logo de l'en-tête : trois barres empilées aux couleurs des tiers S, A et B, puis le nom du
// produit. Le dessin est décoratif : le nom suffit comme intitulé du lien vers l'accueil.
export function Logo() {
  return (
    <Link
      to={ROUTES.HOME}
      className="flex items-center gap-2 rounded-md font-heading text-xl font-black font-stretch-125%"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6 shrink-0">
        {LOGO_BARS.map((bar, index) => (
          <rect
            key={bar.color}
            x={1}
            y={2 + index * 7}
            width={bar.width}
            height={6}
            rx={1.5}
            fill={bar.color}
          />
        ))}
      </svg>
      TierList
    </Link>
  );
}
