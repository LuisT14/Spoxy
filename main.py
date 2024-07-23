import io
import aiohttp
import asyncio
import os
from PIL import Image
import base64
from urllib.parse import urlencode
from datetime import datetime, timedelta
from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse

# Simple proxy for spotify api.
CLIENT_ID = ""
CLIENT_SECRET = ""
SPOTIFY_API_URL = "https://api.spotify.com/"
SCOPES = "user-modify-playback-state user-read-playback-state"
CLIENT_BASE64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
# Size of the image to resize to. Width and height.
RESIZE_SIZE = (160, 128)

DB = {
    "access_token": "",
    "refresh_token": "",
    "time_to_refresh": datetime.now(),
    "started": False
}

app = FastAPI()

async def GetAndPossiblyRefreshToken():
    if not DB["started"]:
        return None
    if datetime.now() > DB["time_to_refresh"]:
        token_url = "https://accounts.spotify.com/api/token"
        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/x-www-form-urlencoded",
                       "Authorization": f"Basic {CLIENT_BASE64}"}
            data = {"grant_type": "refresh_token", "refresh_token": DB["refresh_token"]}
            async with session.post(token_url, headers=headers, data=data) as response:
                json_response = await response.json()
                DB["access_token"] = json_response["access_token"]
                DB["time_to_refresh"] = datetime.now() + timedelta(seconds=json_response["expires_in"])
            print(f"Token refreshed at {datetime.now()}")
    return DB["access_token"]

@app.get("/login")
async def GetAuthUrl():
    auth_url = "https://accounts.spotify.com/authorize"
    params = {"client_id": CLIENT_ID, "response_type": "code", "redirect_uri": "http://localhost:8000/callback", "scope": SCOPES}
    return RedirectResponse(f"{auth_url}?{urlencode(params)}")

@app.get("/callback")
async def Callback(code: str | None = None, error: str | None = None):
    token_url = "https://accounts.spotify.com/api/token"
    if code:
        AUTHORIZATION_CODE = code
        # Get Access token
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Basic {CLIENT_BASE64}"}
            data = {"grant_type": "authorization_code", "code": AUTHORIZATION_CODE, "redirect_uri": "http://localhost:8000/callback"}
            async with session.post(token_url, headers=headers, data=data) as response:
                json_response = await response.json()
                DB["access_token"] = json_response["access_token"]
                DB["refresh_token"] = json_response["refresh_token"]
                DB["time_to_refresh"] = datetime.now() + timedelta(seconds=json_response["expires_in"])   
                DB["started"] = True
                return "Authorization code received and access token obtained"

# Proxy for spotify api.
@app.get("/spotify/{endpoint:path}")
async def CurrentState(endpoint: str):
    token = await GetAndPossiblyRefreshToken()
    if not token:
        return {"error": "No access token"}
    print(f"Getting {SPOTIFY_API_URL}{endpoint}")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SPOTIFY_API_URL}{endpoint}", headers={"Authorization": f"Bearer {token}"}) as response:
            if response.status == 200:
                return await response.json()
            return {"error": f"{response.status} {response.reason}"}

# Proxy for spotify api.
@app.post("/spotify/{endpoint:path}")
async def CurrentState(endpoint: str, data: dict):
    token = await GetAndPossiblyRefreshToken()
    if not token:
        return {"error": "No access token"}
    print(f"Posting {SPOTIFY_API_URL}{endpoint}")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SPOTIFY_API_URL}{endpoint}", headers={"Authorization": f"Bearer {token}"}, data=data) as response:
            if response.status == 200:
                return await response.json()
            return {"error": f"{response.status} {response.reason}"}

# Resize image and turn into jpeg. This is used to get pico/pico display compatible images from the spotify api
@app.get("/image")
async def GetImage(image_url: str):
    print(f"Getting image {image_url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            image = Image.open(io.BytesIO(await response.read()))
            image = image.resize(RESIZE_SIZE)
            image = image.convert("RGB")
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            return Response(content=img_byte_arr, media_type="image/jpeg")