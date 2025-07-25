import pytest
from httpx import AsyncClient
from services.database import get_db
from tests.conftest import clear_tournaments, clear_matches
from services.tournament import create_new_tournament, add_participant_to_tournament, start_tournament, create_round_robin_tournament_round, get_tournament_of_game, update_tournament_of_game, update_tournament_stats, end_tournament
from models.tournament import CreateTournamentRequest, Tournament, JoinTournamentRequest
from models.board_configuration import Match
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException


mock_request_data = CreateTournamentRequest(
    name="test", 
    open=True, 
    participants=["testuser"], 
    rounds_to_win=2,
    type="round_robin"
)

mock_request_data_closed = CreateTournamentRequest(
    name="test", 
    open=False, 
    participants=["testuser", "testuser2", "testuser3", "newuser"], 
    rounds_to_win=2,
    type="round_robin"
)

mock_request_data_open_full = CreateTournamentRequest(
    name="test", 
    open=True, 
    participants=["testuser", "testuser2", "testuser3", "testuser4"], 
    rounds_to_win=2,
    type="round_robin"
)

mock_request_data_closed_not_invited = CreateTournamentRequest(
    name="test", 
    open=False, 
    participants=["testuser", "testuser2", "testuser3", "testuser4"], 
    rounds_to_win=2,
    type="round_robin"
)

tournaments_route = "/tournaments"

@pytest.mark.anyio
async def test_create_tournament(client: AsyncClient, token: str):
    await clear_tournaments()
    await clear_matches()

    response = await client.post(tournaments_route, json=mock_request_data.model_dump(),
                                 headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    res_data = response.json()
    assert "tournament" in res_data
    created_tournament = res_data['tournament']
    assert created_tournament['owner'] == 'testuser'
    assert created_tournament['name'] == "test"
    assert created_tournament['open'] == True
    assert created_tournament['participants'] == ['testuser']
    assert created_tournament['rounds_to_win'] == 2


@pytest.mark.anyio
async def test_get_tournament(client: AsyncClient, token: str):
    await clear_tournaments()
    response = await client.get(tournaments_route, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

    await create_new_tournament(mock_request_data, owner="testuser")
    response = await client.get(tournaments_route, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    res_data = response.json()
    assert res_data['owner'] == 'testuser'
    assert res_data['name'] == "test"
    assert res_data['open'] == True
    assert res_data['participants'] == ['testuser']
    assert res_data['rounds_to_win'] == 2

@pytest.mark.anyio
async def test_get_concluded_tournaments(client: AsyncClient, token: str):
    await clear_tournaments()
    response = await client.get(tournaments_route+"/concluded", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []

    await create_new_tournament(mock_request_data, owner="testuser")
    await get_db().tournaments.update_one({"owner": "testuser"}, {"$set": {"status": "finished"}})
    response = await client.get(tournaments_route+"/concluded", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["owner"] == "testuser"
    assert response.json()[0]["name"] == "test"

@pytest.mark.anyio
async def test_tournament_exists(client: AsyncClient, token: str):
    await clear_tournaments()
    response = await client.get(tournaments_route + "/exists", headers={"Authorization": f"Bearer {token}"})
    assert response.json() == False

    await create_new_tournament(mock_request_data, owner="testuser")
    response = await client.get(tournaments_route + "/exists", headers={"Authorization": f"Bearer {token}"})
    assert response.json() == True

@pytest.mark.anyio
async def test_join_tournament(client: AsyncClient, token: str):
    await clear_tournaments()

    mock_request_data = CreateTournamentRequest(
        name="test", 
        open=True, 
        participants=["testuser2"], 
        rounds_to_win=2,
        type="round_robin"
    )
    await create_new_tournament(mock_request_data, owner="testuser2")

    join_request = JoinTournamentRequest(owner="testuser2", name="test")

    response = await client.post(tournaments_route+"/join", json=join_request.model_dump(),
                                 headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["tournament"] is not None
    tournament = Tournament(**data["tournament"])
    assert tournament.participants == ['testuser2', 'testuser']
    assert tournament.confirmed_participants == ['testuser2', 'testuser']

@pytest.mark.anyio
async def test_available_tournaments(client: AsyncClient, token: str):
    await clear_tournaments()

    mock_request_data = CreateTournamentRequest(
        name="test", 
        open=True, 
        participants=["testuser2"], 
        rounds_to_win=2,
        type="round_robin"
    )
    await create_new_tournament(mock_request_data, owner="testuser2")
    tournament = await get_tournament_as_class_object("testuser2")

    response = await client.get(tournaments_route+"/available", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert len(data) == 1
    received_tournament = Tournament(**data[0])
    assert tournament == received_tournament

@pytest.mark.anyio
async def test_add_participant_to_open_tournament():
    await clear_tournaments()
    await create_new_tournament(mock_request_data, owner="testuser")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})

    await add_participant_to_tournament(tournament["_id"], "newuser")
    updated_tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    assert updated_tournament["status"] == "pending"
    assert updated_tournament["participants"] == ["testuser", "newuser"]
    assert updated_tournament["confirmed_participants"] == ["testuser", "newuser"]

    await add_participant_to_tournament(tournament["_id"], "newuser2")
    updated_tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    assert updated_tournament["status"] == "pending"
    assert updated_tournament["participants"] == ["testuser", "newuser", "newuser2"]
    assert updated_tournament["confirmed_participants"] == ["testuser", "newuser", "newuser2"]

@pytest.mark.anyio
async def test_add_participant_to_closed_tournament():
    await clear_tournaments()
    await create_new_tournament(mock_request_data_closed, owner="testuser")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})

    await add_participant_to_tournament(tournament["_id"], "newuser")
    updated_tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    assert updated_tournament["status"] == "pending"
    assert updated_tournament["confirmed_participants"] == ["testuser", "newuser"]

    await add_participant_to_tournament(tournament["_id"], "testuser2")
    updated_tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    assert updated_tournament["status"] == "pending"
    assert updated_tournament["confirmed_participants"] == ["testuser", "newuser", "testuser2"]
    

@pytest.mark.anyio
async def test_add_participant_to_nonexistent_tournament():
    await clear_tournaments()

    with pytest.raises(HTTPException) as exc_info:
        await add_participant_to_tournament("123", "newuser")
    assert exc_info.value.status_code == 404

@pytest.mark.anyio
async def test_add_participant_to_full_open_tournament():
    await clear_tournaments()
    await create_new_tournament(mock_request_data_open_full, owner="testuser")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})

    with pytest.raises(HTTPException) as exc_info:
        await add_participant_to_tournament(tournament["_id"], "newuser")
    assert exc_info.value.status_code == 400

@pytest.mark.anyio
async def test_add_participant_to_closed_tournament_not_invited():
    await clear_tournaments()
    await create_new_tournament(mock_request_data_closed_not_invited, owner="testuser")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})

    with pytest.raises(HTTPException) as exc_info:
        await add_participant_to_tournament(tournament["_id"], "newuser")
    assert exc_info.value.status_code == 400
    await clear_tournaments()

