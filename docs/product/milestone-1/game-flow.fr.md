# Jalon 1 — Déroulé

[English](game-flow.md) | Français

Qui fait quoi, et dans quel ordre, dans le [jalon 1](README.fr.md) : de la création d'un template au partage des résultats. Les diagrammes montrent des **échanges métier** entre les acteurs et l'application, pas des appels techniques. États : [lifecycles.fr.md](lifecycles.fr.md). Stories : [user-stories.fr.md](user-stories.fr.md).

Acteurs : **Admin** (admin de la room, ici aussi propriétaire du template), **Joueur** (participant avec un compte), **Invité** (participant sans compte), **Visiteur** (n'importe qui avec le lien public), **Appli** (TierList).

## 1. Préparer un template

```mermaid
sequenceDiagram
    actor Admin
    participant Appli
    Admin->>Appli: Créer un template « Chips » (US-1.1)
    Appli-->>Admin: Template privé, tiers S A B C D E, sans tuile
    loop Pour chaque item (32 max)
        Admin->>Appli: Ajouter une tuile : texte et/ou image (US-1.2)
        Appli->>Appli: Compresser l'image
        Appli-->>Admin: Tuile ajoutée à la fin
    end
    Admin->>Appli: Renommer, recolorer, réordonner les tiers (US-1.4)
    Admin->>Appli: Réordonner les tuiles (US-1.3)
```

## 2. Créer une room et réunir les joueurs

```mermaid
sequenceDiagram
    actor Admin
    actor Joueur
    actor Invite as Invité
    participant Appli
    Admin->>Appli: Créer une room à partir de « Chips » (US-2.1)
    Appli-->>Admin: Room ouverte : lien + code
    Admin->>Appli: Réglages : ordre aléatoire, timer 30 s, cooldown 60 s, je joue, arrivées acceptées (US-2.2)
    Admin-->>Joueur: Partage le lien (hors de l'appli)
    Admin-->>Invite: Partage le code (hors de l'appli)
    Joueur->>Appli: Ouvrir le lien, connecté (US-2.4)
    Appli-->>Joueur: Place dans la room, affiché avec son nom
    Invite->>Appli: Saisir le code et un pseudo (US-2.5)
    Appli-->>Invite: Place dans la room + lien perso d'invité
    Appli-->>Admin: Salon mis à jour : 3 participants sur 10
```

## 3. Jouer les tours

```mermaid
sequenceDiagram
    actor Admin
    actor Joueur
    actor Invite as Invité
    participant Appli
    Admin->>Appli: Lancer la partie (US-3.1)
    Appli->>Appli: Figer le template, mélanger les items
    loop Pour chaque item
        Appli-->>Admin: Item n sur N (+ timer)
        Appli-->>Joueur: Item n sur N (+ timer)
        Appli-->>Invite: Item n sur N (+ timer)
        Joueur->>Appli: Déposer l'item dans le tier A, position 2 (US-3.3)
        Appli-->>Admin: Joueur a placé (pas où)
        Invite->>Appli: Déposer l'item dans le tier S, position 1
        Appli-->>Admin: Invité a placé
        alt L'admin clique sur suivant
            Admin->>Appli: Suivant (US-3.4)
        else Le timer est écoulé
            Appli->>Appli: Terminer le tour
        else Tous les connectés ont placé
            Appli->>Appli: Terminer le tour
        end
        Appli->>Appli: Vote absent pour qui n'a pas placé (US-4.3)
    end
    Appli-->>Admin: Le cooldown final commence
```

## 4. Déconnexion, arrivée en retard et rattrapage

```mermaid
sequenceDiagram
    actor Invite as Invité
    actor Retard as Joueur en retard
    participant Appli
    Note over Invite,Appli: Tour 3 en cours
    Invite--xAppli: Connexion perdue
    Appli->>Appli: Fin du tour 3 : vote absent pour l'invité
    Invite->>Appli: Revenir depuis le même navigateur (US-4.4)
    Appli->>Appli: Reconnaître l'invité par le cookie du navigateur
    Appli-->>Invite: Même place, même classement, tour 4
    Retard->>Appli: Rejoindre pendant le tour 5 (US-4.5)
    Appli-->>Retard: Place, les tours 1 à 4 comptent comme absents
    Note over Retard,Appli: L'admin de la room peut maintenant verrouiller les arrivées (US-2.10)
    Note over Invite,Appli: Cooldown final
    Appli-->>Invite: Item 3 manqué affiché à part (US-4.6)
    Invite->>Appli: Placer l'item 3 dans le tier B
    Appli-->>Retard: Items 1 à 4 manqués affichés à part
    Retard->>Appli: Les placer
```

## 5. Cooldown, clôture et résultats

```mermaid
sequenceDiagram
    actor Admin
    actor Joueur
    actor Visiteur
    participant Appli
    Appli-->>Joueur: Cooldown : compte à rebours, toutes les tuiles déplaçables (US-4.1)
    Joueur->>Appli: Déplacer l'item 7 de C vers A
    Appli->>Appli: Garder le placement du tour (C) et le final (A) (US-4.2)
    alt Le temps est écoulé
        Appli->>Appli: Terminer le cooldown
    else L'admin y met fin
        Admin->>Appli: Terminer le cooldown
    end
    Appli->>Appli: Clôturer et sauvegarder la partie (US-5.1)
    Appli-->>Admin: Résultats + lien public, room de nouveau ouverte
    Appli-->>Joueur: Résultats : chaque classement, vue globale, médiane (US-5.2)
    Joueur-->>Visiteur: Partage le lien public (hors de l'appli)
    Visiteur->>Appli: Ouvrir le lien public (US-5.3)
    Appli-->>Visiteur: Résultats, en lecture seule
    Admin->>Appli: Lancer une nouvelle partie dans la même room (US-2.9)
```
