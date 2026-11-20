import { useId } from 'react';

import { type DayRange } from './localDays';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface DayRangeFieldsProps {
  range: DayRange;
  onChange: (range: DayRange) => void;
  fromLabel: string;
  toLabel: string;
}

export function DayRangeFields({ range, onChange, fromLabel, toLabel }: DayRangeFieldsProps) {
  const fromId: string = useId();
  const toId: string = useId();
  return (
    <>
      <div className="flex flex-col gap-2">
        <Label htmlFor={fromId}>{fromLabel}</Label>
        <Input
          id={fromId}
          type="date"
          value={range.fromDay}
          max={range.toDay === '' ? undefined : range.toDay}
          onChange={(event) => onChange({ ...range, fromDay: event.target.value })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={toId}>{toLabel}</Label>
        <Input
          id={toId}
          type="date"
          value={range.toDay}
          min={range.fromDay === '' ? undefined : range.fromDay}
          onChange={(event) => onChange({ ...range, toDay: event.target.value })}
        />
      </div>
    </>
  );
}
