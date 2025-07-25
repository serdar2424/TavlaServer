from services.rating import new_ratings_after_match, MINIMUM_RATING


def test_new_ratings_after_match_normal_case():
    winner_rating = 1600
    loser_rating = 1400
    new_winner_rating, new_loser_rating = new_ratings_after_match(winner_rating, loser_rating)
    assert new_winner_rating > winner_rating
    assert new_loser_rating < loser_rating


def test_new_ratings_after_match_loser_below_minimum():
    winner_rating = 400
    loser_rating = MINIMUM_RATING
    new_winner_rating, new_loser_rating = new_ratings_after_match(winner_rating, loser_rating)
    assert new_winner_rating > winner_rating
    assert new_loser_rating == MINIMUM_RATING


def test_new_ratings_scaling():
    winner_rating = 2800

    # winner rating should increase by a bunch, loser rating should decrease by a bunch
    loser_rating1 = 2700
    new_winner_rating1, new_loser_rating1 = new_ratings_after_match(winner_rating, loser_rating1)

    # winner rating should increase by a little, loser rating should decrease by a little
    loser_rating2 = 700
    new_winner_rating2, new_loser_rating2 = new_ratings_after_match(winner_rating, loser_rating2)

    # Winner gained more rating when playing against a similarly rated opponent
    assert new_winner_rating1 - winner_rating > new_winner_rating2 - winner_rating

    # Loser lost more rating when playing against a similarly rated opponent
    assert loser_rating1 - new_loser_rating1 > loser_rating2 - new_loser_rating2
