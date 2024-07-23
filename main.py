import io
import aiohttp
import asyncio
import os
from PIL import Image
import base64
from urllib.parse import urlencode
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse

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
                DB["refresh_token"] = json_response["refresh_token"]
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

@app.get("/spotify/{endpoint:path}")
async def ProxyGet(request: Request, endpoint: str):
    return await ProxyRequest(request, endpoint, "GET")

@app.post("/spotify/{endpoint:path}")
async def ProxyPost(request: Request, endpoint: str):
    return await ProxyRequest(request, endpoint, "POST")

@app.put("/spotify/{endpoint:path}")
async def ProxyPut(request: Request, endpoint: str):
    return await ProxyRequest(request, endpoint, "PUT")

async def ProxyRequest(request: Request, endpoint: str, method: str):
    # Get auth token for spotify api.
    token = await GetAndPossiblyRefreshToken()
    if not token:
        return {"error": "No access token"}
    
    url = f"{SPOTIFY_API_URL}{endpoint}"
    # Use all headers from the request except for host and content-length.
    headers = {key: value for key, value in request.headers.items() if key.lower() not in ['host', 'content-length']}
    # Add token to the headers.
    headers["Authorization"] = f"Bearer {token}"

    async with aiohttp.ClientSession() as session:
        # Create the request.
        req_kwargs = {
            "url": url,
            "headers": headers,
            "params": request.query_params,
        }
        # If the method is POST or PUT, add the body to the request.
        if method in ["POST", "PUT"]:
            req_kwargs["data"] = await request.body()

        async with session.request(method, **req_kwargs) as response:
            # Get the headers from the response.
            response_headers = dict(response.headers)
            # Remove problematic headers
            response_headers.pop('Content-Encoding', None)
            response_headers.pop('Transfer-Encoding', None)
            # Read conent and send it as a response.
            content = await response.read()
            return Response(
                content=content,
                status_code=response.status,
                headers=response_headers,
            )

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
