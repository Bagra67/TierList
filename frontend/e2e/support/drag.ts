import type { Locator, Page } from '@playwright/test';

const START_NUDGE_PX: number = 10;
const DRAG_STEPS: number = 12;

interface Point {
  x: number;
  y: number;
}

async function nextFrame(page: Page): Promise<void> {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
}

async function moveFrameByFrame(page: Page, from: Point, to: Point, steps: number): Promise<void> {
  for (let step = 1; step <= steps; step += 1) {
    await page.mouse.move(
      from.x + ((to.x - from.x) * step) / steps,
      from.y + ((to.y - from.y) * step) / steps,
    );
    await nextFrame(page);
  }
}

export async function dragWithMouse(page: Page, source: Locator, target: Locator): Promise<void> {
  const from = await source.boundingBox();
  const to = await target.boundingBox();
  if (from === null || to === null) throw new Error('drag source or target is not visible');
  const start: Point = { x: from.x + from.width / 2, y: from.y + from.height / 2 };
  const end: Point = { x: to.x + to.width / 2, y: to.y + to.height / 2 };
  const activated: Point = { x: start.x, y: start.y + START_NUDGE_PX };

  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await moveFrameByFrame(page, start, activated, 2);
  await moveFrameByFrame(page, activated, end, DRAG_STEPS);
  await nextFrame(page);
  await page.mouse.up();
}
