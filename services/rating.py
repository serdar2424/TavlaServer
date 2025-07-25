DEFAULT_RATING = 1500
MINIMUM_RATING = 200

def new_ratings_after_match(winner_rating, loser_rating):
    expected_win = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_lose = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

    new_winner_rating = int(winner_rating + 32 * (1 - expected_win))
    new_loser_rating = int(loser_rating + 32 * (0 - expected_lose))

    if new_loser_rating < MINIMUM_RATING:
        new_loser_rating = MINIMUM_RATING

    return new_winner_rating, new_loser_rating