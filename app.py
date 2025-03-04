# -*- coding: utf-8 -*-AAAAAA
import os
import json
import logging
import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from plexapi.server import PlexServer

app = Flask(__name__)

# ✅ Fix `debug_log()` to always use the global config dictionary
def debug_log(message):
    """Logs debug messages only if debug mode is enabled."""
    if config.get("debug_mode", False):  # Use .get() to avoid KeyError
        logging.debug(message)

def load_config():
    """Load configuration from environment variables."""
    plex_url = os.getenv("PLEX_URL", "").strip()
    plex_token = os.getenv("PLEX_TOKEN", "").strip()
    tmdb_api_key = os.getenv("TMDB_API_KEY", "").strip()
    library_name = os.getenv("PLEX_LIBRARY", "Movies").strip()
    web_port = os.getenv("WEB_PORT", "5000").strip()
    debug_mode = os.getenv("DEBUG", "true").strip().lower() == "true"

    print(f"Before modification, plex_url: {repr(plex_url)}")

    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    if not plex_url or not plex_token or not tmdb_api_key:
        raise ValueError("Missing required environment variables (PLEX_URL, PLEX_TOKEN, TMDB_API_KEY)")

    # ✅ Now using `debug_log()` without passing debug_mode
    return {
        "plex_url": plex_url,
        "plex_token": plex_token,
        "tmdb_api_key": tmdb_api_key,
        "library_name": library_name,
        "web_port": web_port,
        "debug_mode": debug_mode
    }

# ✅ Load config AFTER defining load_config()
config = load_config()

# ✅ Configure logging based on DEBUG mode
logging_level = logging.DEBUG if config["debug_mode"] else logging.WARNING
logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Use `debug_log()` freely without passing `debug_mode`
debug_log("Configuration loaded successfully")

def debug_log(message):
    """Logs debug messages only if debug mode is enabled."""
    if config["debug_mode"]:
        logging.debug(message)
def get_tmdb_poster(title, year, api_key):
    """Fetch TMDb poster URL based on movie title & year."""
    debug_log(f"Starting step: Fetching TMDb poster for {title} ({year})")
    
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}&year={year}"
    response = requests.get(search_url).json()
    
    if response.get("results"):
        poster_url = f"https://image.tmdb.org/t/p/w500{response['results'][0].get('poster_path')}"
        debug_log(f"Fetched TMDb poster: {poster_url}")
        return poster_url

    debug_log(f"No poster found on TMDb for {title}")
    return None

@app.route("/fetch-posters", methods=["POST"])
def fetch_posters():
    """Fetch movies dynamically based on time range selection."""
    debug_log("Starting step: Fetching posters from Plex")

    config = load_config()
    try:
        plex = PlexServer(config["plex_url"], config["plex_token"])
    except Exception as e:
        logging.error(f"Error connecting to Plex: {e}")
        return jsonify({"error": f"Failed to connect to Plex: {e}"}), 500

    library = plex.library.section(config["library_name"])
    time_map = {"1 week": 7, "2 weeks": 14, "1 month": 30, "all": 9999}
    selected_time = request.json.get("time_range", "1 week")
    days_back = time_map.get(selected_time, 7)

    since_date = datetime.now() - timedelta(days=days_back)
    all_movies = library.all()
    filtered_movies = [m for m in all_movies if m.addedAt >= since_date]

    debug_log(f"Total movies found: {len(filtered_movies)}")

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
        debug_log(f"Progress: {index}/{len(filtered_movies)}")

    debug_log("Fetching posters complete")
    return jsonify({"movies": movies, "total": len(filtered_movies)})

@app.route("/search-movie", methods=["POST"])
def search_movie():
    """Search for a movie by name in Plex."""
    debug_log("Starting step: Searching for a movie in Plex")

    config = load_config()
    plex = PlexServer(config["plex_url"], config["plex_token"])
    library = plex.library.section(config["library_name"])
    search_query = request.json.get("query", "").strip().lower()

    matching_movies = library.search(search_query)
    matching_movies.sort(key=lambda x: x.addedAt, reverse=True)

    debug_log(f"Found {len(matching_movies)} matching movies")

    movies = [{
        "title": movie.title,
        "year": movie.year,
        "plex_poster": movie.posterUrl,
        "tmdb_poster": get_tmdb_poster(movie.title, movie.year, config["tmdb_api_key"]),
        "ratingKey": movie.ratingKey
    } for movie in matching_movies]

    debug_log("Search complete")
    return jsonify({"movies": movies, "total": len(matching_movies)})

@app.route("/apply-changes", methods=["POST"])
def apply_changes():
    """Apply poster updates to selected movies in Plex."""
    debug_log("Starting step: Applying poster updates")

    config = load_config()
    plex = PlexServer(config["plex_url"], config["plex_token"])
    selected_movies = request.json.get("selected_movies", [])
    response_messages = []

    if not selected_movies:
        debug_log("No movies selected for updating")
        return jsonify({"messages": ["No movies selected for poster updates."]})

    for movie_id, new_poster_url in selected_movies:
        debug_log(f"Processing Movie ID: {movie_id}")

        if not new_poster_url.startswith("http"):
            debug_log(f"Invalid poster URL: {new_poster_url}")
            response_messages.append(f"Error: Invalid poster URL: {new_poster_url}")
            continue

        try:
            movie = plex.fetchItem(int(movie_id))
            if movie:
                debug_log(f"Found movie: {movie.title} (ID: {movie_id})")
                movie.uploadPoster(url=new_poster_url)
                response_messages.append(f"Successfully updated poster for {movie.title}!")
            else:
                debug_log(f"Movie ID {movie_id} not found in Plex.")
                response_messages.append(f"Error: Movie ID {movie_id} not found.")
        except Exception as e:
            logging.error(f"Error updating {movie_id}: {e}")
            response_messages.append(f"Error updating {movie_id}: {str(e)}")

    debug_log("Poster updates complete")
    return jsonify({"messages": response_messages})

#config = load_config()

# Configure logging level based on DEBUG environment variable
logging_level = logging.DEBUG if config["debug_mode"] else logging.WARNING
logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to log debug messages if DEBUG mode is enabled
#def debug_log(message):
#    if config["debug_mode"]:
#        logging.debug(message)

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0", 
        port=int(config["web_port"]), 
        debug=config["debug_mode"], 
        threaded=True
    )
