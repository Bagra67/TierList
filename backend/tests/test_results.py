"""Exemples chiffrés de docs/technical/results.md, recalculés : la doc et le code donnent les mêmes
résultats. Tiers numérotés de haut en bas (0 = S)."""

import uuid
from fractions import Fraction

import pytest

from app.services.results import (
    FinalPlacement,
    GameResults,
    ItemResults,
    PlayerRanking,
    compute_results,
)

S: int = 0
A: int = 1
B: int = 2

PAPRIKA: uuid.UUID = uuid.uuid4()
BARBECUE: uuid.UUID = uuid.uuid4()
NATURE: uuid.UUID = uuid.uuid4()
VINAIGRE: uuid.UUID = uuid.uuid4()
X: uuid.UUID = uuid.uuid4()
Y: uuid.UUID = uuid.uuid4()
Z: uuid.UUID = uuid.uuid4()


def ranking(
    tiers: dict[int, list[uuid.UUID]], absent_tile_ids: frozenset[uuid.UUID] = frozenset()
) -> PlayerRanking:
    """Classement final d'un joueur, écrit tier par tier dans l'ordre des tuiles."""
    final_placements: dict[uuid.UUID, FinalPlacement] = {}
    for tier_index, tile_ids in tiers.items():
        for position, tile_id in enumerate(tile_ids):
            final_placements[tile_id] = FinalPlacement(tier_index=tier_index, position=position)
    return PlayerRanking(final_placements=final_placements, absent_tile_ids=absent_tile_ids)


def test_example_1_median_ranking_without_absent_votes() -> None:
    alice: PlayerRanking = ranking({S: [PAPRIKA, BARBECUE], A: [NATURE]})
    bob: PlayerRanking = ranking({S: [BARBECUE], A: [PAPRIKA, NATURE]})
    chloe: PlayerRanking = ranking({S: [PAPRIKA], A: [BARBECUE], B: [NATURE]})

    results: GameResults = compute_results(
        3, [PAPRIKA, BARBECUE, NATURE], [alice, bob, chloe], True
    )

    assert results.items[PAPRIKA] == ItemResults(
        votes_per_tier=(2, 1, 0),
        absent_count=0,
        median_score=Fraction(1, 2),
        mean_score=Fraction(2, 3),
        median_tier_index=S,
    )
    assert results.items[BARBECUE] == ItemResults(
        votes_per_tier=(2, 1, 0),
        absent_count=0,
        median_score=Fraction(3, 4),
        mean_score=Fraction(11, 12),
        median_tier_index=S,
    )
    assert results.items[NATURE] == ItemResults(
        votes_per_tier=(0, 2, 1),
        absent_count=0,
        median_score=Fraction(7, 4),
        mean_score=Fraction(23, 12),
        median_tier_index=A,
    )
    assert results.median_ranking == ((PAPRIKA, BARBECUE), (NATURE,), ())
    assert results.unranked_tile_ids == ()


def test_example_2_even_vote_count_keeps_the_worse_middle_tier() -> None:
    players: list[PlayerRanking] = [
        ranking({A: [PAPRIKA]}),
        ranking({A: [PAPRIKA]}),
        ranking({B: [PAPRIKA]}),
        ranking({B: [PAPRIKA]}),
    ]

    results: GameResults = compute_results(3, [PAPRIKA], players, True)

    assert results.items[PAPRIKA].median_score == Fraction(5, 2)
    assert results.items[PAPRIKA].median_tier_index == B
    assert results.median_ranking == ((), (), (PAPRIKA,))


