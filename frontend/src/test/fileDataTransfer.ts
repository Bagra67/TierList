export interface FileDataTransfer {
  files: File[];
  types: string[];
  dropEffect: string;
}

export function fileDataTransfer(...files: File[]): FileDataTransfer {
  return { files, types: ['Files'], dropEffect: 'none' };
}
