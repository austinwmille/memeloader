import os
import re
import sys
import time
import random
from dotenv import load_dotenv  # Add this import at the top
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import openai
from openai import OpenAI  # For AI-powered metadata generation
from moviepy import VideoFileClip
import subprocess  # For Whisper transcription
import json

load_dotenv('botsecs.env')

# Load OpenAI API Key from environment variable
OPENAI_API_KEY = os.getenv("gptkey")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API Key is not set. Please set it as an environment variable.")
# Initialize OpenAI client
client = OpenAI(
    api_key=OPENAI_API_KEY
)

# Path to your OAuth 2.0 Client ID JSON file
CLIENT_SECRET_FILE = 'tubesecs.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Set the video folder path at the start of the script
VIDEO_FOLDER_PATH = os.path.abspath(f'./upload')

# Authenticate with YouTube API
def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    return build('youtube', 'v3', credentials=credentials)

HOOK_WORDS = [
    "EPIC", "SHOCKING", "SECRET", "WARNING", "ULTIMATE", "BEHIND-THE-SCENES", 
    "AMAZING", "INCREDIBLE", "UNBELIEVABLE", "INSANE", "CRAZY", "MIND-BLOWING", 
    "LEGENDARY", "WILD", "UNSTOPPABLE", "HILARIOUS", "HEARTWARMING", "TERRIFYING", 
    "INSPIRING", "BEAUTIFUL", "FUNNY", "STRANGE", "MOVING", "UNEXPECTED", 
    "DRAMATIC", "IMPOSSIBLE", "EXTREME", "HARDCORE", "SAVAGE", "ULTIMATE", 
    "GENIUS", "NEXT-LEVEL", "REVOLUTIONARY", "UNSEEN", "RARE", "TOP-SECRET", 
    "EXCLUSIVE", "BEYOND-BELIEF", "CRITICAL", "LIFE-CHANGING", "GAME-CHANGING", 
    "VIRAL", "TRENDING", "HIDDEN", "LIMITED", "RIDICULOUS", "UNFILTERED", 
    "RAW", "UNEDITED", "PROVEN", "BRILLIANT", "CONTROVERSIAL", "OUTRAGEOUS", 
    "STUNNING", "MYSTERIOUS", "FORBIDDEN", "MASSIVE", "HUGE", "BREAKING", 
    "INSIDER", "GROUNDBREAKING", "POWERFUL", "UNIMAGINABLE", "TOP-TIER"
]

COMMON_MISSPELLINGS = {
    "tutorial": ["tutoral", "tuturial", "tutoriol", "tuturials"],
    "gaming": ["gamminng", "gameing", "gaiming", "gamming", "gaminng"],
    "vlog": ["vlogg", "vloq", "vloug", "vllog", "vloog"],
    "review": ["revue", "reeview", "reviw", "revu", "reviue"],
    "challenge": ["chalenge", "chalange", "challange", "challeng", "challege"],
    "minecraft": ["mincraft", "minecaft", "minecraf", "minecrafte", "minecratf"],
    "python": ["pyhton", "pythoon", "pythn", "phyton", "pythoon"],
    "science": ["scinece", "sciense", "scince", "sceince", "sciens"],
    "education": ["educaion", "eduction", "educashun", "edukatoin", "educcation"],
    "fitness": ["fitnes", "fitniss", "fitnees", "fittness", "fitnnes"],
    "sports": ["sprots", "spors", "sportz", "sporst", "spourts"],
    "entertainment": ["entartainment", "entertainmnt", "entertaiment", "entetainment", "entertanment"],
    "music": ["musick", "musci", "musoc", "musik", "mucsic"],
    "comedy": ["commedy", "comedie", "commedy", "komedy", "commdedy"],
    "technology": ["tecnology", "techology", "technolgy", "tecknology", "technologie"],
    "travel": ["traval", "travle", "travele", "trvel", "treval"],
    "animals": ["animels", "animasl", "anmials", "animuls", "anamals"],
    "recipes": ["recipies", "recepes", "recepies", "reciepes", "resipes"],
    "workout": ["workot", "workut", "wrkout", "worcout", "wokout"],
    "basketball": ["baskettball", "basketbal", "baskeball", "basketboll", "basketbal"],
    "skateboarding": ["skatebording", "skatboarding", "sk8boarding", "sk8bordng", "sk8bording"],
    "reaction": ["reacion", "recation", "reacton", "reacshun", "reactionn"],
    "adventure": ["adveture", "advenure", "adventur", "advanture", "advantuer"],
    "streaming": ["streming", "streeming", "streamin", "stremming", "streamng"]
}


