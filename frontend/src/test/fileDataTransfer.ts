// Ce que porte l'événement d'un fichier glissé depuis l'ordinateur (dragenter, dragover, drop),
// à passer à fireEvent : jsdom n'a pas de vrai DataTransfer
export interface FileDataTransfer {
  files: File[];
  types: string[];
  dropEffect: string;
}

export function fileDataTransfer(file: File): FileDataTransfer {
  return { files: [file], types: ['Files'], dropEffect: 'none' };
}