@pytest.mark.anyio
async def test_start_tournament():
    tournament, _ = await setup_basic_tournament()

    assert tournament["status"] == "started"
    assert tournament["confirmed_participants"] == ["testuser", "testuser2", "testuser3", "testuser4"]
    assert tournament["participants"] == ["testuser", "testuser2", "testuser3", "testuser4"]
    assert len(tournament["match_ids"]) == 2
    assert len(tournament["stats"]) == 4
    
    for stat in tournament["stats"]:
            assert stat["wins"] == 0
            assert stat["losses"] == 0
            assert stat["matches"] == 0
            assert stat["points"] == 0

@pytest.mark.anyio
async def test_create_round_robin_tournament_round():
    tournament, tournament_id = await setup_basic_tournament()
    g1_id, g2_id = tournament["match_ids"]

    assert g1_id != g2_id

    g1 = await get_db().matches.find_one({"_id": g1_id})
    g1_p1, g1_p2 = g1["player1"], g1["player2"]
    assert g1 is not None
    assert g1_p1 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g1_p2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g1_p1 != g1_p2

    g2 = await get_db().matches.find_one({"_id": g2_id})
    g2_p1, g2_p2 = g2["player1"], g2["player2"]
    assert g2 is not None
    assert g2_p1 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g2_p2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g2_p1 != g2_p2

    await clear_matches()
    await create_round_robin_tournament_round(tournament_id, 2)

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    g1_id_2, g2_id_2 = tournament["match_ids"]

    assert g1_id_2 != g2_id_2
    assert g1_id != g1_id_2
    assert g2_id != g2_id_2

    g1_2 = await get_db().matches.find_one({"_id": g1_id_2})
    g1_p1_2, g1_p2_2 = g1_2["player1"], g1_2["player2"]
    assert g1_2 is not None
    assert g1_p1_2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g1_p2_2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g1_p1_2 != g1_p2_2

    g2_2 = await get_db().matches.find_one({"_id": g2_id_2})
    g2_p1_2, g2_p2_2 = g2_2["player1"], g2_2["player2"]
    assert g2_2 is not None
    assert g2_p1_2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g2_p2_2 in ["testuser", "testuser2", "testuser3", "testuser4"]
    assert g2_p1_2 != g2_p2_2


async def setup_basic_tournament():
    await clear_tournaments()
    await create_new_tournament(mock_request_data, owner="testuser")
    await get_db().tournaments.update_one(
        {"owner": "testuser"},
        {"$set": {
            "participants": ["testuser", "testuser2", "testuser3", "testuser4"],
            "confirmed_participants": ["testuser", "testuser2", "testuser3", "testuser4"]
        }
        }
    )
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    tournament_id = tournament["_id"]
    await start_tournament(tournament_id)
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    return tournament, tournament_id