def optimize_tags(tags):
    for tag in tags[:3]:
        if tag.lower() in COMMON_MISSPELLINGS:
            tags.extend(COMMON_MISSPELLINGS[tag.lower()])
        else:
            # Better misspelling patterns
            tags.append(f"{tag}ss")  # "hack" → "hackss", "challenge" → "challengess"
            tags.append(f"{tag[:-1]}")  # "coding" → "codin", "gaming" → "gamin"
    return list(dict.fromkeys(tags))[:15]

def sanitize_file_name(file_name):
    """
    Removes emojis, special characters, and trims file names for compatibility.
    """
    # Remove emojis
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # Emoticons
        u"\U0001F300-\U0001F5FF"  # Symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # Transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # Flags (iOS)
        u"\U00002500-\U00002BEF"  # Chinese characters
        u"\U00002702-\U000027B0"  # Dingbats
        u"\U000024C2-\U0001F251"  # Enclosed characters
        "]+",
        flags=re.UNICODE
    )
    file_name = emoji_pattern.sub("", file_name)  # Remove emojis

    # Replace spaces with underscores and remove special characters
    sanitized_name = re.sub(r"[\\/*?\"<>|]", "", file_name).replace(" ", "_")

    # Limit file name length to 100 characters (excluding extension)
    base_name, ext = os.path.splitext(sanitized_name)
    return base_name[:100] + ext

def get_youtube_categories(youtube):
    """Fetch YouTube video categories and return a dict of id to title."""
    try:
        request = youtube.videoCategories().list(
            part="snippet",
            regionCode="US"  # Adjust region if needed
        )
        response = request.execute()
        categories = {}
        for item in response.get('items', []):
            categories[item['id']] = item['snippet']['title']
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return {}

# After fetching categories, add priority keywords
CATEGORY_KEYWORDS = {
    "Howto & Style": [
        "tutorial", "hack", "DIY", "build", "repair", "style", "makeup", 
        "fashion", "design", "tips", "how-to", "guide", "craft", "sewing", 
        "decor", "home improvement", "organization", "skincare", "beauty"
    ],
    "Gaming": [
        "minecraft", "speedrun", "gameplay", "stream", "fps", "rpg", 
        "walkthrough", "multiplayer", "pvp", "strategy", "battle royale", 
        "esports", "console", "playstation", "xbox", "nintendo", "gaming", 
        "video games", "cheats", "mods", "quests", "sandbox"
    ],
    "Education": [
        "python", "coding", "math", "science", "history", "astronomy", 
        "physics", "chemistry", "biology", "tutorial", "school", 
        "learning", "lectures", "programming", "data science", 
        "engineering", "technology", "class", "study", "exam prep", 
        "knowledge", "skills", "books", "educational"
    ],
    "Travel & Events": [
        "travel", "vlog", "adventure", "backpacking", "vacation", 
        "road trip", "exploring", "tourism", "culture", "local", 
        "sightseeing", "nature", "hiking", "beach", "camping", "hotels", 
        "flights", "cruise", "journey", "getaway", "landmarks"
    ],
    "Sports": [
        "workout", "soccer", "basketball", "stunt", "fitness", "training", 
        "exercise", "gym", "bodybuilding", "yoga", "running", "marathon", 
        "football", "tennis", "swimming", "racing", "extreme sports", 
        "baseball", "golf", "surfing", "skateboarding", "cycling", "athlete"
    ],
    "Comedy": [
        "funny", "parody", "skit", "prank", "humor", "laugh", "jokes", 
        "stand-up", "satire", "spoof", "roast", "entertainment", 
        "hilarious", "memes", "fails", "reaction", "comedy", "sarcasm"
    ],
    "Music": [
        "music", "song", "cover", "album", "live", "concert", "band", 
        "performance", "singing", "karaoke", "playlist", "dance", 
        "instrumental", "remix", "DJ", "rap", "hip-hop", "rock", "pop", 
        "EDM", "classical", "country", "jazz", "R&B", "lyrics"
    ],
    "News & Politics": [
        "news", "breaking", "current events", "politics", "debate", 
        "government", "election", "world news", "economy", "protest", 
        "crisis", "analysis", "interview", "speech", "opinion", "law", 
        "policy", "scandal", "activism", "press"
    ],
    "Pets & Animals": [
        "pets", "animals", "cute", "funny animals", "wildlife", "dogs", 
        "cats", "birds", "fish", "reptiles", "horses", "puppies", "kittens", 
        "zoo", "nature", "animal care", "training", "rescue", "habitat", 
        "adoption"
    ],
    "Entertainment": [
        "movies", "tv", "celebrities", "reviews", "trailer", "film", 
        "series", "drama", "reaction", "binge", "entertainment", "actors", 
        "director", "streaming", "Netflix", "HBO", "Disney", "Hollywood", 
        "premiere", "red carpet", "award show"
    ],
    "Technology": [
        "tech", "gadgets", "smartphones", "apps", "software", "AI", 
        "robots", "innovation", "review", "tutorial", "coding", 
        "programming", "devices", "unboxing", "gaming tech", 
        "computers", "laptops", "hardware", "VR", "AR", "5G", "IoT", 
        "cloud", "blockchain"
    ],
    "Food & Drink": [
        "cooking", "recipes", "food", "drink", "baking", "desserts", 
        "grilling", "kitchen", "cuisine", "restaurant", "review", "tasting", 
        "healthy eating", "vegan", "vegetarian", "BBQ", "snacks", "chefs", 
        "cocktails", "smoothies", "wine", "coffee", "beer", "street food"
    ],
    "Health & Wellness": [
        "mental health", "self-care", "therapy", "wellness", "meditation", 
        "stress relief", "yoga", "mindfulness", "health tips", "nutrition", 
        "work-life balance", "exercise", "diet", "healthy living"
    ],
    "Autos & Vehicles": [
        "cars", "motorcycles", "vehicles", "driving", "racing", 
        "car reviews", "road trip", "auto repair", "engines", "trucks", 
        "customization", "tuning", "electric vehicles", "car shows", "SUV"
    ],
    "Kids & Family": [
        "toys", "kids", "family", "parenting", "children", "games", 
        "activities", "playtime", "crafts for kids", "education for kids", 
        "nursery rhymes", "stories", "babies", "play", "fun"
    ],
    "Science & Nature": [
        "experiments", "space", "nature", "biology", "geology", 
        "wildlife", "science facts", "physics", "chemistry", 
        "astrophysics", "natural wonders", "climate", "ecosystem", 
        "universe", "ecology", "environment"
    ]
}

