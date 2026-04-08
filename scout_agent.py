import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from googleapiclient.discovery import build

# --- 1. SYSTEM INITIALIZATION ---
print("--- Starting BazaarCraft Scout Agent ---")

try:
    gemini_key = os.environ["GEMINI_API_KEY"]
    yt_key = os.environ["YT_API_KEY"]
    firebase_json = os.environ["FIREBASE_SERVICE_ACCOUNT"]
    print("✅ Secrets Detected.")
except KeyError as e:
    print(f"❌ FAILED: Missing Secret: {e}")
    exit(1)

try:
    # Parsing the Firebase JSON
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connected.")
except Exception as e:
    print(f"❌ FAILED: Firebase Initialization Error: {e}")
    exit(1)

try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ AI Brain Ready.")
except Exception as e:
    print(f"❌ FAILED: AI Config Error: {e}")
    exit(1)

# --- 2. CORE FUNCTIONS ---

def scout_youtube(city):
    print(f"🔍 Searching YouTube for {city}...")
    try:
        youtube = build('youtube', 'v3', developerKey=yt_key)
        query = f"{city} market shopping tour 2026 prices"
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=1
        )
        response = request.execute()
        if response['items']:
            return response['items'][0]
        return None
    except Exception as e:
        print(f"⚠️ YouTube Error: {e}")
        return None

def analyze_video(video_id, city):
    print(f"🧠 AI Analyzing: {video_id}")
    url = f"https://www.youtube.com/watch?v={video_id}"
    prompt = f"Analyze this {city} market video: {url}. Extract 4 products with prices in INR and 1 nav tip. Return ONLY raw JSON: {{\"items\": [{{ \"n\": \"item\", \"p\": 100 }}], \"nav\": \"tip\"}}"
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return None

def save_to_firebase(city, video, intel):
    try:
        doc_ref = db.collection('masterDB').document(city)
        new_market = {
            "id": video['id']['videoId'],
            "m": video['snippet']['title'][:30],
            "items": intel['items'],
            "nav": intel['nav'],
            "lat": "19.0", "lng": "72.8" # Default location
        }
        doc_ref.set({"markets": firestore.ArrayUnion([new_market])}, merge=True)
        print(f"✅ Saved {city} data.")
    except Exception as e:
        print(f"⚠️ Firebase Save Error: {e}")

# --- 3. EXECUTION ---

cities_to_scout = ["delhi", "mumbai", "lonavala", "jaipur", "goa"]

for city_name in cities_to_scout:
    vid = scout_youtube(city_name)
    if vid:
        data = analyze_video(vid['id']['videoId'], city_name)
        if data:
            save_to_firebase(city_name, vid, data)

print("--- Scout Run Complete ---")
