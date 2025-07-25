from fastapi.security import OAuth2PasswordBearer
from copy import deepcopy
from datetime import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
from typing import List

from pydantic import BaseModel, Field
from services.database import default_id


class Point(BaseModel):
    player1: int
    player2: int

    def __init__(self, player1: int = 0, player2: int = 0):
        super().__init__(player1=player1, player2=player2)


# Starting configuration of the board
DEFAULT_POINTS: List[Point] = [
    Point(0, 2),  # Point 1
    Point(0, 0),  # Point 2
    Point(0, 0),  # Point 3
    Point(0, 0),  # Point 4
    Point(0, 0),  # Point 5
    Point(5, 0),  # Point 6
    Point(0, 0),  # Point 7
    Point(3, 0),  # Point 8
    Point(0, 0),  # Point 9
    Point(0, 0),  # Point 10
    Point(0, 0),  # Point 11
    Point(0, 5),  # Point 12
    Point(5, 0),  # Point 13
    Point(0, 0),  # Point 14
    Point(0, 0),  # Point 15
    Point(0, 0),  # Point 16
    Point(0, 3),  # Point 17
    Point(0, 0),  # Point 18
    Point(0, 5),  # Point 19
    Point(0, 0),  # Point 20
    Point(0, 0),  # Point 21
    Point(0, 0),  # Point 22
    Point(0, 0),  # Point 23
    Point(2, 0)  # Point 24
]


class BoardConfiguration(BaseModel):
    points: List[Point]
    bar: Point

    def __init__(self, points: List[Point] = None, bar: Point = None):
        points = deepcopy(DEFAULT_POINTS) if points is None else points
        bar = Point(player1=0, player2=0) if bar is None else bar
        super().__init__(points=points, bar=bar)


class StartDice(BaseModel):
    roll1: int
    count1: int
    roll2: int
    count2: int

    def __init__(self, roll1: int = 0, count1: int = 0, roll2: int = 0, count2: int = 0):
        super().__init__(roll1=roll1, count1=count1, roll2=roll2, count2=count2)


class DoublingCube(BaseModel):
    count: int
    last_usage: int
    proposed: bool
    proposer: int

    def __init__(self, count: int = 0, last_usage: int = 0, proposed: bool = False, proposer: int = 0):
        super().__init__(count=count, last_usage=last_usage, proposed=proposed, proposer=proposer)


class Match(BaseModel):
    id: str = Field(default_factory=default_id, alias="_id")
    player1: str
    player2: str
    board_configuration: BoardConfiguration = BoardConfiguration()
    dice: List[int] = []
    available: List[int] = []
    turn: int = -1
    last_updated: str = Field(default_factory=lambda: datetime.now().replace(microsecond=0).isoformat()) #ISO format without microseconds
    status: str = "pending"
    rounds_to_win: int
    winsP1: int = 0
    winsP2: int = 0
    starter: int = 0
    startDice: StartDice = StartDice()
    ai_suggestions: List[int] = Field(default_factory=lambda: [0, 0])
    doublingCube: DoublingCube = DoublingCube()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def __setattr__(self, name, value):
        if name != "last_updated":
            super().__setattr__("last_updated", datetime.now().replace(microsecond=0).isoformat())
        super().__setattr__(name, value)

    def get_last_modified_time(self) -> str:
        return self.last_updated


class CreateInviteRequest(BaseModel):
    opponent_username: str
    rounds_to_win: int
    use_email: bool = False


class AcceptInviteRequest(BaseModel):
    invite_id: str
