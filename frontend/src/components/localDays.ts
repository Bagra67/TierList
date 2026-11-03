export function startOfDay(day: string): string {
  return new Date(`${day}T00:00:00`).toISOString();
}

// Début du jour suivant : le jour choisi est inclus en entier
export function startOfNextDay(day: string): string {
  const next: Date = new Date(`${day}T00:00:00`);
  next.setDate(next.getDate() + 1);
  return next.toISOString();
}

export function today(): string {
  const now: Date = new Date();
  const month: string = String(now.getMonth() + 1).padStart(2, '0');
  const date: string = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${date}`;
}