def add_timestamps(description, duration):
    if duration > 60:  # Only for videos >1 minute
        base_timestamps = {
            0: "Intro",
            duration//4: "The Setup",
            duration//2: "Big Moment",
            duration-30: "Finale"
        }
        timestamp_lines = [f"{sec//60}:{sec%60:02d} {text}" for sec, text in base_timestamps.items()]
        return f"{description}\n\n⏱️ TIMESTAMPS:\n" + "\n".join(timestamp_lines)
    return description

def detect_category(title, description, categories):
    for word in title.lower().split() + description.lower().split():
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if word in keywords and cat in categories.values():
                return cat
    return "Entertainment"  # Default

def rename_files_in_folder(folder_path):
    """
    Renames video files in a folder to sanitized names while retaining context.
    """
    seen_names = set()  # Track sanitized names to avoid duplicates
    with open("rename_log.txt", "w", encoding="utf-8") as log_file:
        for i, file_name in enumerate(os.listdir(folder_path)):
            if file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                file_path = os.path.join(folder_path, file_name)
                sanitized_name = sanitize_file_name(file_name)

                # Add a unique index if the name is already used
                base_name, ext = os.path.splitext(sanitized_name)
                new_file_name = sanitized_name
                counter = 1
                while new_file_name in seen_names:
                    new_file_name = f"{base_name}_{counter}{ext}"
                    counter += 1

                # Update seen names and rename file
                seen_names.add(new_file_name)
                new_file_path = os.path.join(folder_path, new_file_name)
                os.rename(file_path, new_file_path)
                log_file.write(f"Renamed {file_name} to {new_file_name}\n")
                print(f"Renamed {file_name} to {new_file_name}")

# Extract metadata from video
def analyze_video(file_path):
    try:
        clip = VideoFileClip(file_path)
        duration = clip.duration
        resolution = f"{clip.w}x{clip.h}"
        clip.close()
        return {"duration": duration, "resolution": resolution}
    except Exception as e:
        print(f"Error analyzing video: {e}")
        return {}

