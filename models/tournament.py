from pydantic import BaseModel, Field
from typing import List
from services.database import default_id


class TournamentStats(BaseModel):
    username: str
    wins: int
    losses: int
    matches: int
    points: int

class Tournament(BaseModel):
    id: str = Field(default_factory=default_id, alias="_id")
    owner: str
    type: str
    participants: List[str]
    confirmed_participants: List[str]
    open: bool
    match_ids: List[str]
    name: str
    status: str
    rounds_to_win: int
    stats: List[TournamentStats]

class CreateTournamentRequest(BaseModel):
    name: str
    participants: List[str]
    open: bool
    rounds_to_win: int
    type: str

class JoinTournamentRequest(BaseModel):
    owner: str
    name: str