@pytest.mark.parametrize(
    ("include_absent_votes", "expected_barbecue", "expected_ranking"),
    [
        (
            True,
            ItemResults(
                votes_per_tier=(1, 0, 1),
                absent_count=1,
                median_score=Fraction(5, 2),
                mean_score=Fraction(3, 2),
                median_tier_index=B,
            ),
            ((), (PAPRIKA,), (BARBECUE,)),
        ),
        (
            False,
            ItemResults(
                votes_per_tier=(1, 0, 0),
                absent_count=0,
                median_score=Fraction(1, 2),
                mean_score=Fraction(1, 2),
                median_tier_index=S,
            ),
            ((BARBECUE,), (PAPRIKA,), ()),
        ),
    ],
)
def test_example_3_absent_votes_with_and_without_the_toggle(
    include_absent_votes: bool,
    expected_barbecue: ItemResults,
    expected_ranking: tuple[tuple[uuid.UUID, ...], ...],
) -> None:
    alice: PlayerRanking = ranking({S: [BARBECUE], A: [PAPRIKA]})
    # Dan a raté Barbecue au tour et l'a rattrapé au cooldown, en B
    dan: PlayerRanking = ranking({S: [PAPRIKA], B: [BARBECUE]}, frozenset({BARBECUE}))
    # Eve a raté Barbecue et ne l'a jamais placé
    eve: PlayerRanking = ranking({A: [PAPRIKA]}, frozenset({BARBECUE}))

    results: GameResults = compute_results(
        3, [PAPRIKA, BARBECUE], [alice, dan, eve], include_absent_votes
    )

    assert results.items[BARBECUE] == expected_barbecue
    assert results.items[PAPRIKA] == ItemResults(
        votes_per_tier=(1, 2, 0),
        absent_count=0,
        median_score=Fraction(3, 2),
        mean_score=Fraction(7, 6),
        median_tier_index=A,
    )
    assert results.median_ranking == expected_ranking


@pytest.mark.parametrize(("include_absent_votes", "expected_absent_count"), [(True, 2), (False, 0)])
def test_example_4_an_item_nobody_placed_is_unranked(
    include_absent_votes: bool, expected_absent_count: int
) -> None:
    alice: PlayerRanking = ranking({S: [PAPRIKA]}, frozenset({VINAIGRE}))
    bob: PlayerRanking = ranking({A: [PAPRIKA]}, frozenset({VINAIGRE}))

    results: GameResults = compute_results(
        3, [PAPRIKA, VINAIGRE], [alice, bob], include_absent_votes
    )

    assert results.items[VINAIGRE] == ItemResults(
        votes_per_tier=(0, 0, 0),
        absent_count=expected_absent_count,
        median_score=None,
        mean_score=None,
        median_tier_index=None,
    )
    assert results.unranked_tile_ids == (VINAIGRE,)
    assert results.median_ranking == ((), (PAPRIKA,), ())


def test_example_5_equal_median_scores_are_ordered_by_mean_score() -> None:
    alice: PlayerRanking = ranking({A: [X, Y, Z]})
    bob: PlayerRanking = ranking({A: [Y, X, Z]})
    chloe: PlayerRanking = ranking({S: [Y, X, Z]})

    results: GameResults = compute_results(2, [X, Y, Z], [alice, bob, chloe], True)

    assert results.items[X].median_score == Fraction(7, 6)
    assert results.items[Y].median_score == Fraction(7, 6)
    assert results.items[X].mean_score == Fraction(19, 18)
    assert results.items[Y].mean_score == Fraction(17, 18)
    # Y passe avant X, pourtant premier dans le template, grâce à son score moyen
    assert results.median_ranking[A][:2] == (Y, X)


def test_example_5_equal_median_and_mean_scores_keep_the_template_order() -> None:
    alice: PlayerRanking = ranking({S: [X, Y]})
    bob: PlayerRanking = ranking({S: [Y, X]})

    results: GameResults = compute_results(2, [X, Y], [alice, bob], True)

    assert results.items[X].median_score == results.items[Y].median_score == Fraction(3, 4)
    assert results.items[X].mean_score == results.items[Y].mean_score == Fraction(1, 2)
    assert results.median_ranking == ((X, Y), ())


def test_fine_score_ignores_gaps_between_positions() -> None:
    gapped: PlayerRanking = PlayerRanking(
        final_placements={
            PAPRIKA: FinalPlacement(tier_index=A, position=3),
            BARBECUE: FinalPlacement(tier_index=A, position=10),
        },
        absent_tile_ids=frozenset(),
    )

    results: GameResults = compute_results(2, [PAPRIKA, BARBECUE], [gapped], True)

    assert results.items[PAPRIKA].median_score == Fraction(5, 4)
    assert results.items[BARBECUE].median_score == Fraction(7, 4)
