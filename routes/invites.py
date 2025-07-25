from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from models.board_configuration import CreateInviteRequest, AcceptInviteRequest
from services.ai import is_ai
from services.auth import oauth2_scheme, get_user_from_token
from services.database import get_db
from services.game import create_started_match
from services.invite import create_invite, get_pending_invites, accept_invite
from services.websocket import manager
from services.user import get_user

router = APIRouter()


def serialize_invite(invite):
    invite["_id"] = str(invite["_id"])
    return invite


@router.get("/invites")
async def receive_invite_endpoint(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    pending_invites = await get_pending_invites(user.username)
    serialized_invites = [serialize_invite(invite) for invite in pending_invites]
    return JSONResponse(status_code=200, content={"pending_invites": serialized_invites})


@router.post("/invites")
async def create_invite_endpoint(request: CreateInviteRequest, token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    opponent_username = request.opponent_username
    rounds_to_win = request.rounds_to_win
    if request.use_email:
        opponent = (await get_db().users.find_one({"email": opponent_username}))
        if opponent is None:
            raise HTTPException(status_code=404, detail="Opponent not found")
        opponent_username = opponent["username"]
    elif await get_user(opponent_username) is None and not is_ai(opponent_username):
        raise HTTPException(status_code=404, detail="Opponent not found")

    if user.username == opponent_username:
        raise HTTPException(status_code=400, detail="You cannot invite yourself")
    
    else:
        already_started_matches = await get_db().matches.find(
            {"$or": [{"player1": user.username}, {"player2": user.username}], "status": "started"}).to_list(length=None)
        
        if len(already_started_matches) > 0:
            raise HTTPException(status_code=400, detail="You are already playing a match")
        
        elif is_ai(opponent_username):
            await create_started_match(user.username, opponent_username, rounds_to_win)

        else: 
            await create_invite(user.username, opponent_username, rounds_to_win)

            await websocket_invite(opponent_username, user)

    return JSONResponse(status_code=200, content={"message": "Invite created successfully"})


async def websocket_invite(user1, user):
    inviter_websocket = await manager.get_user(user.username)
    if inviter_websocket:
        await manager.send_personal_message({"type": "invite-sent", "to": user1}, inviter_websocket)
    invited_websocket = await manager.get_user(user1)
    if invited_websocket:
        await manager.send_personal_message({"type": "invite", "from": user.username}, invited_websocket)


@router.post("/invites/accept")
async def accept_invite_endpoint(request: AcceptInviteRequest, token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    invite_id = request.invite_id
    invite = await get_db().matches.find_one({"_id": invite_id, "status": "pending"})
    already_started_matches = await get_db().matches.find(
        {"$or": [{"player1": user.username}, {"player2": user.username}], "status": "started"}).to_list(length=None)
    if len(already_started_matches) > 0:
        raise HTTPException(status_code=400, detail="You are already playing a match")
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    opponent_username = invite["player1"]
    opponent_started_matches = await get_db().matches.find(
        {"$or": [{"player1": opponent_username}, {"player2": opponent_username}], "status": "started"}).to_list(length=None)
    if len(opponent_started_matches) > 0:
        raise HTTPException(status_code=400, detail="Opponent is already playing a match")    
    if invite["player2"] != user.username:
        raise HTTPException(status_code=403, detail="You are not the recipient of this invite")
    await accept_invite(invite_id)
    websocket = await manager.get_user(invite["player1"])
    if websocket:
        await manager.send_personal_message({"type": "invite-accepted", "from": user.username}, websocket)
    return JSONResponse(status_code=200, content={"message": "Invite accepted successfully"})
