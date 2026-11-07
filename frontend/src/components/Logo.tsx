import { Link } from 'react-router';

import { LOGO_BARS, LOGO_VIEWBOX_SIZE } from '../constants/brand';
import { ROUTES } from '../constants/routes';

export function Logo() {
  return (
    <Link
      to={ROUTES.HOME}
      className="flex items-center gap-2 rounded-md font-heading text-xl font-black font-stretch-125%"
    >
      <svg
        aria-hidden="true"
        viewBox={`0 0 ${LOGO_VIEWBOX_SIZE} ${LOGO_VIEWBOX_SIZE}`}
        className="size-6 shrink-0"
      >
        {LOGO_BARS.map((bar, index) => (
          <rect
            key={bar.color}
            x={1}
            y={2 + index * 7}
            width={bar.widthInViewBox}
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
