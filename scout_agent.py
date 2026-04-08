import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from googleapiclient.discovery import build

print("--- Agent Booting Up ---")

# 1. FETCH SECRETS
gemini_key = os.getenv("GEMINI_API_KEY")
yt_key = os.getenv("YT_API_KEY")
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

# 2. FIREBASE CONNECTION (The most likely failure point)
try:
    if not firebase_json:
        raise ValueError("Firebase Secret is empty!")
    
    # Cleaning the JSON string from mobile formatting issues
    clean_json = firebase_json.strip()
    cred_dict = json.loads(clean_json)
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connected")
except Exception as e:
    print(f"❌ FIREBASE ERROR: {e}")
    exit(1)

# 3. AI CONFIG
try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ AI Ready")
except Exception as e:
    print(f"❌ AI ERROR: {e}")
    exit(1)

# 4. SCOUTING ENGINE
def run_scout(city):
    try:
        print(f"🔍 Scouting {city}...")
        youtube = build('youtube', 'v3', developerKey=yt_key)
        request = youtube.search().list(q=f"{city} market tour 2026", part="snippet", maxResults=1)
        res = request.execute()
        
        if res['items']:
            vid = res['items'][0]
            v_id = vid['id']['videoId']
            
            # AI Watch
            prompt = f"Analyze video {v_id}. List 3 items with prices in INR. Return ONLY JSON: {{\"items\":[{{\"n\":\"name\",\"p\":100}}]}}"
            ai_res = model.generate_content(prompt)
            clean_ai = ai_res.text.replace('```json', '').replace('```', '').strip()
            intel = json.loads(clean_ai)
            
            # Save
            doc_ref = db.collection('masterDB').document(city)
            doc_ref.set({"markets": firestore.ArrayUnion([{
                "id": v_id,
                "m": vid['snippet']['title'][:30],
                "items": intel['items'],
                "nav": "Market Entrance",
                "lat": "19.0", "lng": "72.8"
            }])}, merge=True)
            print(f"✅ {city} Updated")
    except Exception as e:
        print(f"⚠️ Error scouting {city}: {e}")

# Run for your main cities
for c in ["delhi", "mumbai", "lonavala"]:
    run_scout(c)

print("--- Scout Complete ---")
