# Legal pages

English | [Français](legal-pages.fr.md)

Pages that tell users how TierList handles their data, the rules of the service and who publishes it. They are readable without an account: the privacy policy (#200), the terms of use (#201) and the legal notice (#235), with a section to report illegal content (#236).

## 1. The pages

| Page           | Route (`ROUTES`)                             | Component                             | Text (`fr.ts` reference, `en.ts`) | Date (`constants/legal.ts`) |
| -------------- | -------------------------------------------- | ------------------------------------- | --------------------------------- | --------------------------- |
| Privacy policy | `/privacy` (`PRIVACY`)                       | `pages/PrivacyPolicyPage.tsx`         | `privacy.*`                       | `PRIVACY_POLICY_UPDATED_AT` |
| Terms of use   | `/terms` (`TERMS`)                           | `pages/TermsPage.tsx`                 | `terms.*`                         | `TERMS_UPDATED_AT`          |
| Legal notice   | `/legal` (`LEGAL_NOTICE`)                    | `pages/LegalNoticePage.tsx`           | `legalNotice.*`                   | `LEGAL_NOTICE_UPDATED_AT`   |
| Report content | section of the terms and of the legal notice | `components/ReportContentSection.tsx` | `legalPages.report.*`             | —                           |

| Item       | Where                                                                                                                                                                                                                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes     | Public, in `App.tsx`, outside `RequireAuth`.                                                                                                                                                                                                                                             |
| Layout     | `components/LegalPage.tsx`: `LegalPage` (title, date of the last update from `legalPages.updatedAt`, introduction), `LegalSection` and `LegalList`, shared by the three pages.                                                                                                           |
| Text       | One key per paragraph or list item, named in the page: no `returnObjects`, so the key parity test covers the whole text. A sentence with a link uses `Trans` with named tags (`<privacy>…</privacy>`), never fragments put together.                                                     |
| Constants  | `frontend/src/constants/legal.ts`: publisher and controller name, the contact address (`LEGAL_CONTACT_EMAIL`, also used for GDPR requests and reports), the host (`LEGAL_HOST_*`, taken from MineStrator's legal notice), the date of each page, the CNIL complaint page.                |
| Links      | `components/LegalLinks.tsx`, the three pages: in the footer of every page (`SiteFooter`, in `Layout.tsx`: sign-in, sign-up, guest in a room, public results) and in the settings panel, section "Informations" / "About", signed in or not.                                              |
| Acceptance | `components/TermsAcceptance.tsx`: under the sign-up form, and under "Continuer avec Google" on the sign-in page (Google may create the account), a sentence says that creating an account accepts the terms and the privacy policy, with both links. Nothing is stored (#201, option a). |

The texts were written from the code (data inventory of #200, scope of #201) and validated by the product owner. They are not legal advice.

### Publisher and host

- The publisher is an individual, publishing on a non-professional basis: the legal notice gives their name and email, not their address, as allowed by article 6-III-2 of the LCEN (their details are known to the host).
- The host is OctoGency SARL (MineStrator), whose details come from [its legal notice](https://minestrator.com/mentions/legales). Check them again when the hosting changes ([deployment guide](deployment.md)).

### Reports

Illegal content is reported by email to `LEGAL_CONTACT_EMAIL`, until the in-app reports (#126). The section says what to include (link, content, reason, an address to answer) and what happens next (removal, suspension or deletion of the account, done by hand for now). The privacy policy describes the data of a report and how long it is kept.

## 2. Keeping the pages up to date

**Update the privacy policy in the same PR** as any change to what it describes (AGENTS.md §51: checked for every change):

- a new kind of personal data collected, or data collected for a new purpose;
- a retention period (`REFRESH_TOKEN_TTL_DAYS`, `GUEST_LINK_TTL_DAYS`, `DELETED_TEMPLATE_RETENTION_DAYS`, `UNUSED_IMAGE_RETENTION_DAYS`, `ROOM_INACTIVITY_HOURS`, `BACKUP_RETENTION_DAYS`, the email link lifetimes);
- a new service provider, or a provider in a new country ([deployment guide](deployment.md));
- a new cookie or a new local storage key (an audience measurement cookie would also need a consent banner);
- what other users can see (rooms, results links, history).

**Update the terms of use** when a rule they describe changes (guest link validity, what others see, content rules, moderation), and **the legal notice** when the publisher, the host or a provider changes.

Then:

1. change the text in **both** `fr.ts` and `en.ts`;
2. set the date of the page (`PRIVACY_POLICY_UPDATED_AT`, `TERMS_UPDATED_AT` or `LEGAL_NOTICE_UPDATED_AT`) to the date of the change;
3. for a significant change, tell the users in the application, as the policy and the terms promise.

The in-app data export (#202) will have to be added to the "Your rights" section of the policy once it is built.

## 3. Tests

Described in the [testing guide](testing.md): `src/pages/PrivacyPolicyPage.test.tsx`, `TermsPage.test.tsx` and `LegalNoticePage.test.tsx` (each page without an account, its sections, its links, English), the footer links in `src/App.test.tsx`, the settings panel links in `src/components/SettingsPanel.test.tsx`, and the acceptance sentence in `src/pages/LoginPage.test.tsx` and `RegisterPage.test.tsx`. The parity and non-empty checks of `src/i18n/i18n.test.ts` cover the text.
