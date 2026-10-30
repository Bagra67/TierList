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

// Hooks communs au plateau des tours (GameBoard) et au plateau du cooldown (CooldownBoard)

// Distance (px) avant qu'un appui de souris devienne un glisser : un simple clic ne pose rien
const MOUSE_DRAG_DISTANCE = 8;
// Au doigt, un appui long saisit la tuile ; un balayage fait défiler la page
const TOUCH_DRAG_DELAY_MS = 200;
const TOUCH_DRAG_TOLERANCE = 5;

// Au clavier, Espace ou Entrée saisit l'item, les flèches le déplacent, Espace ou Entrée le dépose
const DEFAULT_KEYBOARD_CODES: KeyboardCodes = {
  start: [KeyboardCode.Space, KeyboardCode.Enter],
  cancel: [KeyboardCode.Esc],
  end: [KeyboardCode.Space, KeyboardCode.Enter],
};

// Sur le plateau final, Entrée (le clic) choisit la tuile pour « Déplacer ici » : seul Espace la
// saisit pour la glisser
export const COOLDOWN_KEYBOARD_CODES: KeyboardCodes = {
  ...DEFAULT_KEYBOARD_CODES,
  start: [KeyboardCode.Space],
};

// Capteurs des plateaux : souris, doigt et clavier
export function useBoardSensors(
  keyboardCodes: KeyboardCodes = DEFAULT_KEYBOARD_CODES,
): SensorDescriptor<SensorOptions>[] {
  return useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: MOUSE_DRAG_DISTANCE } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: TOUCH_DRAG_DELAY_MS, tolerance: TOUCH_DRAG_TOLERANCE },
    }),
    useSensor(KeyboardSensor, { keyboardCodes }),
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

// Clé de focus d'une tuile du plateau final : elle garde le focus après un déplacement, même dans
// une autre rangée (useFocusAfterUpdate)
export function tileFocusKey(itemId: string): string {
  return `${itemId}:tile`;
}
