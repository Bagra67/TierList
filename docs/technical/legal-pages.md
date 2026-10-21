# Legal pages

English | [Français](legal-pages.fr.md)

Pages that tell users how TierList handles their data and the rules of the service. They are readable without an account. Only the privacy policy exists today (#200); the terms of use come with #201.

## 1. Privacy policy

| Item      | Where                                                                                                                                                                                                           |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Page      | `/privacy` (`ROUTES.PRIVACY`), `frontend/src/pages/PrivacyPolicyPage.tsx`. Public route in `App.tsx`, outside `RequireAuth`.                                                                                    |
| Text      | Translations `privacy.*` in `frontend/src/i18n/locales/fr.ts` (reference) and `en.ts`. One key per paragraph or list item, named in the page: no `returnObjects`, so the key parity test covers the whole text. |
| Constants | `frontend/src/constants/legal.ts`: controller name, contact address, date of the last update (`PRIVACY_POLICY_UPDATED_AT`), CNIL complaint page.                                                                |
| Links     | `components/SiteFooter.tsx`, in the footer of every page (`Layout.tsx`): sign-in, sign-up, guest in a room, public results. Also in the settings panel, section "Informations" / "About", signed in or not.     |

The text was written from the code (data inventory of #200) and validated by the product owner. It is not legal advice.

## 2. Keeping the policy up to date

**Update the policy in the same PR** as any change to what it describes (AGENTS.md §51: checked for every change):

- a new kind of personal data collected, or data collected for a new purpose;
- a retention period (`REFRESH_TOKEN_TTL_DAYS`, `GUEST_LINK_TTL_DAYS`, `DELETED_TEMPLATE_RETENTION_DAYS`, `UNUSED_IMAGE_RETENTION_DAYS`, `ROOM_INACTIVITY_HOURS`, `BACKUP_RETENTION_DAYS`, the email link lifetimes);
- a new service provider, or a provider in a new country ([deployment guide](deployment.md));
- a new cookie or a new local storage key (an audience measurement cookie would also need a consent banner);
- what other users can see (rooms, results links, history).

Then:

1. change the text in **both** `fr.ts` and `en.ts`;
2. set `PRIVACY_POLICY_UPDATED_AT` to the date of the change;
3. for a significant change, tell the users in the application, as the policy promises.

The in-app data export (#202) will have to be added to the "Your rights" section once it is built.

## 3. Tests

Described in the [testing guide](testing.md): `src/pages/PrivacyPolicyPage.test.tsx` (the page without an account, its sections, the contact and CNIL links, English), the footer link in `src/App.test.tsx` and the settings panel link in `src/components/SettingsPanel.test.tsx`. The parity and non-empty checks of `src/i18n/i18n.test.ts` cover the text.
