import { useLocation } from 'react-router';

// Fragment de l'adresse affichée, pour vérifier qu'un jeton en a été retiré
export function LocationHash() {
  return <p data-testid="location-hash">{useLocation().hash}</p>;
}
