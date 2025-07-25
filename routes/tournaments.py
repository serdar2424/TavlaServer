from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from services.auth import oauth2_scheme, get_user_from_token
from models.tournament import CreateTournamentRequest, JoinTournamentRequest
from services.tournament import get_current_tournament, get_available_tournaments, get_concluded_tournaments, create_new_tournament, get_tournament_id_from_owner_and_name, add_participant_to_tournament
from routes.game import game_exists
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.post("/tournaments")
async def create_tournament_endpoint(request: CreateTournamentRequest, token: str = Depends(oauth2_scheme)):
    if await tournament_exists(token=token):
        raise HTTPException(status_code=400, detail="You have already joined a tournament")
    elif await game_exists(token=token):
        raise HTTPException(status_code=400, detail="You cannot create a tournament while playing a game")
    else:
        user = await get_user_from_token(token)
        created_tournament = await create_new_tournament(request=request, owner=user.username)
        return JSONResponse(status_code=200, content={"tournament": jsonable_encoder(created_tournament)})


@router.post("/tournaments/join")
async def join_tournament(request: JoinTournamentRequest, token: str = Depends(oauth2_scheme)):
    if await tournament_exists(token=token):
        raise HTTPException(status_code=400, detail="You have already joined a tournament")
    elif await game_exists(token=token):
        raise HTTPException(status_code=400, detail="You cannot join a tournament while playing a game")
    else:
        user = await get_user_from_token(token)
        tournament_id = await get_tournament_id_from_owner_and_name(owner=request.owner, name=request.name)
        if tournament_id == "":
            raise HTTPException(status_code=404, detail="No corresponding tournament found")
        await add_participant_to_tournament(tournament_id=tournament_id, participant=user.username)

        tournament = await get_current_tournament(user.username)
        return JSONResponse(status_code=200, content={"tournament": jsonable_encoder(tournament)})


@router.get("/tournaments")
async def game(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_tournament = await get_current_tournament(user.username)
    if not current_tournament:
        raise HTTPException(status_code=404, detail="No started tournament found")
    return current_tournament.model_dump(by_alias=True)


@router.get("/tournaments/concluded")
async def concluded_tournaments(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    concluded_tournaments = await get_concluded_tournaments(user.username)
    return [tournament.model_dump(by_alias=True) for tournament in concluded_tournaments]


@router.get("/tournaments/available")
async def available_tournaments(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    available_tournaments = await get_available_tournaments(user.username)
    return [tournament.model_dump(by_alias=True) for tournament in available_tournaments]


@router.get("/tournaments/exists")    
async def tournament_exists(token: str = Depends(oauth2_scheme)):
    user = await get_user_from_token(token)
    current_tournament = await get_current_tournament(user.username)
    if not current_tournament:
        return False
    return True