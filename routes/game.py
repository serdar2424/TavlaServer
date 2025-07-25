from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from models.board_configuration import Match, oauth2_scheme
from pydantic import BaseModel
from services.ai import ai_names
from services.auth import get_user_from_token
from services.database import get_db
from services.game import throw_dice, get_current_game, check_winner, quit_the_game, check_timeout_condition, \
    update_match
from services.websocket import manager

NOT_YOUR_TURN = "It's not your turn"

NO_ONGOING_GAME_FOUND = "No ongoing game found"

router = APIRouter()


@router.get("/game")
async def game(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    if not current_game:
        raise HTTPException(status_code=400, detail="No started game found")
    return current_game.dict(by_alias=True)


@router.get("/game/exists")
async def game_exists(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    if not current_game:
        return False
    return True


@router.post("/move/piece")
async def move(move_data: dict, token: str = Depends(oauth2_scheme)):
    current_game = await get_user_and_check(token)

    board_value = move_data.get("board")
    dice_value = move_data.get("dice")

    current_game.board_configuration = board_value
    if dice_value in current_game.available:
        current_game.available.remove(dice_value)

    if len(current_game.available) <= 0:
        current_game.turn += 1
        current_game.dice = []
        current_game.available = []

    await check_winner(current_game, manager)

    await update_match({"_id": current_game.id}, {
        "$set": {"board_configuration": current_game.board_configuration, "available": current_game.available,
                 "dice": current_game.dice,
                 "turn": current_game.turn}})
    


    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message({"type": "move_piece", "match": current_game.dict(by_alias=True)},
                                            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message({"type": "move_piece", "match": current_game.dict(by_alias=True)},
                                            websocket_player2)


@router.post("/move/ai")
async def move(move_data: dict, token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if current_game.player1 not in ai_names and current_game.player2 not in ai_names:
        raise HTTPException(status_code=400, detail=NOT_YOUR_TURN)

    board_value = move_data.get("board")

    current_game.board_configuration = board_value

    current_game.turn += 1
    current_game.dice = []
    current_game.available = []

    await check_winner(current_game, manager)

    await update_match({"_id": current_game.id}, {
        "$set": {"board_configuration": current_game.board_configuration, "available": current_game.available,
                 "dice": current_game.dice,
                 "turn": current_game.turn}})

    websocket_player1 = await manager.get_user(user.username)
    if websocket_player1:
        await manager.send_personal_message({"type": "move_piece", "match": current_game.dict(by_alias=True)},
                                            websocket_player1)


@router.get("/throw_start_dice")
async def start_dice_endpoint(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    is_player1 = current_game.player1 == user.username

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail="No pending game found")

    if current_game.starter > 0:
        raise HTTPException(status_code=400, detail="Start dice already thrown")

    old_start_dice = current_game.startDice
    if is_player1 and old_start_dice.count1 > old_start_dice.count2 or \
            not is_player1 and old_start_dice.count2 > old_start_dice.count1:
        raise HTTPException(status_code=400, detail="You have already thrown the start dice. Wait for the other player")

    result = throw_dice()
    starter, turn, old_start_dice = await get_dices(current_game, is_player1, old_start_dice, result)

    await update_match({"_id": current_game.id},
                       {"$set": {"startDice": jsonable_encoder(old_start_dice), "starter": starter, "turn": turn}})
    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "start_dice_roll", "result": jsonable_encoder(old_start_dice), "starter": starter, "turn": turn},
            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "start_dice_roll", "result": jsonable_encoder(old_start_dice), "starter": starter, "turn": turn},
            websocket_player2)


async def get_dices(current_game, is_player1, old_start_dice, result):
    if is_player1:
        old_start_dice.roll1, old_start_dice.count1 = result[0], old_start_dice.count1 + 1
        if current_game.player2 in ai_names:
            old_start_dice.roll2, old_start_dice.count2 = result[1], old_start_dice.count2 + 1
    else:
        old_start_dice.roll2, old_start_dice.count2 = result[0], old_start_dice.count2 + 1
        if current_game.player1 in ai_names:
            old_start_dice.roll1, old_start_dice.count1 = result[1], old_start_dice.count1 + 1

    starter, turn = 0, -1
    if old_start_dice.count1 == old_start_dice.count2:
        if old_start_dice.roll1 > old_start_dice.roll2:
            starter, turn = 1, 0
        elif old_start_dice.roll2 > old_start_dice.roll1:
            starter, turn = 2, 1
    return starter, turn, old_start_dice


@router.get("/throw_dice")
async def dice_endpoint(token: str = Depends(oauth2_scheme)):
    current_game = await get_user_and_check(token)

    if current_game.dice:
        raise HTTPException(status_code=400, detail="Dice already thrown")

    result = throw_dice()
    current_game.dice = result
    if result[0] == result[1]:
        current_game.available = [result[0]] * 4
    else:
        current_game.available = result

    await update_match({"_id": current_game.id},
                       {"$set": {"dice": result, "available": current_game.available}})
    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "dice_roll", "result": result, "available": current_game.available}, websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "dice_roll", "result": result, "available": current_game.available}, websocket_player2)


class InGameMessageRequest(BaseModel):
    message: str


