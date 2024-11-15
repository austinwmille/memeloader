import yt_dlp

LOG_FILE = 'downloaded_urls.txt'

def load_downloaded_urls():
    """Load already downloaded URLs from the log file."""
    try:
        with open(LOG_FILE, 'r') as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def save_downloaded_url(url):
    """Save a newly downloaded URL to the log file."""
    with open(LOG_FILE, 'a') as file:
        file.write(url + '\n')

def download_youtube_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio',
        'merge_output_format': 'mp4',
        'outtmpl': '%(title)s.%(ext)s',  # Save as video title
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# Load the set of already downloaded URLs
downloaded_urls = load_downloaded_urls()

# Example usage with multiple URLs
video_urls = [
    "https://twitter.com/i/status/",  # Replace with your URLs
    
]

for url in video_urls:
    if url not in downloaded_urls:
        download_youtube_video(url)
        save_downloaded_url(url)  # Log the URL after downloading
        print(f"Downloaded and logged: {url}")
    else:
        print(f"Already downloaded: {url}")
