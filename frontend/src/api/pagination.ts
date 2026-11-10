interface PageWithMore {
  has_more: boolean;
}

export function nextOffset<Page extends PageWithMore>(
  itemsOf: (page: Page) => readonly unknown[],
): (lastPage: Page, pages: Page[]) => number | undefined {
  return (lastPage: Page, pages: Page[]) =>
    lastPage.has_more
      ? pages.reduce((count: number, page: Page) => count + itemsOf(page).length, 0)
      : undefined;
}
