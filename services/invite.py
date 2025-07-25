from bson import ObjectId
from models.board_configuration import Match
from services.database import get_db
from services.game import update_match


async def create_invite(player1: str, player2: str, rounds_to_win: int):
    match = Match(player1=player1, player2=player2, rounds_to_win=rounds_to_win)
    match_data = match.dict(by_alias=True)
    await get_db().matches.insert_one(match_data)


async def get_pending_invites(username: str):
    pending_invites = await get_db().matches.find({"player2": username, "status": "pending"}).to_list(length=None)
    return pending_invites


async def accept_invite(invite_id: str):
    await update_match({"_id": invite_id}, {"$set": {"status": "started", "turn": -1}})
