import {
  KeyboardCode,
  type KeyboardCodes,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  type SensorDescriptor,
  type SensorOptions,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { type RefObject, useEffect, useRef } from 'react';

const MOUSE_DRAG_ACTIVATION_DISTANCE_PX = 8;
const TOUCH_LONG_PRESS_DELAY_MS = 200;
const TOUCH_LONG_PRESS_TOLERANCE_PX = 5;

const DEFAULT_KEYBOARD_CODES: KeyboardCodes = {
  start: [KeyboardCode.Space, KeyboardCode.Enter],
  cancel: [KeyboardCode.Esc],
  end: [KeyboardCode.Space, KeyboardCode.Enter],
};

export const ENTER_CHOOSES_TILE_KEYBOARD_CODES: KeyboardCodes = {
  ...DEFAULT_KEYBOARD_CODES,
  start: [KeyboardCode.Space],
};

export function useBoardSensors(
  keyboardCodes: KeyboardCodes = DEFAULT_KEYBOARD_CODES,
): SensorDescriptor<SensorOptions>[] {
  return useSensors(
    useSensor(MouseSensor, {
      activationConstraint: { distance: MOUSE_DRAG_ACTIVATION_DISTANCE_PX },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: TOUCH_LONG_PRESS_DELAY_MS,
        tolerance: TOUCH_LONG_PRESS_TOLERANCE_PX,
      },
    }),
    useSensor(KeyboardSensor, { keyboardCodes }),
  );
}

export function useFocusAfterUpdate(
  container: RefObject<HTMLElement | null>,
  serverUpdate: unknown,
): { focusFirstEnabledAfterUpdate: (focusKeysByPriority: string[]) => void; cancel: () => void } {
  const focusKeysToRestore = useRef<string[] | null>(null);

  useEffect(() => {
    const keys: string[] | null = focusKeysToRestore.current;
    if (keys === null) return;
    focusKeysToRestore.current = null;
    for (const key of keys) {
      const element: HTMLElement | null | undefined = container.current?.querySelector(
        `[data-focus-key="${key}"]`,
      );
      if (element instanceof HTMLElement && !element.hasAttribute('disabled')) {
        element.focus();
        return;
      }
    }
  }, [container, serverUpdate]);

  return {
    focusFirstEnabledAfterUpdate: (focusKeysByPriority: string[]) => {
      focusKeysToRestore.current = focusKeysByPriority;
    },
    cancel: () => {
      focusKeysToRestore.current = null;
    },
  };
}

export function tileFocusKey(itemId: string): string {
  return `${itemId}:tile`;
}
