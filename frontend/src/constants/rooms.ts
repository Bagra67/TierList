export const ROOMS_QUERY_KEY: readonly ['rooms'] = ['rooms'];

export const COUNTDOWN_URGENT_SECONDS: number = 5;

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
