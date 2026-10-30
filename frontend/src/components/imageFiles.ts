import { ACCEPTED_IMAGE_TYPES } from '../constants/images';

// Un fichier d'un type connu autre que JPEG, PNG ou WebP est refusé sans être envoyé. Un type
// vide veut dire que le système ne le connaît pas (ex. .webp sur un Windows ancien) : le fichier
// part au backend, qui reconnaît le format d'après son contenu
export function isAcceptedImageFile(file: File): boolean {
  return file.type === '' || ACCEPTED_IMAGE_TYPES.includes(file.type);
}
