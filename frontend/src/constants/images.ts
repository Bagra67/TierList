// Types de fichiers proposés par le sélecteur et acceptés au dépôt : ceux que le backend accepte
// (docs/technical/images.md). Ce contrôle évite un aller-retour, le backend reste l'autorité.
export const ACCEPTED_IMAGE_TYPES: readonly string[] = ['image/jpeg', 'image/png', 'image/webp'];

// Ajout de plusieurs images d'un coup (useBulkImageTiles) : nombre d'images envoyées en même temps
export const BULK_IMAGE_UPLOAD_CONCURRENCY: number = 3;
