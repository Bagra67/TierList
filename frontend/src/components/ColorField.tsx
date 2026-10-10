import { useEffect, useId, useRef, useState, type RefObject } from 'react';
import { HexColorInput, HexColorPicker } from 'react-colorful';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { TIER_COLOR_PRESETS } from '../constants/templates';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';

interface ColorFieldProps {
  label: string;
  // Couleur enregistrée, #RRGGBB en majuscules
  value: string;
  // Promesse rejetée si l'enregistrement échoue : la pastille revient alors à la couleur
  // enregistrée
  onSave: (color: string) => Promise<unknown>;
}

// #ABC → #AABBCC, en majuscules : le backend n'accepte que #RRGGBB
function toSixDigitHex(color: string): string {
  const digits: string = color.replace('#', '').toUpperCase();
  if (digits.length !== 3) return `#${digits}`;
  let expanded: string = '';
  for (const digit of digits) {
    expanded += digit + digit;
  }
  return `#${expanded}`;
}

// Pastille qui ouvre un sélecteur de couleur : nuancier (saturation et teinte), couleurs proposées
// et code hexadécimal. La pastille suit le choix en direct, mais la couleur n'est enregistrée
// qu'une fois, à la fermeture du sélecteur (clic en dehors ou OK) : glisser dans le nuancier
// n'envoie pas une requête par mouvement. Échap annule. Le parent lui donne key={value}.
export function ColorField({ label, value, onSave }: ColorFieldProps) {
  const [open, setOpen] = useState<boolean>(false);
  const [draft, setDraft] = useState<string>(value);
  // Vrai quand la fermeture vient d'Échap : on annule au lieu d'enregistrer
  const isCancelling: RefObject<boolean> = useRef<boolean>(false);
  // Nuancier affiché : le contenu du popover se monte après ce composant, d'où un état (le
  // changement relance l'effet de traduction) plutôt qu'une simple ref
  const [picker, setPicker] = useState<HTMLDivElement | null>(null);
  const presetsLabelId: string = useId();
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  // react-colorful écrit en dur ses libellés d'accessibilité en anglais (« Color », « Hue »,
  // « Saturation x%, Brightness y% »), sans prop pour les changer : on les remplace après chaque
  // rendu par les textes traduits.
  useEffect(() => {
    if (picker === null) return;
    const area: Element | null = picker.querySelector(
      '.react-colorful__saturation [role="slider"]',
    );
    const hue: Element | null = picker.querySelector('.react-colorful__hue [role="slider"]');
    if (area !== null) {
      area.setAttribute('aria-label', t('templates.editor.color.area'));
      const values: RegExpMatchArray | null = (area.getAttribute('aria-valuetext') ?? '').match(
        /(\d+)%.*?(\d+)%/,
      );
      if (values !== null) {
        area.setAttribute(
          'aria-valuetext',
          t('templates.editor.color.areaValue', { saturation: values[1], brightness: values[2] }),
        );
      }
    }
    hue?.setAttribute('aria-label', t('templates.editor.color.hue'));
  });

  function save() {
    const color: string = toSixDigitHex(draft);
    if (color === value) return;
    // L'erreur elle-même est affichée par le parent
    onSave(color).catch(() => setDraft(value));
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setDraft(value);
      return;
    }
    if (isCancelling.current) {
      isCancelling.current = false;
      setDraft(value);
      return;
    }
    save();
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={label}
          className="size-8 shrink-0 cursor-pointer rounded-full border-2 border-background ring-1 ring-foreground/20"
          style={{ backgroundColor: draft }}
        />
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-60"
        onEscapeKeyDown={() => {
          isCancelling.current = true;
        }}
      >
        <div ref={setPicker}>
          <HexColorPicker color={draft} onChange={setDraft} style={{ width: '100%' }} />
        </div>
        <p id={presetsLabelId} className="sr-only">
          {t('templates.editor.color.presets')}
        </p>
        <div role="group" aria-labelledby={presetsLabelId} className="grid grid-cols-6 gap-1.5">
          {TIER_COLOR_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              aria-label={t('templates.editor.color.preset', { color: preset })}
              aria-pressed={toSixDigitHex(draft) === preset}
              onClick={() => setDraft(preset)}
              className="aspect-square rounded-full ring-1 ring-foreground/20 aria-pressed:ring-2 aria-pressed:ring-foreground"
              style={{ backgroundColor: preset }}
            />
          ))}
        </div>
        <div className="flex items-center gap-2">
          <HexColorInput
            color={draft}
            onChange={setDraft}
            prefixed
            aria-label={t('templates.editor.color.hex')}
            className="h-8 min-w-0 flex-1 rounded-md border bg-transparent px-2 font-mono text-sm uppercase"
          />
          <Button type="button" size="sm" onClick={() => handleOpenChange(false)}>
            {t('templates.editor.color.done')}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
