import { ACCEPTED_IMAGE_TYPES } from '../constants/images';

export function isAcceptedImageFile(file: File): boolean {
  return file.type === '' || ACCEPTED_IMAGE_TYPES.includes(file.type);
}
