import os
import json
import google.generativeai as genai
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize Firebase & Gemini
# Use GitHub Secrets to keep these safe
cred_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
cred = credentials.Certificate(cred_json)
firebase_admin.initialize_app(cred)
db = firestore.client()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

def get_latest_market_video(city):
    youtube = build('youtube', 'v3', developerKey=os.environ["YT_API_KEY"])
    query = f"{city} market shopping tour 2026 price list"
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=1)
    return request.execute()['items'][0]

def analyze_with_gemini(video_id):
    # The agent "watches" the video metadata and frames
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    prompt = f"""
    Analyze this market tour video: {video_url}.
    1. Identify 4 key home decor products shown.
    2. Extract the price mentioned or estimate based on 2026 market rates.
    3. Write a 1-line navigation tip for this specific stall.
    Return ONLY valid JSON: {{"items": [{{"n": "Item", "p": 100}}], "nav": "Guide"}}
    """
    response = model.generate_content(prompt)
    return json.loads(response.text)

def update_database(city, video_data, ai_intel):
    # This pushes data DIRECTLY to your live index.html feed
    city_ref = db.collection('masterDB').document(city)
    new_entry = {
        "id": video_data['id']['videoId'],
        "m": video_data['snippet']['title'][:25],
        "items": ai_intel['items'],
        "nav": ai_intel['nav'],
        "lat": "28.5", "lng": "77.2" # Placeholder for Geocoding
    }
    # Update Firestore: the index.html will pick this up on next refresh
    city_ref.set({"markets": firestore.ArrayUnion([new_entry])}, merge=True)

# Main Loop
cities = ["delhi", "mumbai", "lonavala", "goa", "jaipur"]
for city in cities:
    video = get_latest_market_video(city)
    intel = analyze_with_gemini(video['id']['videoId'])
    update_database(city, video, intel)


Add scout agent brain