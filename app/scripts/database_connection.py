# This file handles the MongoDB connection using Motor.
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime

# Retrieve the MongoDB connection string from environment variables or use the default.
# NOTE: Using a sensitive key directly in code is not recommended for production.
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Kevin:Year2006@users.s5a3uxi.mongodb.net/?retryWrites=true&w=majority&appName=Users")

# Initialize the async MongoDB client
client = AsyncIOMotorClient(MONGO_URI)

# Select the 'kmrl_summaries' database
db = client.kmrl_summaries

# collection: summaries
