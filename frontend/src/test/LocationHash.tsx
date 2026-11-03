import { useLocation } from 'react-router';

export function LocationHash() {
  return <p data-testid="location-hash">{useLocation().hash}</p>;
}
