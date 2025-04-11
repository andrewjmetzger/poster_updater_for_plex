# Plex Poster Updater

**Plex Poster Updater** is a lightweight tool designed to automatically update your Plex media posters. Fed up with manually changing bad or outdated posters, this project leverages both the Plex API and The Movie Database (TMDB) API to fetch crisp, correct artwork and apply it to your Plex libraries... all with a few simple clicks.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

## Features

- **Automated Poster Updates:** Retrieve and apply high-quality posters with ease.
- **Search Options:** Choose between text-based search queries or time-based filters (e.g., movies added in the last week) to narrow your selection.
- **Easy Configuration:** Simply input your Plex token and TMDB API keys, then point the updater to your Plex server URL.
- **Docker & Unraid Ready:** Designed for Docker-based setups, and also available via the Unraid Community Applications plugin.
  
## Installation

### Prerequisites

- A running Plex Media Server
- Valid Plex token and TMDB API key
- Docker or an Unraid environment with the Community Applications plugin installed

### Using Unraid (Community Applications)

1. Open the Community Applications plugin in your Unraid dashboard.
2. Search for **Plex Poster Updater**.
3. Click **Install** and follow the on-screen instructions.

### Using Docker

1. Pull the project image from Docker Hub:

   ```bash
   docker pull vwdewaal/plex_poster_updater:latest
   ```

2. Run the container:

   ```bash
   docker run -d \
     --name=plexposterupdater \
     -p 5000:5000 \
     -e PLEX_API_KEY=your_plex_api_key \
     -e TMDB_API_KEY=your_tmdb_api_key \
     vwdewaal/plex_poster_updater:latest
   ```

3. Replace `your_plex_api_key` and `your_tmdb_api_key` with your secret keys to enable communication with Plex and TMDB.

## Configuration

After installation, configuration is straightforward:

1. **Access the Interface:**  
   Open your browser and navigate to `http://<YOUR_SERVER_IP>:5000`.

2. **Enter API Keys:**  
   Input your [X-Plex-Token] and TMDB API key. These keys allow the updater to access your Plex server data and fetch the correct movie posters from TMDB.

3. **Set Plex Server Details:**  
   Provide your Plex Media Server URL (for example, `http://192.168.1.50:32400` and X-Plex-Token).

4. **Select Your Library:**  
   Specify the name of the movie library you wish to update. Your Plex library might be labeled as `Movies`, `Films`, or another custom name.

5. **Choose a Search Method:**  
   - **Text Search:** Enter part of a movie’s title (e.g., entering "day" might find "Glory Days", "Groundhog Day", "Independence Day", etc.).
   - **Time-based Filter:** Filter by the date the movies were added (last week, last two weeks, etc.).  
   
6. **Update Posters:**  
   Check the boxes next to the movies you want to update and hit **Apply Changes**. The tool will fetch the new posters and update your Plex library accordingly.

## Usage

- **Interface:**  
  The application is browser-based, so you can access it from any device on your network.

- **Progress Monitoring:**  
  Watch a responsive interface and progress indicators that let you know when poster updates are completed.

- **Dynamic Search:**  
  Whether via text queries or time filters, you can quickly narrow down the movies that need fresh posters.

## Troubleshooting

If you run into issues:

- **API Keys:**
  - Find your Plex token by following the [official steps from Plex support][X-Plex-Token].
  - Find your TMDB API Key on [your account settings page][TMDB API].
  - Verify that both your Plex token and your TMDB API key have been entered correctly.
  
- **Connectivity:**
  - Make sure your Plex server is reachable ath the address specified.
  
- **Logs:**
  - Consult the Docker or system logs for error messages; they often contain useful debugging information.
  

## Support

If you have any questions, issues, or ideas for improvements, check out the [Unraid Support Thread] on the Unraid forums, or open an issue in this repository.

[X-Plex-Token]: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
[TMDB API]: https://www.themoviedb.org/settings/api
[Unraid Support Thread]: https://forums.Unraid.net/topic/187534-plex-poster-updater-support-thread/
