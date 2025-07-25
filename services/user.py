from models.user import UserInDB, UserOnline, UserInLeaderboard
from services.database import get_db


async def get_user(username: str):
    user = await get_db().users.find_one({"username": username})
    if user:
        return UserInDB(**user)


async def get_usernames_starting_with(query: str):
    cursor = get_db().users.find(
        {"username": {"$regex": f"^{query}"}},
        {"_id": 1, "username": 1}  # Include both _id and username fields
    ).limit(10)
    usernames = []
    async for user in cursor:
        usernames.append({"id": str(user["_id"]), "username": user["username"]})
    return usernames


async def get_all_users():
    users = await get_db().users.find().to_list(length=None)
    return [UserOnline(**user) for user in users]


async def get_all_users_leaderboard():
    users = await get_db().users.find().to_list(length=None)
    return [UserInLeaderboard(**user) for user in users]
