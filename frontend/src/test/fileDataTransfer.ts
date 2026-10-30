// Ce que porte l'événement d'un fichier glissé depuis l'ordinateur (dragenter, dragover, drop),
// à passer à fireEvent : jsdom n'a pas de vrai DataTransfer
export interface FileDataTransfer {
  files: File[];
  types: string[];
  dropEffect: string;
}

// Un ou plusieurs fichiers glissés ensemble
export function fileDataTransfer(...files: File[]): FileDataTransfer {
  return { files, types: ['Files'], dropEffect: 'none' };
}
