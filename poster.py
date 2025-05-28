from fastapi import FastAPI, Query, Response, HTTPException
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = FastAPI()

TMDB_API_KEY = "de19ae80ab28129b35fc510770e30b48"
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_DETAILS_URL = "https://api.themoviedb.org/3/movie/{id}/images"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def fetch_tmdb_movie(title, year=None):
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "include_adult": False,
        "language": "en-US",
    }
    if year:
        params["year"] = year
    response = requests.get(TMDB_SEARCH_URL, params=params)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None

def fetch_backdrop_image(movie_id):
    url = TMDB_MOVIE_DETAILS_URL.format(id=movie_id)
    response = requests.get(url, params={"api_key": TMDB_API_KEY})
    response.raise_for_status()
    data = response.json()
    for image in data.get("backdrops", []):
        if image.get("iso_639_1") == "hi":
            return TMDB_IMAGE_BASE_URL + image["file_path"]
    if data.get("backdrops"):
        return TMDB_IMAGE_BASE_URL + data["backdrops"][0]["file_path"]
    return None

def overlay_text(image_bytes, text):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    font_size = int(height * 0.07)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    text_width, text_height = draw.textsize(text, font=font)
    position = ((width - text_width) // 2, height - text_height - 40)
    draw.text((position[0] + 2, position[1] + 2), text, font=font, fill="black")
    draw.text(position, text, font=font, fill="white")
    output = BytesIO()
    image.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output.read()

@app.get("/api/v1/poster")
def get_poster(title: str = Query(...), year: Optional[int] = Query(None)):
    movie = fetch_tmdb_movie(title, year)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    image_url = fetch_backdrop_image(movie["id"])
    if not image_url:
        raise HTTPException(status_code=404, detail="No poster found")
    image_response = requests.get(image_url)
    if image_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to download image")
    final_image = overlay_text(image_response.content, movie["title"])
    return Response(content=final_image, media_type="image/jpeg")
