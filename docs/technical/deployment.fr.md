# Déploiement

[English](deployment.md) | Français

Où TierList tourne et comment il se déploie automatiquement, avec un environnement de **staging** et un de **production**. Décidé dans le spike #155 ; **pas encore construit** : les issues d'implémentation sont listées au §5 (milestone Infrastructure).

## 1. Besoins et contraintes

| Besoin                | Détail                                                                                                                                                                                                                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend               | FastAPI avec **un seul worker** : le registre temps réel est en mémoire ([guide du temps réel](realtime.fr.md#29-montée-en-charge)). Un processus qui tourne en continu, pas du serverless.                                    |
| WebSocket             | Derrière TLS (`wss://`), avec un délai d'inactivité plus long que le battement de cœur de 10 s. Un redéploiement ferme les sockets ; les clients se reconnectent et relisent la salle ([guide du WebSocket](websocket.fr.md)). |
| Données               | PostgreSQL avec les migrations Alembic ; un stockage compatible S3 pour les images des tuiles ([guide des images](images.fr.md)).                                                                                              |
| Emails                | SMTP pour les emails de vérification et de réinitialisation du mot de passe ([guide des emails](emails.fr.md#4-en-production)), avec SPF, DKIM et DMARC.                                                                       |
| Frontend              | Build Vite statique, sur la même origine que l'API (`/api`), comme en développement.                                                                                                                                           |
| Budget et hébergement | Un **VPS** de préférence ; environ **20 €/mois** pour le staging et la production ensemble, stockage et emails compris (product owner, #155).                                                                                  |

La charge est faible pour l'instant : des salles de 10 participants au plus, quelques salles à la fois.

## 2. Options considérées

Prix vérifiés le **16/10/2026**. Les deux fournisseurs ont augmenté leurs prix en 2026 : à revérifier au moment de commander. HT = hors taxes.

### 2.1 Serveurs

| Fournisseur   | Offre                  | Taille                                  | Prix par mois                                         | Sauvegardes              | Remarques                                                                                                                                  |
| ------------- | ---------------------- | --------------------------------------- | ----------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **OVHcloud**  | VPS-1 (gamme VPS 2026) | 4 vCore, 8 Go de RAM, 75 Go, 400 Mbit/s | 7,79 € sans engagement (depuis le 1er avril 2026) [1] | Incluses [2]             | Entreprise française, centres de données dans l'UE, trafic illimité. Moins cher avec un engagement de 6 ou 12 mois.                        |
| Hetzner Cloud | CX23                   | 2 vCPU, 4 Go de RAM, 40 Go, 20 To       | 5,49 € HT + 0,50 € d'IPv4 [3]                         | +20 % du prix du serveur | Facturation à l'heure, bonne API. Au moment de la rédaction, les pages officielles affichaient les offres partagées **indisponibles** [4]. |
| Hetzner Cloud | CX33                   | 4 vCPU, 8 Go de RAM, 80 Go, 20 To       | 8,49 € HT + 0,50 € d'IPv4 [3]                         | +20 %                    | Même réserve sur la disponibilité.                                                                                                         |
| Scaleway      | DEV1-S                 | 2 vCPU, 2 Go de RAM                     | environ 6,55 € HT, stockage et IPv4 en plus [5]       | Snapshots en plus        | 2 Go, c'est juste pour PostgreSQL + backend + proxy.                                                                                       |

Un **PostgreSQL managé** est écarté : à lui seul, il prendrait l'essentiel du budget. PostgreSQL tourne dans un conteneur sur le serveur, avec des sauvegardes hors du serveur (§3.4).

### 2.2 Stockage et emails

| Besoin                         | Option                           | Prix                                                                  | Remarques                                                                                                                 |
| ------------------------------ | -------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Images, sauvegardes de la base | **Scaleway Object Storage**      | 0,01606 €/Go/mois HT (multi-AZ), 75 Go de sortie offerts par mois [6] | API S3, Paris. Les images sont de petits fichiers WebP : quelques centimes par mois. Hors des serveurs.                   |
| Images                         | SeaweedFS sur le serveur         | Disque du serveur                                                     | Déjà utilisé en développement, mais les images partagent alors le sort du serveur et demandent leurs propres sauvegardes. |
| Emails                         | **Scaleway Transactional Email** | 300 emails offerts par mois, puis 0,25 € HT les 1 000 [7]             | Sans abonnement, UE. Même compte que le stockage.                                                                         |
| Emails                         | Brevo                            | Offre gratuite : 300 emails par jour, relais SMTP [8]                 | Mention Brevo dans les emails de l'offre gratuite ; à garder en tête si le volume grandit.                                |

## 3. Décision

### 3.1 Hébergement

- **Deux VPS-1 OVHcloud**, un pour le **staging** et un pour la **production**. Des machines séparées : un déploiement ou un test sur le staging ne peut jamais ralentir ni casser la production. Avec les sauvegardes incluses et 8 Go de RAM, c'est l'offre qui colle le mieux au budget.
- **Alternative** : deux serveurs Hetzner CX23, si OVHcloud devient indisponible ou trop cher. L'installation ci-dessous reste la même : seules les machines changent.
- **Scaleway Object Storage** : un bucket par environnement pour les images (lecture publique), et un bucket privé pour les sauvegardes de la base.
- **Scaleway Transactional Email** pour les emails, avec le domaine autorisé (SPF, DKIM, DMARC).
- **Un nom de domaine** est nécessaire : `tierlist.<domaine>` pour la production, `staging.tierlist.<domaine>` pour le staging. Reste à choisir (§6).

Coût estimé : environ **16 €/mois** pour les deux serveurs, plus moins de 1 € de stockage et d'emails au volume actuel. Le domaine s'ajoute, à l'année.

### 3.2 Sur chaque serveur

```
Internet ──443──> Caddy ──┬── /api/*  ──> backend (uvicorn, 1 worker) ──> PostgreSQL
                          └── /*      ──> frontend (fichiers statiques)
                                           backend ──> Scaleway S3, Scaleway TEM
```

- **Docker Compose** avec trois services : `caddy`, `backend`, `postgres`.
- **Caddy** : certificats TLS automatiques (Let's Encrypt), proxy WebSocket sans configuration supplémentaire, sert le build du frontend (copié dans l'image Caddy), retire `/api` avant le backend comme le fait le proxy Vite en développement.
- **Backend** : uvicorn avec **un seul worker** ; les migrations Alembic passent avant son démarrage (§4).
- **PostgreSQL** : image officielle, données sur un volume Docker, pas exposé hors du serveur.
- **Durcissement du serveur** : clés SSH seulement, pare-feu ouvert sur 22, 80 et 443, mises à jour de sécurité automatiques.

### 3.3 Configuration et secrets

- Un **environment GitHub** par cible : `staging` et `production`. Chacun porte l'adresse du serveur, la clé SSH de déploiement et les secrets de l'application (`JWT_SECRET_KEY`, mot de passe de la base, clés S3, SMTP, Google OAuth).
- Le déploiement écrit le `.env` du serveur à partir de ces secrets : GitHub est le seul endroit où ils vivent, et un serveur peut être reconstruit de zéro.
- Par environnement : `FRONTEND_BASE_URL`, `GOOGLE_REDIRECT_URI` (HTTPS), `IMAGE_PUBLIC_BASE_URL` (le bucket public), `AUTH_COOKIE_SECURE=true`, une `JWT_SECRET_KEY` différente.
- `production` exige une **approbation manuelle** (relecteur requis) avant chaque déploiement.

### 3.4 Sauvegardes

- **Base** : un `pg_dump` chaque nuit, compressé, envoyé dans le bucket privé des sauvegardes. Gardé 14 jours en production, 3 jours en staging. Une restauration est testée une fois avant les premiers vrais utilisateurs, puis après toute mise à jour majeure de PostgreSQL.
- **Serveur** : la sauvegarde quotidienne d'OVHcloud (incluse) permet de restaurer une machine entière.
- **Images** : elles vivent dans le stockage objet, hors des serveurs.

## 4. Déploiement continu

| Événement                                                                 | Cible          | Approbation |
| ------------------------------------------------------------------------- | -------------- | ----------- |
| CI verte sur un push dans `develop` (une PR mergée)                       | **staging**    | aucune      |
| Tag `vX.Y.Z` créé par le workflow `Release` ([releases](releasing.fr.md)) | **production** | manuelle    |

Étapes d'un workflow de déploiement (`.github/workflows/deploy.yml`) :

1. **Construire** les images (`backend`, et `caddy` avec le build du frontend), les pousser sur le GitHub Container Registry (GHCR) avec le SHA du commit comme tag, plus `vX.Y.Z` pour une release.
2. **Se connecter** au serveur en SSH (clé de déploiement, clé d'hôte épinglée), écrire le `.env`, `docker compose pull`.
3. **Migrer** : `docker compose run --rm backend alembic upgrade head`. En cas d'échec, le déploiement s'arrête et la version en place continue de tourner.
4. **Redémarrer** : `docker compose up -d`. Les sockets ouverts sont fermés ; les clients se reconnectent seuls.
5. **Vérifier** : `GET /api/health` et `/api/health/db` doivent répondre `200` en moins d'une minute ; sinon le workflow échoue.

**Retour en arrière** : lancer le workflow à la main (`workflow_dispatch`) avec le tag précédent. Les migrations doivent rester compatibles avec la version précédente (ajouter une colonne d'abord, la retirer dans une release suivante) : un retour en arrière ne demande jamais de downgrade.

Deux déploiements de production ne tournent jamais en même temps (`concurrency` par environnement).

## 5. Issues d'implémentation

Milestone **Infrastructure** :

1. **Images de production et fichier Compose** (#158) : `Dockerfile` du backend, image Caddy avec le build du frontend et son `Caddyfile`, `deploy/compose.yaml`, health checks.
2. **Provisionnement des serveurs** (#159) : un script documenté et rejouable (utilisateurs, SSH, pare-feu, mises à jour automatiques, Docker), appliqué aux serveurs de staging et de production.
3. **Workflow de déploiement du staging** (#160) : GHCR, SSH, migrations, health checks, environment `staging`.
4. **Workflow de déploiement de la production** (#161) : déclenché par le tag de release, approbation manuelle, retour en arrière par `workflow_dispatch`.
5. **Sauvegardes de la base** (#162) : `pg_dump` chaque nuit vers le stockage objet, rétention, restauration documentée.
6. **Configuration de production** (#163) : domaine et DNS, SMTP (SPF, DKIM, DMARC), URI de redirection et écran de consentement Google OAuth, les points restants de `TODO.md`.

## 6. Questions ouvertes

- **Nom de domaine** : lequel, et chez quel registrar.
- **Engagement OVHcloud** : au mois (souple) ou sur 6 à 12 mois (moins cher), une fois l'installation stable.
- **Supervision** : un contrôle de disponibilité externe suffit au début ; à ajouter avec #160 ou #161 si on le souhaite.

## Sources

Vérifiées le 16/10/2026.

1. Next.ink, [OVHcloud augmente fortement le prix de ses VPS 2026 et IPv4](https://next.ink/225720/ovhcloud-augmente-fortement-le-prix-de-ses-vps-2026-et-ipv4/) (VPS-1 : 5,39 € → 7,79 € le 1er avril 2026, caractéristiques).
2. VPSBenchmarks, [VPS-1 2026 by OVHcloud](https://www.vpsbenchmarks.com/hosters/ovhcloud/plans/vps-1) (sauvegardes incluses dans la gamme VPS 2026). À confirmer sur [ovhcloud.com](https://www.ovhcloud.com/fr/vps/) au moment de commander.
3. CostGoat, [Hetzner pricing](https://costgoat.com/pricing/hetzner) (mis à jour le 5 septembre 2026 ; IPv4 +0,50 €, sauvegardes +20 %).
4. Hetzner, offres [Cost-Optimized](https://www.hetzner.com/cloud/cost-optimized/) et [Regular Performance](https://www.hetzner.com/cloud/regular-performance/).
5. Scaleway, [prix des Virtual Instances](https://www.scaleway.com/en/pricing/virtual-instances/).
6. Scaleway, [prix du stockage](https://www.scaleway.com/en/pricing/storage/).
7. Scaleway, [prix des services managés](https://www.scaleway.com/en/pricing/managed-services/) (Transactional Email).
8. Brevo, [tarifs](https://www.brevo.com/pricing/) (limites de l'offre gratuite d'après des avis tiers).
