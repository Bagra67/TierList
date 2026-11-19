export function startOfDay(day: string): string {
  return new Date(`${day}T00:00:00`).toISOString();
}

export function exclusiveEndOfDay(day: string): string {
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

export interface DayRange {
  fromDay: string;
  toDay: string;
}

export const EMPTY_DAY_RANGE: DayRange = { fromDay: '', toDay: '' };

export interface DayRangeBounds {
  after: string | undefined;
  before: string | undefined;
}

export function dayRangeBounds({ fromDay, toDay }: DayRange): DayRangeBounds {
  return {
    after: fromDay === '' ? undefined : startOfDay(fromDay),
    before: toDay === '' ? undefined : exclusiveEndOfDay(toDay),
  };
}

export function isDayRangeSet({ fromDay, toDay }: DayRange): boolean {
  return fromDay !== '' || toDay !== '';
}
