from models.tournament import Tournament, CreateTournamentRequest, TournamentStats
from fastapi import HTTPException
from typing import List
from services.database import get_db
from services.game import create_started_match, get_current_game
from models.board_configuration import Match
from services.websocket import manager as websocket_manager
from fastapi.encoders import jsonable_encoder
from services.ai import ai_names


MAX_TOURNMENT_PARTICIPANTS = 4


async def get_current_tournament(username: str) -> Tournament:
    tournament_data = await get_db().tournaments.find_one({
        "confirmed_participants": {"$in": [username]},
        "status": {"$in": ["pending", "started"]},
    })
    if tournament_data:
        return Tournament(**tournament_data)
    return None


async def get_available_tournaments(username: str) -> List[Tournament]:
    # Get all tournaments that are closed tournaments that the user is invited to OR open tournaments with less than 4 participants 
    tournament_data = await get_db().tournaments.find({
        "$and": [
        {"status": "pending"},
        {
            "$or": [
                {"participants": {"$in": [username]}},
                {"$and": [
                    {"open": True},
                    {"$expr": {"$lt": [{"$size": "$participants"}, 4]}}
                ]}
            ]
        }
    ]
    }).to_list(length=None)
    if tournament_data:
        return [Tournament(**tournament) for tournament in tournament_data]
    return []


async def get_concluded_tournaments(username: str) -> List[Tournament]:
    tournament_data = await get_db().tournaments.find({
        "confirmed_participants": {"$in": [username]},
        "status": "finished"
    }).to_list(length=None)
    if tournament_data:
        return [Tournament(**tournament) for tournament in tournament_data]
    return []


async def create_new_tournament(request: CreateTournamentRequest, owner: str):
    confirmed_participants = [owner]
    for participant in request.participants:
        if participant in ai_names:
            confirmed_participants.append(participant)
    if len(set(confirmed_participants).intersection(ai_names)) > 1:
        raise HTTPException(status_code=400, detail="Cannot have more than 1 AI players in a tournament")
    new_tournament = Tournament(owner=owner, 
                                participants= [owner] if (request.open and len(request.participants)==0 ) else request.participants,
                                confirmed_participants=confirmed_participants,
                                open=request.open,
                                name=request.name,
                                match_ids=[],
                                status="pending",
                                type=request.type,
                                rounds_to_win=request.rounds_to_win,
                                stats=[]
                            )
    tournament_data = new_tournament.model_dump(by_alias=True)
    await get_db().tournaments.insert_one(tournament_data)
    return new_tournament


async def get_tournament_id_from_owner_and_name(owner: str, name: str) -> Tournament:
    tournament_data = await get_db().tournaments.find_one({
        "owner": owner,
        "name": name
    })
    if tournament_data:
        return tournament_data["_id"]
    return ""


async def add_participant_to_tournament(tournament_id: str, participant=str):
    tournament = await get_db().tournaments.find_one({"_id": tournament_id})

    if not tournament:
        raise HTTPException(status_code=404, detail="No corresponding tournament found")
    
    is_open = tournament["open"]
    participants = tournament["participants"]
    confirmed_participants = tournament["confirmed_participants"]

    if is_open:
        #Join open tournament. Check that there are less than 4 participants and that participant is not already in participants.
        #Finally, add participant to participants and confirmed_participants
        if(len(participants) >= 4 or participant in participants):
            raise HTTPException(status_code=400, detail="Cannot join tournament")
        else:
            await get_db().tournaments.update_one(
                {"_id": tournament_id},
                {
                    "$push": {
                        "participants": participant,
                        "confirmed_participants": participant
                    }
                }
            )
    else:
        #Join closed tournament. Check that participant is in participants (invited), then that participant is not already in confirmed_participants.
        #Finally, add participant to confirmed_participants
        if participant not in participants:
            raise HTTPException(status_code=400, detail="Not invited to tournament")
        else:
            if(participant in confirmed_participants):
                raise HTTPException(status_code=400, detail="Already joined tournament")
            else:
                await get_db().tournaments.update_one(
                    {"_id": tournament_id},
                    {
                        "$push": {
                            "confirmed_participants": participant
                        }
                    }
                )

    tournament = await get_db().tournaments.find_one({"_id": tournament_id})
    if len(tournament["confirmed_participants"]) == MAX_TOURNMENT_PARTICIPANTS:
        await start_tournament(tournament_id)


