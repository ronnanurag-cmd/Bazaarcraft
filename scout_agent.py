import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from googleapiclient.discovery import build

print("--- Agent Booting Up (v49.0) ---")

# 1. LOAD REPOSITORY SECRETS
gemini_key = os.getenv("GEMINI_API_KEY")
yt_key = os.getenv("YT_API_KEY")
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

# 2. FIREBASE AUTO-INITIALIZATION
try:
    if not firebase_json:
        raise ValueError("CRITICAL: FIREBASE_SERVICE_ACCOUNT secret is completely empty!")
    
    # Strip any hidden spaces or mobile formatting artifacts
    clean_json = firebase_json.strip()
    cred_dict = json.loads(clean_json)
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Authorization: Connected and Unlocked")
except Exception as e:
    print(f"❌ FIREBASE CRASH: Check your GitHub Secrets. Error: {e}")
    exit(1)

# 3. AI BRAIN CONFIGURATION
try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Status: Online")
except Exception as e:
    print(f"❌ GEMINI AI CRASH: Check your GEMINI_API_KEY. Error: {e}")
    exit(1)

# 4. AUTOMATED SCOUTING ENGINE
def run_scout(city):
    # Standardize the city name to lowercase to match your website's expected filter
    city_id = city.lower().strip()
    print(f"🔍 Scouting YouTube for active 2026 data in: [{city_id}]...")
    
    try:
        youtube = build('youtube', 'v3', developerKey=yt_key)
        search_query = f"{city_id} market tour 2026 prices"
        request = youtube.search().list(q=search_query, part="snippet", maxResults=1)
        res = request.execute()
        
        if not res.get('items'):
            print(f"⚠️ No new videos found matching criteria for {city_id}.")
            return
            
        vid = res['items'][0]
        v_id = vid['id']['videoId']
        v_title = vid['snippet']['title']
        print(f"📍 Video Located: '{v_title}' (ID: {v_id})")
        
        # Pass payload to Gemini for structural extraction
        prompt = f"Analyze video {v_id}. List 3 home decor or local lifestyle items with reasonable market prices in INR. Return ONLY raw JSON formatting matching this scheme: {{\"items\":[{{\"n\":\"Item Name\",\"p\":500}}]}}"
        ai_res = model.generate_content(prompt)
        
        # Clean any raw markdown blocks returning from the LLM engine
        clean_ai = ai_res.text.replace('```json', '').replace('```', '').strip()
        intel = json.loads(clean_ai)
        
        # TARGET DIRECT DOCUMENT CODENAME (Fixes the Auto-ID loop issue)
        doc_ref = db.collection('masterDB').document(city_id)
        
        market_payload = {
            "id": v_id,
            "m": v_title[:30],
            "items": intel['items'],
            "nav": "Main Market Entrance",
            "lat": "19.0", "lng": "72.8"
        }
        
        # .set() with merge=True will safely force-create the document if missing!
        doc_ref.set({
            "status": "active",
            "markets": firestore.ArrayUnion([market_payload])
        }, merge=True)
        
        print(f"✅ Data fully synced and mapped into Firestore under: masterDB -> {city_id}")
        
    except Exception as e:
        print(f"⚠️ Dynamic processing failed for city [{city_id}]: {e}")

# --- 5. RUN ENGINE FOR SELECTED SITES ---
target_cities = ["delhi", "mumbai", "lonavala"]

for current_city in target_cities:
    run_scout(current_city)
    print("-" * 30)

print("--- Scout Routine Completed Successfully ---")
