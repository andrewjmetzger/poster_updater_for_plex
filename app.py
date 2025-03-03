# -*- coding: utf-8 -*-AAAAAA
import os
import logging
import json
import validators
import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from plexapi.server import PlexServer

app = Flask(__name__)

CONFIG_FILE = "config.json"

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
app = Flask(__name__)
# Load configuration settings
def load_config():
    plex_url = os.getenv("PLEX_URL", "").strip()
    plex_token = os.getenv("PLEX_TOKEN", "").strip()
    tmdb_api_key = os.getenv("TMDB_API_KEY", "").strip()
    library_name = os.getenv("PLEX_LIBRARY", "Movies").strip()
    web_port = os.getenv("WEB_PORT", "5000").strip()

    # Ensure PLEX_URL starts with "http://"
    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    if not plex_url or not plex_token or not tmdb_api_key:
        raise ValueError("Missing required environment variables (PLEX_URL, PLEX_TOKEN, TMDB_API_KEY)")

    return {
        "plex_url": plex_url,
        "plex_token": plex_token,
        "tmdb_api_key": tmdb_api_key,
        "library_name": library_name,
        "web_port": web_port
    }

# Fetch TMDb poster
def get_tmdb_poster(title, year, api_key):
    """Fetch TMDb poster URL based on movie title & year."""
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}&year={year}"
    response = requests.get(search_url).json()
    if response.get("results"):
        return f"https://image.tmdb.org/t/p/w500{response['results'][0].get('poster_path')}"
    return None

# Fetch movies dynamically based on user selection
@app.route("/fetch-posters", methods=["POST"])
def fetch_posters():
    """Fetch movies based on time range selection."""
    config = load_config()
    plex = PlexServer(config["plex_url"], config["plex_token"])
    library = plex.library.section(config["library_name"])

    time_map = {"1 week": 7, "2 weeks": 14, "1 month": 30, "all": 9999}
    selected_time = request.json.get("time_range", "1 week")
    days_back = time_map.get(selected_time, 7)

    since_date = datetime.now() - timedelta(days=days_back)
    all_movies = library.all()
    
    # Filter movies based on time range
    filtered_movies = [m for m in all_movies if m.addedAt >= since_date]
    
    logging.debug(f"Fetching posters for {len(filtered_movies)} movies")

    # 🔥 Sort movies by `addedAt` in descending order (newest first)
    filtered_movies.sort(key=lambda x: x.addedAt, reverse=True)

    movies = []
    for index, movie in enumerate(filtered_movies, start=1):
        movies.append({
            "title": movie.title,
            "year": movie.year,
            "plex_poster": movie.posterUrl,
            "tmdb_poster": get_tmdb_poster(movie.title, movie.year, config["tmdb_api_key"]),
            "ratingKey": movie.ratingKey
        })
        logging.debug(f"Progress: {index}/{len(filtered_movies)}")

    return jsonify({"movies": movies, "total": len(filtered_movies)})

@app.route("/search-movie", methods=["POST"])
def search_movie():
    """Search for a movie by name in Plex."""
    config = load_config()
    plex = PlexServer(config["plex_url"], config["plex_token"])
    library = plex.library.section(config["library_name"])
    search_query = request.json.get("query", "").strip().lower()

    logging.debug(f"Searching for movie: {search_query}")

    matching_movies = library.search(search_query)

    # 🔥 Sort search results by `addedAt` (newest first)
    matching_movies.sort(key=lambda x: x.addedAt, reverse=True)

    movies = [{
        "title": movie.title,
        "year": movie.year,
        "plex_poster": movie.posterUrl,
        "tmdb_poster": get_tmdb_poster(movie.title, movie.year, config["tmdb_api_key"]),
        "ratingKey": movie.ratingKey
    } for movie in matching_movies]

    return jsonify({"movies": movies, "total": len(matching_movies)})

@app.route("/apply-changes", methods=["POST"])
def apply_changes():
    config = load_config()
    plex_url = config["plex_url"].rstrip("/")  # Ensure no trailing slash
    plex = PlexServer(plex_url, config["plex_token"])

    selected_movies = request.json.get("selected_movies", [])
    response_messages = []

    if not selected_movies:
        response_messages.append("⚠ No movies selected for poster updates.")
        logging.debug("No movies selected for updating.")
        return jsonify({"messages": response_messages})

    for movie_id, new_poster_url in selected_movies:
        try:
            logging.debug(f"🔄 Processing Movie ID: {movie_id}")
            response_messages.append(f"🔄 Processing Movie ID {movie_id}...")

            # Validate the new poster URL
            if not new_poster_url.startswith("http"):
                response_messages.append(f"❌ Error: Invalid poster URL: {new_poster_url}")
                logging.error(f"Invalid poster URL: {new_poster_url}")
                continue

            # Ensure proper formatting of API request URL
            request_url = f"{plex_url}/library/metadata/{movie_id}"
            logging.debug(f"📡 Fetching movie from: {request_url}")
            response_messages.append(f"📡 Fetching movie from: {request_url}")

            # Validate movie_id as an integer
            if not str(movie_id).isdigit():
                response_messages.append(f"❌ Error: Invalid movie ID {movie_id}.")
                logging.error(f"Invalid movie ID: {movie_id}")
                continue

            # Fetch movie from Plex
            movie = plex.fetchItem(int(movie_id))
            if movie:
                response_messages.append(f"✅ Found movie: {movie.title} (ID: {movie_id})")
                response_messages.append(f"📸 Applying TMDb Poster: {new_poster_url}")
                logging.debug(f"✅ Found movie: {movie.title} (ID: {movie_id})")

                # Apply the new poster from TMDb
                movie.uploadPoster(url=new_poster_url)
                response_messages.append(f"🎉 Successfully updated poster for {movie.title}!")
                logging.debug(f"🎉 Successfully updated poster for {movie.title}")

            else:
                response_messages.append(f"❌ Error: Movie ID {movie_id} not found in Plex.")
                logging.error(f"Movie ID {movie_id} not found in Plex.")

        except Exception as e:
            error_msg = f"❌ Error updating {movie_id}: {str(e)}"
            response_messages.append(error_msg)
            logging.error(error_msg)

    return jsonify({"messages": response_messages})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

