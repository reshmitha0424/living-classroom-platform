# ---------- SINGLE API CALL ----------------
# This block makes ONE API request, prints number of detections, and prints the latest detection details. Useful for quick testing / debugging.


# import requests #allows Python to make HTTP API calls.

# STATION_ID = 14218 #BirdWeather station ID you want to pull data from.
# URL = f"https://app.birdweather.com/api/v1/stations/{STATION_ID}/detections" 

# r = requests.get(URL, timeout=20)  #Sends an HTTP GET request to the API.
# timeout=20 means: wait max 20 seconds before failing.

# r.raise_for_status() #If the API returns an error (like 404 or 500), this line throws an exception.
# data = r.json() #Converts the API response (JSON format) into a Python dictionary.

# detections = data.get("detections", []) #Extracts the "detections" list from the JSON. If the key doesn’t exist, returns an empty list instead of crashing.
# print("detections returned:", len(detections)) #Prints how many detections were returned by the API call.

# if detections: #if not empty
#     newest = detections[0] #The API returns detections sorted newest-first. index 0 = most recent bird detection.
#     species = (newest.get("species") or {}).get("commonName") #Gets the bird’s common name (e.g., "American Goldfinch"). (or {}) prevents crashing if "species" is missing.
#     ts = newest.get("timestamp") #Timestamp of bird detection
#     conf = newest.get("confidence") #confidence score
#     print("latest:", species, "|", ts, "| confidence:", conf) 





import time #time module - so we can pause execution using sleep().
import requests #to make HTTP API calls.

STATION_ID = 14218 
URL = f"https://app.birdweather.com/api/v1/stations/{STATION_ID}/detections"

while True: #infinite loop.
    try: #to safely handle network/API errors.
        r = requests.get(URL, timeout=20)  #Sends an HTTP GET request to the API.
        # timeout=20 means: wait max 20 seconds before failing.
        r.raise_for_status() #If the API returns an error (like 404 or 500), this line throws an exception.
        data = r.json() #Converts the API response (JSON format) into a Python dictionary.

        detections = data.get("detections", [])
        if detections:
            newest = detections[0]
            species = (newest.get("species") or {}).get("commonName")
            ts = newest.get("timestamp")
            conf = newest.get("confidence")
            print(f"{ts} | {species} | conf={conf:.3f}")
        else:
            print("No detections returned.")

    except Exception as e: 
        print("API error:", e) #Catches any network or parsing errors and prints them instead of crashing.

    time.sleep(10) #Waits 10 seconds before making the next API call.