from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from core import config

def default_id():
    return str(ObjectId())

# Ensure unique indexes for username and email
async def create_indexes():
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)

# Initialize the database connection
client = None
db = None

def initialize_db_connection():
    global client, db
    client = AsyncIOMotorClient(config.MONGODB_URL)
    db = client.backgammon
    print("Database connection initialized.")

def get_db():
    return db