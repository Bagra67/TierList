import {
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  type SensorDescriptor,
  type SensorOptions,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { type RefObject, useEffect, useRef } from 'react';

// Hooks communs au plateau des tours (GameBoard) et au plateau du cooldown (CooldownBoard)

// Distance (px) avant qu'un appui de souris devienne un glisser : un simple clic ne pose rien
const MOUSE_DRAG_DISTANCE = 8;
// Au doigt, un appui long saisit la tuile ; un balayage fait défiler la page
const TOUCH_DRAG_DELAY_MS = 200;
const TOUCH_DRAG_TOLERANCE = 5;

// Capteurs des plateaux : souris, doigt et clavier
export function useBoardSensors(): SensorDescriptor<SensorOptions>[] {
  return useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: MOUSE_DRAG_DISTANCE } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: TOUCH_DRAG_DELAY_MS, tolerance: TOUCH_DRAG_TOLERANCE },
    }),
    useSensor(KeyboardSensor),
  );
}

// Rend le focus après une action du plateau : la tuile déplacée change de rangée et son bouton
// est remonté, le focus du clavier serait perdu. request(clés) : le premier élément
// [data-focus-key] trouvé et actif reçoit le focus quand trigger change (la réponse du serveur).
export function useFocusAfterUpdate(
  container: RefObject<HTMLElement | null>,
  trigger: unknown,
): { request: (keys: string[]) => void; cancel: () => void } {
  const wanted = useRef<string[] | null>(null);

  useEffect(() => {
    const keys: string[] | null = wanted.current;
    if (keys === null) return;
    wanted.current = null;
    for (const key of keys) {
      const element: HTMLElement | null | undefined = container.current?.querySelector(
        `[data-focus-key="${key}"]`,
      );
      if (element instanceof HTMLElement && !element.hasAttribute('disabled')) {
        element.focus();
        return;
      }
    }
  }, [container, trigger]);

  return {
    request: (keys: string[]) => {
      wanted.current = keys;
    },
    cancel: () => {
      wanted.current = null;
    },
  };
}
