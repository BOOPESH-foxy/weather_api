# app_blue/main.py
import os, httpx
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("WEATHER_API_KEY")
app = FastAPI(title="Weather API v1 - Blue")

@app.get("/weather/{city}")
async def get_weather(city: str):
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}"
    params = {"unitGroup": "metric", "key": API_KEY, "contentType": "json"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="API Error")
        
        # Notice: No Redis logic here!
        return {"version": "v1-blue", "source": "direct_api", "data": response.json()}