async def start_tournament(tournament_id: str):

    tournament = await get_db().tournaments.find_one({"_id": tournament_id})
    stats = [TournamentStats(username=participant, wins=0, losses=0, matches=0, points=0) for participant in tournament["confirmed_participants"]]

    if tournament:
        await get_db().tournaments.update_one(
            {"_id": tournament_id},
            {"$set": {"status": "started", "stats": jsonable_encoder(stats)}}
        )

        if tournament["type"] == "round_robin":
            await create_round_robin_tournament_round(tournament_id, 1)


async def create_round_robin_tournament_round(tournament_id: str, round: int):
    tournament = await get_db().tournaments.find_one({"_id": tournament_id})
    if not tournament:
        raise HTTPException(status_code=404, detail="No corresponding tournament found")
    elif len(tournament['match_ids']) > round:
        raise HTTPException(status_code=400, detail="Round already exists")
    
    g1_participants = (tournament["confirmed_participants"][0], tournament["confirmed_participants"][round])
    remaining_indices = [i for i in range(4) if i != 0 and i != round]
    g2_participants = (tournament["confirmed_participants"][remaining_indices[0]], tournament["confirmed_participants"][remaining_indices[1]])

    await create_started_match(g1_participants[0], g1_participants[1], tournament["rounds_to_win"])
    await create_started_match(g2_participants[0], g2_participants[1], tournament["rounds_to_win"])

    g1 = await get_current_game(g1_participants[0])
    g2 = await get_current_game(g2_participants[0])

    await get_db().tournaments.update_one(
        {"_id": tournament_id},
        {
            "$set": {
                "match_ids": [g1.id, g2.id]
            }
        }
    )


async def get_tournament_of_game(game_id: str):
    tournament = await get_db().tournaments.find_one({"match_ids": game_id})
    if tournament:
        return Tournament(**tournament)
    return None


async def update_tournament_of_game(game: Match, winner_username: str, loser_username: str, gained_points: int):
    tournament = await get_tournament_of_game(game.id)
    
    if tournament:
        await update_tournament_stats(tournament, winner_username, loser_username, gained_points)
        tournament = await get_db().tournaments.find_one({"_id": tournament.id})

        total_games = sum(stat['wins'] for stat in tournament['stats'])

        if tournament['type'] == "round_robin":
            if total_games >= (len(tournament['confirmed_participants']) * (len(tournament['confirmed_participants']) - 1)) // 2:
                await end_tournament(tournament)
            elif total_games % 2 == 0:
                await create_round_robin_tournament_round(tournament['_id'], total_games // 2 + 1)


async def update_tournament_stats(tournament: Tournament, winner_username: str, loser_username: str, gained_points: int):
    winner_stats = next((stat for stat in tournament.stats if stat.username == winner_username), None)
    if winner_stats:
        winner_stats.wins += 1
        winner_stats.matches += 1
        winner_stats.points += gained_points
    loser_stats = next((stat for stat in tournament.stats if stat.username == loser_username), None)
    if loser_stats:
        loser_stats.losses += 1
        loser_stats.matches += 1

    await get_db().tournaments.update_one(
        {"_id": tournament.id},
        {"$set": {"stats": jsonable_encoder(tournament.stats)}}
    )


async def end_tournament(tournament: Tournament):
    await get_db().tournaments.update_one(
        {"_id": tournament['_id']},
        {"$set": {"status": "finished"}}
    )

    winner = max(tournament['stats'], key=lambda x: x["wins"])
    if len([stat for stat in tournament['stats'] if stat["wins"] == winner["wins"]]) > 1:
        winner = max([stat for stat in tournament['stats'] if stat["wins"] == winner["wins"]], key=lambda x: x["points"])

    #Increment tournament wins stat for winner
    await get_db().users.update_one(
        {"username": winner["username"]},
        {"$inc": {"stats.tournaments_won": 1}}
    )

    for participant in tournament['confirmed_participants']:
        websocket = await websocket_manager.get_user(participant)
        if websocket:
            await websocket_manager.send_personal_message({"type": "tournament_over", "winner": winner["username"]}, websocket)