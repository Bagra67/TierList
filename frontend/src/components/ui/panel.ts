import { cva } from 'class-variance-authority';

export const panelVariants = cva('flex w-full flex-col rounded-panel', {
  variants: {
    variant: {
      solid: 'gap-2 border bg-card p-4',
      dashed: 'gap-2 border-2 border-dashed p-4',
      list: 'divide-y overflow-hidden border bg-card',
      muted: 'gap-2 bg-muted p-4',
    },
  },
  defaultVariants: {
    variant: 'solid',
  },
});
