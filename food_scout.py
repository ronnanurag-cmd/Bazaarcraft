import os
import json
import time  # ADDED FOR RATE LIMITING
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from google.genai import types
from googleapiclient.discovery import build

print("--- Foodcraft Agent Booting Up (v1.1 - Rate Limited Culinary Fleet) ---")

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

def run_food_scout(city):
    city_id = city.lower().strip()
    print(f"🍔 Scouting Foodcraft highlights for: [{city_id}]...")
    try:
        youtube = build('youtube', 'v3', developerKey=yt_key)
        search_query = f"{city_id} local street food tour specialties prices"
        
        request = youtube.search().list(q=search_query, part="snippet", maxResults=3, type="video")
        res = request.execute()
        
        if not res.get('items'):
            print(f"⚠️ No food videos located for {city_id}.")
            return
            
        print(f"📡 Found {len(res['items'])} culinary videos. Filtering records...")
        seen_video_ids = set()
        
        for item in res['items']:
            try:
                v_id = item['id']['videoId']
                v_title = item['snippet']['title']
                
                if v_id in seen_video_ids:
                    continue
                seen_video_ids.add(v_id)
                
                print(f"🍲 Parsing Food Video: '{v_title[:40]}...'")
                
                prompt = (
                    f"Analyze the local food video titled '{v_title}'. "
                    f"Identify 3 famous local street food items or cheap regional specialties "
                    f"(like phuchka, vada pav, puffs, chats, local sweets) and extract their average retail street prices in INR. "
                    f"Return ONLY raw JSON matching this format: {{\"items\":[{{\"n\":\"Food Name (Per Plate/Piece)\",\"p\":40}}]}}"
                )
                
                ai_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                clean_ai = ai_res.text.replace('```json', '').replace('```', '').strip()
                intel = json.loads(clean_ai)
                
                food_payload = {
                    "id": v_id,
                    "m": v_title[:45],
                    "items": intel['items'],
                    "nav": "Famous Local Food Junction",
                    "lat": "20.0", "lng": "77.0"
                }
                
                doc_ref = db.collection('foodDB').document(city_id)
                doc_ref.set({
                    "status": "active",
                    "specialties": firestore.ArrayUnion([food_payload])
                }, merge=True)
                
                print(f"   ✅ Foodcraft Sync Complete -> [foodDB -> {city_id}]")
                
                # FIXED: Sleep 12 seconds between items to stay safely under 5 requests per minute
                print("   ⏳ Pacing food API footprint... sleeping 12s...")
                time.sleep(12)
                
            except Exception as video_err:
                print(f"   ⚠️ Skipping food video breakdown: {video_err}")
                continue
                
    except Exception as e:
        print(f"❌ Food scout stalled for city [{city_id}]: {e}")

# PAN-INDIA TARGET CULINARY MATRICES
target_cities = [
    "delhi", "mumbai", "kolkata", "bangalore", 
    "chennai", "hyderabad", "pune", "jaipur"
]

for current_city in target_cities:
    run_food_scout(current_city)
    print("=" * 40)

print("--- PAN-India Foodcraft Run Completed ---")
