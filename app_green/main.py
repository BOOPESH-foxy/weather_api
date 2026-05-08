import os
import json
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("WEATHER_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

# Initialize Redis client
r = redis.from_url(REDIS_URL, decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    try:
        await r.ping()
        print("✅ SUCCESS: Connected to Redis")
    except Exception as e:
        print(f"❌ ERROR: Redis connection failed: {e}")
    yield
    await r.close()

app = FastAPI(title="Weather API Wrapper", lifespan=lifespan)

@app.get("/weather/{city}")
async def get_weather(city: str):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key missing in .env")

    # 1. Check Redis Cache (The "Fridge")
    cache_key = f"weather:{city.lower().strip()}"
    try:
        cached_data = await r.get(cache_key)
        if cached_data:
            return {
                "source": "cache",
                "city": city,
                "data": json.loads(cached_data)
            }
    except Exception as e:
        print(f"⚠️ Redis Error: {e}")

    # 2. Fetch from Visual Crossing (The "Kitchen")
    # Correct Timeline URL format: /timeline/[location]?key=[key]
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/"
    
    params = {
        "unitGroup": "metric",
        "key": API_KEY,
        "contentType": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code != 200:
                print(f"❌ API Error {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail="Location not found or API limit reached."
                )
            
            data = response.json()
            
            # 3. Save to Redis for 12 hours (43200 seconds)
            await r.setex(cache_key, 43200, json.dumps(data))
            
            return {
                "source": "api",
                "city": city,
                "data": data
            }
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Weather service unreachable: {e}")

@app.get("/")
async def root():
    return {"message": "Weather Wrapper API is Online. Use /weather/{city}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)