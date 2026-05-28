import aiohttp
from motor.motor_asyncio import AsyncIOMotorCollection

# Initialize MongoDB collection for words
word_collection = None  # This would be initialized with your MongoDB connection

async def is_valid_word(word: str) -> bool:
    """Check if a word exists in the dictionary"""
    # First check MongoDB cache
    if word_collection:
        cached = await word_collection.find_one({"word": word.lower()})
        if cached:
            return True
    
    # If not in cache, check external dictionary API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as resp:
                if resp.status == 200:
                    # Cache the word for future checks
                    if word_collection:
                        await word_collection.update_one(
                            {"word": word.lower()},
                            {"$set": {"word": word.lower()}},
                            upsert=True
                        )
                    return True
    except:
        pass
    
    return False

async def get_random_word(length: int) -> str:
    """Get a random word of specific length"""
    # Try to get from MongoDB first
    if word_collection:
        pipeline = [
            {"$match": {"$expr": {"$eq": [{"$strLenCP": "$word"}, length]}}},
            {"$sample": {"size": 1}}
        ]
        word = await word_collection.aggregate(pipeline).to_list(1)
        if word:
            return word[0]["word"]
    
    # Fallback to API if not found in DB
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://random-word-api.herokuapp.com/word?length={length}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[0]
    except:
        pass
    
    # Final fallback - generate random letters
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))
