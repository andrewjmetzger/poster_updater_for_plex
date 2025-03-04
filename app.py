# -*- coding: utf-8 -*-
import os
import json
import logging
import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from plexapi.server import PlexServer

app = Flask(__name__)

# ✅ Load configuration function
def load_config():
    """Load configuration from environment variables."""
    plex_url = os.getenv("PLEX_URL", "").strip()
    plex_token = os.getenv("PLEX_TOKEN", "").strip()
    tmdb_api_key = os.getenv("TMDB_API_KEY", "").strip()
    library_name = os.getenv("PLEX_LIBRARY", "Movies").strip()
    web_port = os.getenv("WEB_PORT", "5000").strip()
    debug_mode = os.getenv("DEBUG", "true").strip().lower() == "true"

    # ✅ Ensure Plex URL starts with "http://"
    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    # ✅ Debug log for configuration loading
    print(f"Loaded Config: Plex URL={plex_url}, Library={library_name}, Debug={debug_mode}")

    if not plex_url or not plex_token or not tmdb_api_key:
        raise ValueError("❌ Missing required environment variables (PLEX_URL, PLEX_TOKEN, TMDB_API_KEY)")

    return {
        "plex_url": plex_url,
        "plex_token": plex_token,
        "tmdb_api_key": tmdb_api_key,
        "library_name": library_name,
        "web_port": web_port,
        "debug_mode": debug_mode
    }

# ✅ Load config globally
config = load_config()

# ✅ Configure logging based on DEBUG mode
logging_level = logging.DEBUG if config["debug_mode"] else logging.WARNING
logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")

def debug_log(message):
    """Logs debug messages only if debug mode is enabled."""
    if config["debug_mode"]:
        logging.debug(message)

# ✅ Fetch TMDb poster
def get_tmdb_poster(title, year):
    """Fetch TMDb poster URL based on movie title & year."""
    api_key = config['tmdb_api_key']
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={title}&year={year}"

    logging.debug(f"🔍 Fetching TMDb Poster: {search_url}")

    response = requests.get(search_url)
    logging.debug(f"📝 TMDb Response Status Code: {response.status_code}")
    logging.debug(f"📝 TMDb Response Body: {response.text}")

    if response.status_code == 401:
        logging.error("❌ TMDb API Key Unauthorized! Check API key settings.")

    if response.ok and response.json().get("results"):
        return f"https://image.tmdb.org/t/p/w500{response.json()['results'][0].get('poster_path')}"

    return None

# ✅ Fetch movies dynamically based on user selection
@app.route("/fetch-posters", methods=["POST"])
def fetch_posters():
    """Fetch movies based on time range selection."""
   
    debug_log("Starting step: Fetching posters from Plex")

    plex_url = config.get("plex_url", "").strip()
    plex_token = config.get("plex_token", "").strip()

    # ✅ Ensure Plex URL starts with "http://"
    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    if not plex_url or not plex_token:
        logging.error("❌ Plex URL or Token is missing in config")
        return jsonify({"error": "Plex URL or Token missing from config"}), 500

    try:
        debug_log(f"Connecting to Plex at: {plex_url} with token: {plex_token}")
        plex = PlexServer(plex_url, plex_token)
    except Exception as e:
        logging.error(f"❌ Error connecting to Plex: {e}")
        return jsonify({"error": f"Failed to connect to Plex: {e}"}), 500

    library = plex.library.section(config["library_name"])

    time_map = {"1 week": 7, "2 weeks": 14, "1 month": 30, "all": 9999}
    selected_time = request.json.get("time_range", "1 week")
    days_back = time_map.get(selected_time, 7)

    since_date = datetime.now() - timedelta(days=days_back)
    all_movies = library.all()

    # Filter movies based on time range
    filtered_movies = [m for m in all_movies if m.addedAt >= since_date]

    debug_log(f"Found {len(filtered_movies)} movies in selected time range.")

    # ✅ Sort movies by `addedAt` in descending order (newest first)
    filtered_movies.sort(key=lambda x: x.addedAt, reverse=True)

    movies = []
    for index, movie in enumerate(filtered_movies, start=1):
        movies.append({
            "title": movie.title,
            "year": movie.year,
            "plex_poster": movie.posterUrl,
            "tmdb_poster": get_tmdb_poster(movie.title, movie.year),
            "ratingKey": movie.ratingKey
        })
        debug_log(f"Processing {index}/{len(filtered_movies)}: {movie.title}")

    return jsonify({"movies": movies, "total": len(filtered_movies)})

# ✅ Search movies by name
@app.route("/search-movie", methods=["POST"])
def search_movie():
    """Search for a movie by name in Plex."""
    search_query = request.json.get("query", "").strip().lower()
    debug_log(f"Searching for movie: {search_query}")

    plex_url = config.get("plex_url", "").strip()
    plex_token = config.get("plex_token", "").strip()

    # ✅ Ensure Plex URL starts with "http://"
    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    plex = PlexServer(plex_url, plex_token)
    library = plex.library.section(config["library_name"])

    matching_movies = library.search(search_query)

    # ✅ Sort search results by `addedAt` (newest first)
    matching_movies.sort(key=lambda x: x.addedAt, reverse=True)

    movies = [{
        "title": movie.title,
        "year": movie.year,
        "plex_poster": movie.posterUrl,
        "tmdb_poster": get_tmdb_poster(movie.title, movie.year),
        "ratingKey": movie.ratingKey
    } for movie in matching_movies]

    return jsonify({"movies": movies, "total": len(matching_movies)})

# ✅ Apply changes (update posters)
@app.route("/apply-changes", methods=["POST"])
def apply_changes():
    debug_log("Starting step: Applying changes to posters")

    selected_movies = request.json.get("selected_movies", [])
    response_messages = []

    if not selected_movies:
        logging.debug("❌ No movies selected for updating.")
        return jsonify({"messages": ["No movies selected for poster updates."]})

    plex_url = config["plex_url"].rstrip("/")
    plex_token = config["plex_token"]

    # ✅ Ensure Plex URL starts with "http://"
    if plex_url and not plex_url.startswith("http"):
        plex_url = f"http://{plex_url}"

    plex = PlexServer(plex_url, plex_token)

    for movie_id, new_poster_url in selected_movies:
        try:
            debug_log(f"Processing Movie ID: {movie_id}")

            if not new_poster_url.startswith("http"):
                response_messages.append(f"❌ Error: Invalid poster URL: {new_poster_url}")
                logging.error(f"Invalid poster URL: {new_poster_url}")
                continue

            movie = plex.fetchItem(int(movie_id))
            if movie:
                debug_log(f"Found movie: {movie.title} (ID: {movie_id})")
                movie.uploadPoster(url=new_poster_url)
                response_messages.append(f"✅ Successfully updated poster for {movie.title}!")
            else:
                response_messages.append(f"❌ Error: Movie ID {movie_id} not found in Plex.")

        except Exception as e:
            error_msg = f"❌ Error updating {movie_id}: {str(e)}"
            response_messages.append(error_msg)
            logging.error(error_msg)

    return jsonify({"messages": response_messages})

# ✅ Web UI route
@app.route("/")
def index():
    return render_template("index.html")

# ✅ Start the Flask app
if __name__ == "__main__":
    debug_log("Starting Flask server")
    app.run(host="0.0.0.0", port=int(config["web_port"]), debug=config["debug_mode"], threaded=True)

