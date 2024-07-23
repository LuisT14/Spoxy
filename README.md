# Spoxy

Spoxy is a simple, single-user proxy for Spotify with image convertor.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/LuisT14/spoxy.git
   cd spoxy
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Spotify API credentials:
   - Create a Spotify Developer account and register your application
   - Set the `CLIENT_ID` and `CLIENT_SECRET` variables in the script with your Spotify API credentials

## Usage

To run the server:

```
fastapi dev --host 0.0.0.0 --port 8000
```

The server will run on `http://localhost:8000`.

or

```
fastapi run
```

The server will run on `http://localhost:80`.

## Endpoints

### Authentication

- **GET /login**
  - Initiates the Spotify OAuth flow
  - Redirects the user to the Spotify authorization page

- **GET /callback**
  - Handles the callback from Spotify after successful authorization
  - Exchanges the authorization code for access and refresh tokens

### Spotify API Proxy

- **GET /spotify/{endpoint}**
  - Proxies GET requests to the Spotify API
  - Replace `{endpoint}` with the desired Spotify API endpoint
  - Automatically handles token refresh

- **POST /spotify/{endpoint}**
  - Proxies POST requests to the Spotify API
  - Replace `{endpoint}` with the desired Spotify API endpoint
  - Automatically handles token refresh

### Image Processing

- **GET /image**
  - Fetches and resizes an image from a given URL
  - Query parameter: `image_url`
  - Resizes the image to 160x128 pixels and converts it to JPEG format
  - Useful for preparing album artwork for small displays

## Example Usage

1. Start the authentication process:
   ```
   http://localhost:8000/login
   ```

2. After successful authentication, you can make requests to the Spotify API:
   ```
   http://localhost:8000/spotify/v1/me/player
   ```

3. To resize an album artwork:
   ```
   http://localhost:8000/image?image_url=https://i.scdn.co/image/ab67616d0000b273...
   ```