@pytest.mark.anyio
async def test_get_tournament_of_game():
    await clear_tournaments()
    await clear_matches()

    missing_tournament = await get_tournament_of_game("123")
    assert missing_tournament is None

    await create_new_tournament(mock_request_data, owner="testuser")
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    tournament_id = tournament["_id"]
    await add_participant_to_tournament(tournament_id, "testuser2")
    await add_participant_to_tournament(tournament_id, "testuser3")
    await add_participant_to_tournament(tournament_id, "testuser4")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    g1_id, g2_id = tournament["match_ids"]
    tournament = Tournament(**tournament)


    assert await get_tournament_of_game(g1_id) == tournament
    assert await get_tournament_of_game(g2_id) == tournament

@pytest.mark.anyio
async def test_end_tournament():
    await clear_tournaments()
    await create_new_tournament(mock_request_data, owner="testuser")
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    tournament_id = tournament["_id"]
    await add_participant_to_tournament(tournament_id, "testuser2")
    await add_participant_to_tournament(tournament_id, "testuser3")
    await add_participant_to_tournament(tournament_id, "testuser4")

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    await end_tournament(tournament)

    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    assert tournament["status"] == "finished"


async def get_tournament_as_class_object(owner):
    tournament = await get_db().tournaments.find_one({"owner": owner})
    return Tournament(**tournament)

async def get_match_as_class_object(id):
    match = await get_db().matches.find_one({"_id": id})
    return Match(**match)

@pytest.mark.anyio
async def test_update_tournament_stats():
    await clear_tournaments()
    await create_new_tournament(mock_request_data, owner="testuser")
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    tournament_id = tournament["_id"]
    await add_participant_to_tournament(tournament_id, "testuser2")
    await add_participant_to_tournament(tournament_id, "testuser3")
    await add_participant_to_tournament(tournament_id, "testuser4")

    tournament = await get_tournament_as_class_object("testuser")
    await update_tournament_stats(tournament, "testuser", "testuser2", 2)
    tournament = await get_tournament_as_class_object("testuser")
    assert tournament.stats[0].wins == 1
    assert tournament.stats[0].matches == 1
    assert tournament.stats[0].points == 2
    assert tournament.stats[0].losses == 0
    assert tournament.stats[1].wins == 0
    assert tournament.stats[1].matches == 1
    assert tournament.stats[1].points == 0
    assert tournament.stats[1].losses == 1

    await update_tournament_stats(tournament, "testuser", "testuser3", 5)
    assert tournament.stats[0].wins == 2
    assert tournament.stats[0].matches == 2
    assert tournament.stats[0].points == 7
    assert tournament.stats[0].losses == 0
    assert tournament.stats[2].wins == 0
    assert tournament.stats[2].matches == 1
    assert tournament.stats[2].points == 0
    assert tournament.stats[2].losses == 1

@pytest.mark.anyio
async def test_update_tournament_of_game():
    await clear_tournaments()
    await clear_matches()

    await create_new_tournament(mock_request_data, owner="testuser")
    tournament = await get_db().tournaments.find_one({"owner": "testuser"})
    tournament_id = tournament["_id"]
    await add_participant_to_tournament(tournament_id, "testuser2")
    await add_participant_to_tournament(tournament_id, "testuser3")
    await add_participant_to_tournament(tournament_id, "testuser4")

    tournament = await get_tournament_as_class_object("testuser")
    m1_id, m2_id = tournament.match_ids
    m1 = await get_match_as_class_object(m1_id)
    m2 = await get_match_as_class_object(m2_id)

    await get_db().matches.update_one({"player1": m1.player1}, {"$set": {"status": "won_player_1"}})
    await update_tournament_of_game(m1, m1.player1, m1.player2, 3)
    tournament = await get_tournament_as_class_object("testuser")
    tot_w_after = sum(stat.wins for stat in tournament.stats)
    tot_l_after = sum(stat.losses for stat in tournament.stats)
    tot_m_after = sum(stat.matches for stat in tournament.stats)
    tot_p_after = sum(stat.points for stat in tournament.stats)

    assert tot_w_after == 1
    assert tot_l_after == 1
    assert tot_m_after == 2
    assert tot_p_after == 3

    await get_db().matches.update_one({"player1": m2.player1}, {"$set": {"status": "won_player_1"}})
    await update_tournament_of_game(m2, m2.player1, m2.player2, 4)
    tournament = await get_tournament_as_class_object("testuser")
    tot_w_after = sum(stat.wins for stat in tournament.stats)
    tot_l_after = sum(stat.losses for stat in tournament.stats)
    tot_m_after = sum(stat.matches for stat in tournament.stats)
    tot_p_after = sum(stat.points for stat in tournament.stats)

    assert tot_w_after == 2
    assert tot_l_after == 2
    assert tot_m_after == 4
    assert tot_p_after == 7

    m1_id_new, m2_id_new = tournament.match_ids
    assert m1_id != m1_id_new
    assert m2_id != m2_id_new
    assert m1_id_new != m2_id_new