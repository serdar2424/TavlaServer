import random
from datetime import datetime, timedelta
from time import strptime

from models.board_configuration import Match, BoardConfiguration, StartDice, DoublingCube
from services.ai import ai_names, ai_rating
from services.board import is_gammon, is_backgammon
from services.database import get_db
from services.rating import new_ratings_after_match
from services.websocket import ConnectionManager


async def update_match(selector, data):
    data["$set"]["last_updated"] = datetime.now().replace(microsecond=0).isoformat()
    await get_db().matches.update_one(selector, data)


def throw_dice():
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    return die1, die2


async def get_current_game(username: str) -> Match:
    match_data = await get_db().matches.find_one({
        "$or": [{"player1": username}, {"player2": username}],
        "status": "started"
    })
    if match_data:
        return Match(**match_data)
    return None


async def create_started_match(player1: str, player2: str, rounds_to_win: int = 1):
    new_match = Match(player1=player1, player2=player2, status="started", rounds_to_win=rounds_to_win)
    match_data = new_match.dict(by_alias=True)
    await get_db().matches.insert_one(match_data)


async def check_timeout_condition(match: Match):
    current_time = datetime.now().replace(microsecond=0)  # Remove microseconds from current time

    print("current_time: ", current_time)
    print("dt(strptime) out: ", datetime(*strptime(match.last_updated, "%Y-%m-%dT%H:%M:%S")[:6]))

    # Convert last_updated to tuple, then to datetime object and compare with current time
    return current_time - datetime(*strptime(match.last_updated, "%Y-%m-%dT%H:%M:%S")[:6]) > timedelta(seconds=30)


async def check_timeout_winner(current_game: Match):
    if await check_timeout_condition(current_game):
        if current_game.turn == 0:  # Player 1's turn timed out, winner should be player 2
            return 2
        else:  # Player 2's turn timed out, winner should be player 1
            return 1
    else:
        return 0


def check_win_condition(match: Match):
    player1_counter = match.board_configuration["bar"]["player1"]
    player2_counter = match.board_configuration["bar"]["player2"]

    for point in match.board_configuration["points"]:
        player1_counter += point["player1"]
        player2_counter += point["player2"]
        if player1_counter > 0 and player2_counter > 0:
            return {"winner": 0}

    return {"winner": 1} if player1_counter == 0 else {"winner": 2}


async def check_winner(current_game: Match, manager: ConnectionManager, winner:int=None, is_timeout:bool=False):
    if is_timeout:
        winner = await check_timeout_winner(current_game)
    elif winner is None:
        winner = check_win_condition(current_game)
        winner = winner.get("winner")

    p1_data, p2_data = await get_players_data(current_game)

    # Check if someone won the current round
    if winner != 0:
        loser_username, old_loser_rating, old_winner_rating, winner_username, gained_points = await update_rating(
            current_game,
            p1_data, p2_data,
            winner)

        # Check if someone won the entire match (won rounds_to_win rounds)
        if current_game.winsP1 >= current_game.rounds_to_win or current_game.winsP2 >= current_game.rounds_to_win:
            current_game.doublingCube.proposed = False
            current_game.doublingCube.proposer = 0
            await update_on_match_win(current_game, loser_username, manager, old_loser_rating, old_winner_rating,
                                      winner, winner_username)

            from services.tournament import update_tournament_of_game
            await update_tournament_of_game(current_game, winner_username, loser_username, gained_points)
        else:
            # Message for round end (gammon/backgammon/normal win)
            info_str = get_winning_info_str(current_game, winner) if not is_timeout else " due to timeout"

            # Must proceed to next round
            # Reset the board configuration, turn, dice and available
            current_game = reset_match_for_new_tournament(current_game, winner_username)

            # Message for round end
            await notify_players_of_round_end(manager, current_game, winner_username, info_str)

    current_game = game_fields_to_dict(current_game)

    await update_match({"_id": current_game.id},
                       {"$set": {"board_configuration": current_game.board_configuration,
                                 "status": current_game.status,
                                 "available": current_game.available,
                                 "dice": current_game.dice,
                                 "turn": current_game.turn,
                                 "startDice": current_game.startDice,
                                 "doublingCube": current_game.doublingCube,
                                 "winsP1": current_game.winsP1,
                                 "winsP2": current_game.winsP2,
                                 "ai_suggestions": current_game.ai_suggestions}})


def reset_match_for_new_tournament(match: Match, winner_username: str):
    match.board_configuration = BoardConfiguration().dict(by_alias=True)
    match.available = []
    match.dice = []
    match.ai_suggestions = [0, 0]
    match.turn = int(winner_username == match.player2)
    match.starter = 0
    match.startDice = StartDice()
    match.doublingCube = DoublingCube()
    return match


async def notify_players_of_round_end(manager: ConnectionManager, current_game: Match, winner_username: str, info_str: str):
    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message({"type": "round_over", "winner": winner_username, "info": info_str}, websocket_player1)
    
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message({"type": "round_over", "winner": winner_username, "info": info_str}, websocket_player2)


async def get_players_data(current_game):
    p1_data = await get_db().users.find_one({
        "username": current_game.player1
    }) or {}
    p2_data = await get_db().users.find_one({
        "username": current_game.player2
    }) or {}
    if current_game.player2 in ai_names:
        p2_data["username"] = current_game.player2
        p2_data["rating"] = ai_rating[ai_names.index(current_game.player2)]
    elif current_game.player1 in ai_names:
        p1_data["username"] = current_game.player1
        p1_data["rating"] = ai_rating[ai_names.index(current_game.player1)]
    return p1_data, p2_data


