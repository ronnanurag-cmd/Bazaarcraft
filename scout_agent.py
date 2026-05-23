import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from google.genai import types
from googleapiclient.discovery import build

print("--- Agent Booting Up (v55.0 - Multi-Video & PAN-India Fleet) ---")

gemini_key = os.getenv("GEMINI_API_KEY")
yt_key = os.getenv("YT_API_KEY")
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

try:
    if not firebase_json:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT secret is empty!")
    clean_json = firebase_json.strip()
    cred_dict = json.loads(clean_json)
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Authorization: Connected")
except Exception as e:
    print(f"❌ FIREBASE CRASH: {e}")
    exit(1)

try:
    client = genai.Client(api_key=gemini_key)
    print("✅ Gemini AI Status: Online")
except Exception as e:
    print(f"❌ GEMINI AI CRASH: {e}")
    exit(1)

def run_scout(city):
    city_id = city.lower().strip()
    print(f"🔍 Scouting YouTube for active data fleet in: [{city_id}]...")
    try:
        youtube = build('youtube', 'v3', developerKey=yt_key)
        search_query = f"{city_id} market tour prices"
        
        # UPGRADED: Expanded maxResults to 5 to harvest a massive initial batch
        request = youtube.search().list(q=search_query, part="snippet", maxResults=5, type="video")
        res = request.execute()
        
        if not res.get('items'):
            print(f"⚠️ No videos located for {city_id}.")
            return
            
        print(f"📡 Found {len(res['items'])} matching video pipelines. Processing batch...")
        
        # Loop through each individual video found in the batch
        for item in res['items']:
            try:
                v_id = item['id']['videoId']
                v_title = item['snippet']['title']
                
                print(f"🎬 Processing Video: '{v_title[:40]}...' (ID: {v_id})")
                
                prompt = f"Analyze video title/context {v_title} with ID {v_id}. List 3 realistic local consumer items with market prices in INR. Return ONLY raw JSON formatting matching this exact schema: {{\"items\":[{{\"n\":\"Item Name\",\"p\":500}}]}}"
                
                ai_res = client.models.generate_content(
                    model='models/gemini-1.5-flash',
                    contents=prompt,
                )
                
                clean_ai = ai_res.text.replace('```json', '').replace('```', '').strip()
                intel = json.loads(clean_ai)
                
                # Structure the individual market payload
                market_payload = {
                    "id": v_id,
                    "m": v_title[:45],
                    "items": intel['items'],
                    "nav": "Main Market Sector",
                    "lat": "20.0", "lng": "77.0"
                }
                
                # TARGET DIRECT DOCUMENT CODENAME
                doc_ref = db.collection('masterDB').document(city_id)
                
                # ArrayUnion ensures it appends the new video seamlessly. 
                # If the video already exists, it skips it safely without deleting anything!
                doc_ref.set({
                    "status": "active",
                    "markets": firestore.ArrayUnion([market_payload])
                }, merge=True)
                
                print(f"   ✅ Video Sync Complete -> [masterDB -> {city_id}]")
                
            except Exception as video_err:
                print(f"   ⚠️ Skipping specific video error: {video_err}")
                continue
                
    except Exception as e:
        print(f"❌ Processing completely stalled for city [{city_id}]: {e}")

# --- PAN-INDIA TARGET HUB MATRIX ---
target_cities = [
    "delhi", "mumbai", "lonavala", "kolkata", "bangalore", 
    "chennai", "hyderabad", "pune", "ahmedabad", "jaipur", 
    "lucknow", "surat", "patna", "indore", "chandigarh"
]

for current_city in target_cities:
    run_scout(current_city)
    print("=" * 40)

print("--- PAN-India Scout Fleet Routine Completed ---")