# Transcribe video using Whisper
# Replace transcribe_video() with:
def transcribe_video(file_path):
    try:
        import whisper
        model = whisper.load_model("medium")  # Use 'small' or 'medium' for better accuracy
        result = model.transcribe(file_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing video: {e}")
        return ""

# Generate metadata using AI
def generate_metadata(file_path, categories):
    video_data = analyze_video(file_path)
    transcript = transcribe_video(file_path) or "No transcript available."
    original_file_name = os.path.splitext(os.path.basename(file_path))[0]

    # Create a name-to-ID mapping and list of category names
    category_name_to_id = {v: k for k, v in categories.items()}
    category_names = list(categories.values())

    # Updated prompt to include category selection
    # Updated prompt in generate_metadata()
    prompt = (
        f"Generate YouTube metadata as JSON (title, description, tags, category) for ANY video type. RULES:\n"
        f"1. TITLE:\n"
        f"   - Start with 1-2 CAPS hook words from: {', '.join(HOOK_WORDS)}\n"
        f"   - Add intrigue in parentheses: (Gone Wrong?), (Here’s Why), (3 AM Challenge)\n"
        f"   - Example for 'Gardening_Tips.mp4': 'SECRET Gardening Hacks (You’ve NEVER Seen Before!)'\n"
        f"2. DESCRIPTION:\n"
        f"   - First line: Pose a question or tease drama\n"
        f"   - Include 2-3 emojis (🎥, 🔥, ⚠️)\n"
        f"   - Add CTA: Ask viewers to comment/subscribe\n"
        f"3. TAGS:\n"
        f"   - Mix niche and trending terms\n"
        f"   - Include 2-3 misspelled versions of key terms\n"
        f"---\n"
        f"Filename: {original_file_name}\n"
        f"Duration: {video_data.get('duration', 0)}s\n"
        f"Transcript: {transcript}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in YouTube metadata optimization."},
                {"role": "user", "content": prompt},
            ]
        )
        metadata_content = response.choices[0].message.content.strip()

        # Parse metadata
        metadata = json.loads(metadata_content)
        
        # Add to generate_metadata() after getting AI response:
        metadata["description"] = add_timestamps(metadata.get("description", ""), video_data.get("duration", 0))

        # Validate and map category to ID
        category_name = metadata.get('category')
        if category_name in category_name_to_id:
            metadata['categoryId'] = category_name_to_id[category_name]
        else:
            print(f"Invalid category '{category_name}'. Defaulting to 'Comedy'.")
            metadata['categoryId'] = '23'  # Fallback

        return metadata
    except json.JSONDecodeError:
        print("AI response not in JSON format. Using default metadata.")
        return {"title": "Untitled Video", "description": "", "tags": [], "categoryId": "23"}
    except Exception as e:
        print(f"Error generating metadata: {e}")
        return {"title": "Untitled Video", "description": "", "tags": [], "categoryId": "23"}
# Function to upload a single video
def upload_video(youtube, file_path, metadata):
    request_body = {
        'snippet': {
            'title': metadata.get('title', "Untitled Video"),
            'description': metadata.get('description', "No description provided."),
            'tags': metadata.get('tags', []),
            'categoryId': metadata.get('categoryId', '23'),  # Dynamic category
        },
        'status': {
            'privacyStatus': 'public',  # Options: 'public', 'unlisted', 'private'
            'selfDeclaredMadeForKids': False  # Default to "Not Made for Kids"
        }
    }
    media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading {file_path}: {int(status.progress() * 100)}%")
    print(f"Upload completed: {metadata.get('title', 'Untitled Video')}")
    return response

# Process all videos in a folder
def process_folder(youtube, folder_path):
    rename_files_in_folder(folder_path)
    
    # Define the "done" folder path
    done_folder_path = os.path.abspath('./done')

    # Fetch YouTube categories
    categories = get_youtube_categories(youtube)
    if not categories:
        print("Warning: Using default category 'Comedy' (ID 23).")
        categories = {'23': 'Comedy'}  # Fallback

    # Get all video files in the folder
    video_files = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
    ]

    # Continue until no video files are left
    while video_files:
        # Pick a random video
        file_path = random.choice(video_files)
        video_files.remove(file_path)  # Remove the file from the list to avoid reprocessing

        print(f"Processing video: {file_path}")
        metadata = generate_metadata(file_path, categories)  # Pass categories
        print(f"Generated Metadata: {metadata}")
        
        if metadata.get("title") != "Untitled Video":
            # Upload the video
            upload_video(youtube, file_path, metadata)
            print(f"Uploaded {file_path}. Moving to 'done' folder.")

            # Move the file to the "done" folder
            done_file_path = os.path.join(done_folder_path, os.path.basename(file_path))
            os.rename(file_path, done_file_path)
            print(f"Moved {file_path} to {done_file_path}. Random wait before the next upload.")
            
            # Generate a random sleep time between 2 minutes (120 seconds) and 30 minutes (1800 seconds)
            sleep_time = random.randint(120, 1800)
            print(f"Waiting {sleep_time // 60} minutes and {sleep_time % 60} seconds before the next upload...")
            time.sleep(sleep_time)
        else:
            print(f"Skipping upload for {file_path} due to invalid metadata.")

# Main function
def main():
    youtube = get_authenticated_service()

    if os.path.exists(VIDEO_FOLDER_PATH) and os.path.isdir(VIDEO_FOLDER_PATH):
        process_folder(youtube, VIDEO_FOLDER_PATH)
    else:
        print(f"Folder not found: {VIDEO_FOLDER_PATH}")

if __name__ == '__main__':
    main()
