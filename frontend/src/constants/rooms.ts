// Clés du cache TanStack Query des salles (cf. constants/templates.ts) : une salle ouverte est
// rangée sous ['rooms', <code>]. Les bornes des durées ne sont pas recopiées ici : le backend les
// renvoie dans ses erreurs de validation (params ge / le), affichées telles quelles.
export const ROOMS_QUERY_KEY: readonly ['rooms'] = ['rooms'];

// Le lien perso d'un invité porte son jeton dans le fragment : /r/<code>#guest=<jeton> (backend :
// GUEST_LINK_FRAGMENT). Le fragment n'est jamais envoyé au serveur.
export const GUEST_LINK_FRAGMENT: string = 'guest';

export type RoomQueryKey = readonly ['rooms', string];

export function roomQueryKey(code: string): RoomQueryKey {
  return [...ROOMS_QUERY_KEY, code];
}
