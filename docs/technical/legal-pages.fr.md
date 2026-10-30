# Pages légales

[English](legal-pages.md) | Français

Les pages qui expliquent aux utilisateurs comment TierList traite leurs données, les règles du service et qui l'édite. Elles sont lisibles sans compte : la politique de confidentialité (#200), les conditions d'utilisation (#201) et les mentions légales (#235), avec une section pour signaler un contenu illicite (#236).

## 1. Les pages

| Page                         | Route (`ROUTES`)                       | Composant                             | Texte (`fr.ts` référence, `en.ts`) | Date (`constants/legal.ts`) |
| ---------------------------- | -------------------------------------- | ------------------------------------- | ---------------------------------- | --------------------------- |
| Politique de confidentialité | `/privacy` (`PRIVACY`)                 | `pages/PrivacyPolicyPage.tsx`         | `privacy.*`                        | `PRIVACY_POLICY_UPDATED_AT` |
| Conditions d'utilisation     | `/terms` (`TERMS`)                     | `pages/TermsPage.tsx`                 | `terms.*`                          | `TERMS_UPDATED_AT`          |
| Mentions légales             | `/legal` (`LEGAL_NOTICE`)              | `pages/LegalNoticePage.tsx`           | `legalNotice.*`                    | `LEGAL_NOTICE_UPDATED_AT`   |
| Signaler un contenu          | section des conditions et des mentions | `components/ReportContentSection.tsx` | `legalPages.report.*`              | —                           |

| Élément      | Où                                                                                                                                                                                                                                                                                                                            |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes       | Publiques, dans `App.tsx`, hors de `RequireAuth`.                                                                                                                                                                                                                                                                             |
| Mise en page | `components/LegalPage.tsx` : `LegalPage` (titre, date de la dernière mise à jour avec `legalPages.updatedAt`, introduction), `LegalSection` et `LegalList`, communs aux trois pages.                                                                                                                                          |
| Texte        | Une clé par paragraphe ou élément de liste, nommée dans la page : pas de `returnObjects`, le test de parité des clés couvre donc tout le texte. Une phrase avec un lien passe par `Trans` et des balises nommées (`<privacy>…</privacy>`), jamais par des morceaux assemblés.                                                 |
| Constantes   | `frontend/src/constants/legal.ts` : nom de l'éditeur et responsable du traitement, adresse de contact (`LEGAL_CONTACT_EMAIL`, aussi pour les demandes RGPD et les signalements), hébergeur (`LEGAL_HOST_*`, relevé dans les mentions légales de MineStrator), date de chaque page, page de réclamation de la CNIL.            |
| Liens        | `components/LegalLinks.tsx`, les trois pages : dans le pied de page de toutes les pages (`SiteFooter`, dans `Layout.tsx` : connexion, inscription, invité dans une salle, résultats publics) et dans le panneau de paramètres, section « Informations », connecté ou non.                                                     |
| Acceptation  | `components/TermsAcceptance.tsx` : sous le formulaire d'inscription, et sous « Continuer avec Google » sur la connexion (Google peut créer le compte), une phrase dit que créer un compte vaut acceptation des conditions et de la politique de confidentialité, avec les deux liens. Rien n'est enregistré (#201, option a). |

Les textes ont été rédigés à partir du code (inventaire des données de #200, périmètre de #201) et validés par le responsable du produit. Ce n'est pas un avis juridique.

### Éditeur et hébergeur

- L'éditeur est une personne physique, à titre non professionnel : les mentions donnent son nom et son e-mail, pas son adresse, comme le permet l'article 6-III-2 de la LCEN (ses coordonnées sont connues de l'hébergeur).
- L'hébergeur est OctoGency SARL (MineStrator), dont les coordonnées viennent de [ses mentions légales](https://minestrator.com/mentions/legales). Les revérifier quand l'hébergement change ([guide du déploiement](deployment.fr.md)).

### Signalements

Un contenu illicite se signale par e-mail à `LEGAL_CONTACT_EMAIL`, en attendant le signalement dans l'application (#126). La section dit quoi indiquer (lien, contenu, motif, une adresse pour répondre) et la suite (retrait, suspension ou suppression du compte, à la main pour l'instant). La politique de confidentialité décrit les données d'un signalement et leur durée de conservation.

## 2. Garder les pages à jour

**Mettre à jour la politique de confidentialité dans la même PR** que tout changement de ce qu'elle décrit (AGENTS.md §51 : vérifié à chaque changement) :

- un nouveau type de donnée personnelle collectée, ou une donnée collectée pour une nouvelle finalité ;
- une durée de conservation (`REFRESH_TOKEN_TTL_DAYS`, `GUEST_LINK_TTL_DAYS`, `DELETED_TEMPLATE_RETENTION_DAYS`, `UNUSED_IMAGE_RETENTION_DAYS`, `ROOM_INACTIVITY_HOURS`, `BACKUP_RETENTION_DAYS`, la durée des liens envoyés par email) ;
- un nouveau prestataire, ou un prestataire dans un nouveau pays ([guide du déploiement](deployment.fr.md)) ;
- un nouveau cookie ou une nouvelle clé de stockage local (un cookie de mesure d'audience demanderait aussi un bandeau de consentement) ;
- ce que les autres utilisateurs peuvent voir (salles, liens de résultats, historique).

**Mettre à jour les conditions d'utilisation** quand une règle qu'elles décrivent change (validité du lien invité, ce que voient les autres, règles des contenus, modération), et **les mentions légales** quand l'éditeur, l'hébergeur ou un prestataire change.

Ensuite :

1. changer le texte dans `fr.ts` **et** `en.ts` ;
2. mettre la date de la page (`PRIVACY_POLICY_UPDATED_AT`, `TERMS_UPDATED_AT` ou `LEGAL_NOTICE_UPDATED_AT`) à la date du changement ;
3. pour un changement important, prévenir les utilisateurs dans l'application, comme la politique et les conditions le promettent.

L'export des données dans l'application (#202) devra être ajouté à la section « Vos droits » de la politique une fois construit.

## 3. Tests

Décrits dans le [guide des tests](testing.fr.md) : `src/pages/PrivacyPolicyPage.test.tsx`, `TermsPage.test.tsx` et `LegalNoticePage.test.tsx` (chaque page sans compte, ses sections, ses liens, l'anglais), les liens du pied de page dans `src/App.test.tsx`, ceux du panneau de paramètres dans `src/components/SettingsPanel.test.tsx`, et la phrase d'acceptation dans `src/pages/LoginPage.test.tsx` et `RegisterPage.test.tsx`. Les vérifications de parité et de textes non vides de `src/i18n/i18n.test.ts` couvrent le texte.
