// Clés du cache TanStack Query des salles (cf. constants/templates.ts) : une salle ouverte est
// rangée sous ['rooms', <code>]. Les bornes des durées ne sont pas recopiées ici : le backend les
// renvoie dans ses erreurs de validation (params ge / le), affichées telles quelles.
export const ROOMS_QUERY_KEY: readonly ['rooms'] = ['rooms'];

// À partir de ce nombre de secondes restantes, le chrono passe à la couleur de l'accent (manche et
// cooldown), et le cooldown final tremble
export const COUNTDOWN_URGENT_SECONDS: number = 5;

// Amplitude du tremblement du cooldown ajoutée à chaque seconde des dernières secondes, en pixels
export const COOLDOWN_SHAKE_STEP_PX: number = 0.5;

// Le lien perso d'un invité porte son jeton dans le fragment : /r/<code>#guest=<jeton> (backend :
// GUEST_LINK_FRAGMENT). Le fragment n'est jamais envoyé au serveur.
export const GUEST_LINK_FRAGMENT: string = 'guest';

// Code tel que le backend l'enregistre : un code tapé en minuscules ou avec des espaces ouvre la
// même salle (et le cookie d'un invité est posé sous le code canonique)
export function canonicalRoomCode(code: string): string {
  return code.trim().toUpperCase();
}

export type RoomQueryKey = readonly ['rooms', string];

export function roomQueryKey(code: string): RoomQueryKey {
  return [...ROOMS_QUERY_KEY, code];
}
