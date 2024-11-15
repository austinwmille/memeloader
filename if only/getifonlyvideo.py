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

def download_video(url):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': '%(uploader)s/%(upload_date)s-%(id)s.%(ext)s',  # Avoids special characters by using uploader, date, and id
        'sanitize_filename': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            print(f"Skipping video due to error: {e}")


# Load the set of already downloaded URLs
downloaded_urls = load_downloaded_urls()

# Example usage with multiple URLs
video_urls = [
    "video url goes here to download",
    "another url can go here, and so on",
]

for url in video_urls:
    if url not in downloaded_urls:
        download_video(url)
        save_downloaded_url(url)  # Log the URL after downloading
        print(f"Downloaded and logged: {url}")
    else:
        print(f"Already downloaded: {url}")