@router.post("/game/message")
async def send_in_game_message(request: InGameMessageRequest, token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message({"type": "in_game_msg", "msg": request.message, "user": user.username},
                                            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message({"type": "in_game_msg", "msg": request.message, "user": user.username},
                                            websocket_player2)


@router.post("/game/pass_turn")
async def pass_turn(token: str = Depends(oauth2_scheme)):
    current_game = await get_user_and_check(token)

    current_game.turn += 1
    current_game.dice = []
    current_game.available = []

    await update_match({"_id": current_game.id}, {
        "$set": {"dice": current_game.dice, "available": current_game.available, "turn": current_game.turn}})

    await send_move_with_ws(current_game)


async def send_move_with_ws(current_game):
    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message({"type": "pass_turn", "match": current_game.dict(by_alias=True)},
                                            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message({"type": "pass_turn", "match": current_game.dict(by_alias=True)},
                                            websocket_player2)


async def get_user_and_check(token):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)
    if (current_game.turn % 2 == 0 and current_game.player1 != user.username) or \
            (current_game.turn % 2 == 1 and current_game.player2 != user.username) \
            or current_game.doublingCube.proposed:
        raise HTTPException(status_code=400, detail=NOT_YOUR_TURN)
    return current_game


@router.post("/game/request_timeout")
async def request_timeout(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if (current_game.turn % 2 == 0 and current_game.player1 == user.username) or \
            (current_game.turn % 2 == 1 and current_game.player2 == user.username):
        raise HTTPException(status_code=400, detail="It's not your opponent's turn")

    is_timeout = await check_timeout_condition(current_game)

    if not is_timeout:
        raise HTTPException(status_code=400, detail="Timeout condition not met")
    else:
        await check_winner(current_game, manager, is_timeout=True)

    new_current_game = await get_db().matches.find_one({"_id": current_game.id})
    await send_move_with_ws(Match(**new_current_game))


@router.post("/ai/suggestions")
async def use_ai_suggestions(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if (current_game.turn % 2 == 0 and current_game.player1 != user.username) or \
            (current_game.turn % 2 == 1 and current_game.player2 != user.username):
        raise HTTPException(status_code=400, detail=NOT_YOUR_TURN)

    is_player_1 = current_game.player1 == user.username
    if current_game.ai_suggestions[is_player_1] >= 3:
        raise HTTPException(status_code=400, detail="You have already used all your suggestions")

    current_game.ai_suggestions[is_player_1] += 1

    await get_db().matches.update_one({"_id": current_game.id}, {
        "$set": {"ai_suggestions": current_game.ai_suggestions}})


@router.post("/game/quit")
async def quit_game(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if current_game.player1 == user.username:
        winner = 2
    else:
        winner = 1

    await quit_the_game(current_game, manager, winner)

    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "quit_game", "winner": winner, "user": user.username, "match": current_game.dict(by_alias=True)},
            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "quit_game", "winner": winner, "user": user.username, "match": current_game.dict(by_alias=True)},
            websocket_player2)


@router.post("/game/double/propose")
async def propose_double(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    player_number = 1 if current_game.player1 == user.username else 2

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if (current_game.turn % 2 == 0 and current_game.player1 != user.username) or \
            (current_game.turn % 2 == 1 and current_game.player2 != user.username):
        raise HTTPException(status_code=400, detail=NOT_YOUR_TURN)

    if current_game.doublingCube.proposed or current_game.doublingCube.last_usage == player_number:
        raise HTTPException(status_code=400, detail="Doubling already proposed or cube in posses of the other player")

    if current_game.doublingCube.count >= 3:
        raise HTTPException(status_code=400, detail="Doubling cube already reached maximum value")

    current_game.doublingCube.proposed = True
    current_game.doublingCube.proposer = player_number

    await get_db().matches.update_one({"_id": current_game.id}, {
        "$set": {"doublingCube": current_game.doublingCube.model_dump(by_alias=True)}})

    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "double_proposed", "match": current_game.model_dump(by_alias=True)},
            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "double_proposed", "match": current_game.model_dump(by_alias=True)},
            websocket_player2)


@router.post("/game/double/accept")
async def accept_double(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    player_number = 1 if current_game.player1 == user.username else 2

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if not current_game.doublingCube.proposed or current_game.doublingCube.proposer == player_number:
        raise HTTPException(status_code=400, detail="No doubling cube proposed to you")

    current_game.doublingCube.count += 1
    current_game.doublingCube.proposed = False
    current_game.doublingCube.last_usage = current_game.doublingCube.proposer
    current_game.doublingCube.proposer = 0

    await get_db().matches.update_one({"_id": current_game.id}, {
        "$set": {"doublingCube": current_game.doublingCube.model_dump(by_alias=True)}})

    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message(
            {"type": "double_accepted", "match": current_game.model_dump(by_alias=True)},
            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message(
            {"type": "double_accepted", "match": current_game.model_dump(by_alias=True)},
            websocket_player2)


@router.post("/game/double/reject")
async def reject_double(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_game = await get_current_game(user.username)
    player_number = 1 if current_game.player1 == user.username else 2

    if not current_game or current_game.status != "started":
        raise HTTPException(status_code=400, detail=NO_ONGOING_GAME_FOUND)

    if not current_game.doublingCube.proposed or current_game.doublingCube.proposer == player_number:
        raise HTTPException(status_code=400, detail="No doubling cube proposed to you")

    winner = 1 if player_number == 2 else 2
    await check_winner(current_game, manager, winner=winner)

    websocket_player1 = await manager.get_user(current_game.player1)
    if websocket_player1:
        await manager.send_personal_message({"type": "double_rejected", "match": current_game.dict(by_alias=True)},
                                            websocket_player1)
    websocket_player2 = await manager.get_user(current_game.player2)
    if websocket_player2:
        await manager.send_personal_message({"type": "double_rejected", "match": current_game.dict(by_alias=True)},
                                            websocket_player2)
