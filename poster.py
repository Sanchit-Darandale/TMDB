from fastapi import FastAPI, Query, HTTPException, Response
from typing import Optional
import requests
from io import BytesIO

app = FastAPI()

TMDB_API_KEY = "de19ae80ab28129b35fc510770e30b48"
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_URL = "https://api.themoviedb.org/3/movie/{id}/images"
TMDB_BASE_IMAGE = "https://image.tmdb.org/t/p/original"

def search_tmdb_movie(title: str, year: Optional[int] = None):
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "year": year,
        "language": "en-US",
        "include_adult": False
    }
    r = requests.get(TMDB_SEARCH_URL, params=params)
    r.raise_for_status()
    data = r.json()
    return data["results"][0] if data["results"] else None

def get_backdrop_url(movie_id: int):
    r = requests.get(TMDB_IMAGE_URL.format(id=movie_id), params={"api_key": TMDB_API_KEY})
    r.raise_for_status()
    data = r.json()
    for img in data.get("backdrops", []):
        if img.get("iso_639_1") == "hi":
            return TMDB_BASE_IMAGE + img["file_path"]
    if data.get("backdrops"):
        return TMDB_BASE_IMAGE + data["backdrops"][0]["file_path"]
    return None

@app.get("/api/v1/poster")
def fetch_poster(title: str = Query(...), year: Optional[int] = Query(None)):
    try:
        movie = search_tmdb_movie(title, year)
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found.")

        backdrop_url = get_backdrop_url(movie["id"])
        if not backdrop_url:
            raise HTTPException(status_code=404, detail="No poster found.")

        img_response = requests.get(backdrop_url)
        if img_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch image.")

        return Response(content=img_response.content, media_type="image/jpeg")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