def game_fields_to_dict(game: Match):
    board = game.board_configuration
    game.board_configuration = board.model_dump(by_alias=True) if isinstance(board, BoardConfiguration) else board

    doubling = game.doublingCube
    game.doublingCube = doubling.model_dump(by_alias=True) if isinstance(doubling, DoublingCube) else doubling

    start_dice = game.startDice
    game.startDice = start_dice.model_dump(by_alias=True) if isinstance(start_dice, StartDice) else start_dice

    return game


async def update_rating(current_game: Match, p1_data, p2_data, winner, is_timeout: bool = False):
    win_multiplier = 1 if is_timeout else compute_win_multiplier(current_game, winner)

    if winner == 1:
        # Player 1 won the current round
        current_game.winsP1 += win_multiplier
        winner_username = p1_data["username"]
        loser_username = p2_data["username"]
        old_winner_rating = p1_data["rating"]
        old_loser_rating = p2_data["rating"]
    else:
        # Player 2 won the current round
        current_game.winsP2 += win_multiplier
        winner_username = p2_data["username"]
        loser_username = p1_data["username"]
        old_winner_rating = p2_data["rating"]
        old_loser_rating = p1_data["rating"]
    return loser_username, old_loser_rating, old_winner_rating, winner_username, win_multiplier * 1


def compute_win_multiplier(current_game: Match, winner: int) -> int:
    if isinstance(current_game.doublingCube, DoublingCube):
        doubling_value = 2 ** current_game.doublingCube.count
    else:
        doubling_value = 2 ** int(current_game.doublingCube['count'])

    if not isinstance(current_game.board_configuration, BoardConfiguration):
        board = BoardConfiguration(**current_game.board_configuration)
    else:
        board = current_game.board_configuration

    is_player1 = winner == 1

    if is_backgammon(board, is_player1):
        return 3 * doubling_value
    elif is_gammon(board, is_player1):
        return 2 * doubling_value
    else:
        return 1 * doubling_value


def get_winning_info_str(current_game: Match, winner: int):
    if isinstance(current_game.board_configuration, BoardConfiguration):
        board = current_game.board_configuration
    else:
        board = BoardConfiguration(**current_game.board_configuration)

    is_player1 = winner == 1

    if is_backgammon(board, is_player1):
        return " with a backgammon"
    elif is_gammon(board, is_player1):
        return " with a gammon"
    else:
        return ""


async def update_on_match_win(current_game, loser_username, manager, old_loser_rating, old_winner_rating, winner,
                              winner_username):
    current_game.status = "player_" + str(winner) + "_won"

    await get_db().matches.update_one({"_id": current_game.id},
                                      {"$set": {"status": current_game.status}}
                                      )
    
    # Logic for player ratings & stats update and match end
    (new_winner_rating, new_loser_rating) = new_ratings_after_match(old_winner_rating, old_loser_rating)
    await get_db().users.update_one(
        {"username": winner_username},
        {"$set": {"rating": new_winner_rating}, "$inc": {"stats.matches_played": 1, "stats.matches_won": 1}}
    )
    await get_db().users.update_one(
        {"username": loser_username},
        {"$set": {"rating": new_loser_rating}, "$inc": {"stats.matches_played": 1}}
    )
    
    #Update highest rating for winner if applicable
    if(winner_username not in ai_names):
        winner_data = await get_db().users.find_one({"username": winner_username})
        winner_highest_rating = winner_data.get("stats", {}).get("highest_rating", 1500) # Default value is provided solely for the sake of test users
        if new_winner_rating > winner_highest_rating:
            await get_db().users.update_one({"username": winner_username},
                                            {"$set": {"stats.highest_rating": new_winner_rating}})

    # Message for match end, US #103
    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "match_over", "winner": winner_username, "loser": loser_username,
             "old_winner_rating": old_winner_rating, "new_winner_rating": new_winner_rating,
             "old_loser_rating": old_loser_rating, "new_loser_rating": new_loser_rating},
            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "match_over", "winner": winner_username, "loser": loser_username,
             "old_winner_rating": old_winner_rating, "new_winner_rating": new_winner_rating,
             "old_loser_rating": old_loser_rating, "new_loser_rating": new_loser_rating}, websocket_player2)


async def quit_the_game(current_game: Match, manager, winner):
    p1_data, p2_data = await get_players_data(current_game)

    if winner == 1:
        matches_left = current_game.rounds_to_win - current_game.winsP1
    else:
        matches_left = current_game.rounds_to_win - current_game.winsP2

    current_game.board_configuration = BoardConfiguration().dict(by_alias=True)

    for _ in range(matches_left):
        loser_username, old_loser_rating, old_winner_rating, winner_username, gained_points = await update_rating(
            current_game,
            p1_data, p2_data,
            winner)

    if current_game.winsP1 == current_game.rounds_to_win or current_game.winsP2 == current_game.rounds_to_win:
        await update_on_match_win(current_game, loser_username, manager, old_loser_rating, old_winner_rating,
                                  winner, winner_username)
        from services.tournament import update_tournament_of_game
        await update_tournament_of_game(current_game, winner_username, loser_username, gained_points)

    await get_db().matches.update_one({"_id": current_game.id},
                                      {"$set": {"board_configuration": current_game.board_configuration,
                                                "status": 'player_' + str(winner) + '_won',
                                                "available": current_game.available,
                                                "dice": current_game.dice,
                                                "turn": current_game.turn,
                                                "winsP1": current_game.winsP1,
                                                "winsP2": current_game.winsP2}})
