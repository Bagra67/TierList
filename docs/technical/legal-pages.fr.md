# Pages légales

[English](legal-pages.md) | Français

Les pages qui expliquent aux utilisateurs comment TierList traite leurs données et les règles du service. Elles sont lisibles sans compte. Seule la politique de confidentialité existe aujourd'hui (#200) ; les conditions d'utilisation arrivent avec #201.

## 1. Politique de confidentialité

| Élément    | Où                                                                                                                                                                                                                                       |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Page       | `/privacy` (`ROUTES.PRIVACY`), `frontend/src/pages/PrivacyPolicyPage.tsx`. Route publique dans `App.tsx`, hors de `RequireAuth`.                                                                                                         |
| Texte      | Traductions `privacy.*` dans `frontend/src/i18n/locales/fr.ts` (référence) et `en.ts`. Une clé par paragraphe ou élément de liste, nommée dans la page : pas de `returnObjects`, le test de parité des clés couvre donc tout le texte.   |
| Constantes | `frontend/src/constants/legal.ts` : nom du responsable, adresse de contact, date de la dernière mise à jour (`PRIVACY_POLICY_UPDATED_AT`), page de réclamation de la CNIL.                                                               |
| Liens      | `components/SiteFooter.tsx`, dans le pied de page de toutes les pages (`Layout.tsx`) : connexion, inscription, invité dans une salle, résultats publics. Aussi dans le panneau de paramètres, section « Informations », connecté ou non. |

Le texte a été rédigé à partir du code (inventaire des données de #200) et validé par le responsable du produit. Ce n'est pas un avis juridique.

## 2. Garder la politique à jour

**Mettre à jour la politique dans la même PR** que tout changement de ce qu'elle décrit :

- un nouveau type de donnée personnelle collectée, ou une donnée collectée pour une nouvelle finalité ;
- une durée de conservation (`REFRESH_TOKEN_TTL_DAYS`, `GUEST_LINK_TTL_DAYS`, `DELETED_TEMPLATE_RETENTION_DAYS`, `UNUSED_IMAGE_RETENTION_DAYS`, `ROOM_INACTIVITY_HOURS`, `BACKUP_RETENTION_DAYS`, la durée des liens envoyés par email) ;
- un nouveau prestataire, ou un prestataire dans un nouveau pays ([guide du déploiement](deployment.fr.md)) ;
- un nouveau cookie ou une nouvelle clé de stockage local (un cookie de mesure d'audience demanderait aussi un bandeau de consentement) ;
- ce que les autres utilisateurs peuvent voir (salles, liens de résultats, historique).

Ensuite :

1. changer le texte dans `fr.ts` **et** `en.ts` ;
2. mettre `PRIVACY_POLICY_UPDATED_AT` à la date du changement ;
3. pour un changement important, prévenir les utilisateurs dans l'application, comme la politique le promet.

L'export des données dans l'application (#202) devra être ajouté à la section « Vos droits » une fois construit.

## 3. Tests

Décrits dans le [guide des tests](testing.fr.md) : `src/pages/PrivacyPolicyPage.test.tsx` (la page sans compte, ses sections, les liens de contact et de la CNIL, l'anglais), le lien du pied de page dans `src/App.test.tsx` et celui du panneau de paramètres dans `src/components/SettingsPanel.test.tsx`. Les vérifications de parité et de textes non vides de `src/i18n/i18n.test.ts` couvrent le texte.
