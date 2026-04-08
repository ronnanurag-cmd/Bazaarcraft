import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from googleapiclient.discovery import build

# --- 1. VERIFY SECRETS (PREVENTS EXIT CODE 1) ---
print("--- Starting BazaarCraft Scout Agent ---")

try:
    gemini_key = os.environ["GEMINI_API_KEY"]
    yt_key = os.environ["YT_API_KEY"]
    firebase_json = os.environ["FIREBASE_SERVICE_ACCOUNT"]
    print("✅ All Secrets detected.")
except KeyError as e:
    print(f"❌ FAILED: Missing Secret in GitHub: {e}")
    exit(1)

# --- 2. INITIALIZE FIREBASE ---
try:
    # This handles common mobile-copy-paste issues
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connection established.")
except Exception as e:
    print(f"❌ FAILED: Firebase Auth Error. Check your JSON formatting. Error: {e}")
    exit(1)

# --- 3. INITIALIZE GEMINI BRAIN ---
try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Brain online.")
except Exception as e:
    print(f"❌ FAILED: Gemini Config error: {e}")
    exit(1)

# --- 4. THE SCOUTING LOGIC ---
def scout_market_videos(city):
    print(f"🔍 Scouting YouTube for {city} market tours...")
    try:
        youtube = build('youtube', 'v3', developerKey=yt_key)
        # 2026 Season Search Query
        query = f"{city} market shopping tour 2026 prices"
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=1,
            relevanceLanguage="en"
        )
        response = request.execute()
        if response['items']:
            video = response['items'][0]
            print(f"📍 Found Video: {video['snippet']['title']}")
            return video
        return None
    except Exception as e:
        print(f"⚠️ YouTube Search failed for {city}: {e}")
        return None

def analyze_video_intel(video_id, city_name):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"🧠 AI is watching: {video_id}...")
    
    prompt = f"""
    Analyze this 2026 market video for {city_name}: {video_url}
    Extract 4 primary home decor/lifestyle products shown.
    Estimate the 2026 price in INR (₹).
    Provide a 1-line 'Gali-Guide' navigation tip.
    
    RETURN ONLY A RAW JSON OBJECT LIKE THIS:
    {{
      "items": [
        {{"n": "Product Name", "p": 500}},
        {{"n": "Product Name", "p": 1200}}
      ],
      "nav": "Near the old clock tower entrance"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Remove any markdown code blocks if AI adds them
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"⚠️ AI Analysis failed for {video_id}: {e}")
        return None

def update_production_db(city, video_data, ai_intel):
    try:
        # Pushes directly to your BazaarCraft masterDB collection
        doc_ref = db.collection('masterDB').document(city)
        
        new_entry = {
            "id": video_data['id']['videoId'],
            "m": video_data['snippet']['title'][:30],
            "items": ai_intel['items'],
            "nav": ai_intel['nav'],
            "lat": "28.5", "lng": "77.2" # Base coords
        }
        
        # Use ArrayUnion to add to the existing market list without overwriting
        doc_ref.set({
            "markets": firestore.ArrayUnion([new_entry])
        }, merge=True)
        print(f"✅ Database updated for {city}!")
    except Exception as e:
        print(f"⚠️ Database write failed for {city}: {e}")

# --- 5. MAIN EXECUTION LOOP ---
# Adding Lonavala & your core cities
active_cities = ["delhi", "mumbai", "lonavala", "goa", "jaipur", "rishikesh"]

for city in active_cities:
    video = scout_market_videos(city)
    if video:
        intel = analyze_video_intel(video['id']['videoId'], city)
        if intel:
            update_production_db(city, video, intel)

print("--- Scout Run Complete ---")
