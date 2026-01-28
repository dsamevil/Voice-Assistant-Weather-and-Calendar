import requests
import time

# --- CONFIGURATION ---
TEAM_ID = "team_ASUS_PRIVATOOOO444SSSO"

WEATHER_URL = "https://api.responsible-nlp.net/weather.php"
CALENDAR_URL = "https://api.responsible-nlp.net/calendar.php"

# --- WEATHER (UNCHANGED) ---
def get_weather_forecast(city):
    try:
        response = requests.post(WEATHER_URL, data={"place": city})
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


# ---------------- CALENDAR FIXES START HERE ---------------- #

def get_appointments():
    """
    Fetch all appointments with retry logic
    """
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(
                CALENDAR_URL,
                params={"calenderid": TEAM_ID},
                headers={"Cache-Control": "no-cache"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                return []
            
            # If first attempt fails, wait and retry
            if attempt < max_retries - 1:
                time.sleep(0.5)
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                print(f"Error fetching appointments: {e}")
                
    return []


def create_appointment(title, description, start_time, end_time, location):
    """
    Create appointment with verification
    """
    try:
        payload = {
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location
        }
        r = requests.post(
            CALENDAR_URL,
            params={"calenderid": TEAM_ID},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=5
        )
        
        if r.status_code == 200:
            # Wait for sync
            time.sleep(1.0)
            # Verify creation
            events = get_appointments()
            for e in events:
                if e.get('title') == title:
                    return True
        
        return False
    except Exception as e:
        print(f"Error creating appointment: {e}")
        return False


def delete_appointment(title_to_delete):
    """
    Delete appointment by finding its ID first, then using DELETE request
    """
    try:
        events = get_appointments()
        
        # Find the appointment ID
        target_id = None
        for event in events:
            server_title = event.get("title", "")
            # Try exact match first
            if server_title.lower() == title_to_delete.lower():
                target_id = event.get("id")
                break
        
        # If no exact match, try partial match
        if not target_id:
            for event in events:
                server_title = event.get("title", "")
                if title_to_delete.lower() in server_title.lower():
                    target_id = event.get("id")
                    break
        
        if not target_id:
            print(f"Could not find appointment: {title_to_delete}")
            return False
        
        # Delete using ID with DELETE request
        r = requests.delete(
            CALENDAR_URL,
            params={
                "calenderid": TEAM_ID,
                "id": target_id
            },
            timeout=5
        )
        
        if r.status_code == 200:
            time.sleep(1.0)  # Wait for server sync
            return True
        
        return False
        
    except Exception as e:
        print(f"Error deleting appointment: {e}")
        return False


def delete_all_appointments():
    """
    Delete all appointments using DELETE request with ID
    """
    total_deleted = 0
    max_passes = 10
    
    for pass_num in range(max_passes):
        events = get_appointments()
        
        if not events:
            print(f"Pass {pass_num + 1}: No more events found")
            break
        
        print(f"Pass {pass_num + 1}: Found {len(events)} appointments")
        deleted_this_pass = 0
        
        for event in events:
            event_id = event.get("id")
            title = event.get("title", "Unknown")
            
            if event_id:
                try:
                    r = requests.delete(
                        CALENDAR_URL,
                        params={
                            "calenderid": TEAM_ID,
                            "id": event_id
                        },
                        timeout=5
                    )
                    if r.status_code == 200:
                        deleted_this_pass += 1
                        print(f"  Deleted: {title} (ID: {event_id})")
                except Exception as e:
                    print(f"  Failed to delete {title}: {e}")
        
        total_deleted += deleted_this_pass
        print(f"  Deleted {deleted_this_pass} in this pass")
        
        if deleted_this_pass == 0:
            print("No deletions in this pass, stopping")
            break
            
        # Wait for server sync between passes
        time.sleep(2.0)
    
    # Final verification
    time.sleep(1.0)
    remaining = get_appointments()
    print(f"Final check: {len(remaining)} appointments remaining")
    
    return total_deleted


def modify_appointment(old_title, new_location=None, new_title=None, new_date=None, new_end_date=None):
    """
    Modify appointment by deleting and recreating with new values
    """
    try:
        events = get_appointments()
        target_event = None
        
        # Find the appointment (exact or partial match)
        for event in events:
            server_title = event.get("title", "")
            if old_title.lower() == server_title.lower() or old_title.lower() in server_title.lower():
                target_event = event
                break
        
        if not target_event:
            print(f"Could not find appointment: {old_title}")
            return False
        
        # Get the ID for deletion
        event_id = target_event.get("id")
        
        if not event_id:
            print("Appointment has no ID")
            return False
        
        # Delete old appointment using ID
        try:
            r = requests.delete(
                CALENDAR_URL,
                params={
                    "calenderid": TEAM_ID,
                    "id": event_id
                },
                timeout=5
            )
            
            if r.status_code != 200:
                print("Failed to delete old appointment")
                return False
                
        except Exception as e:
            print(f"Error deleting: {e}")
            return False
        
        # Wait for deletion to sync
        time.sleep(1.5)
        
        # Create new appointment with updated values
        success = create_appointment(
            new_title if new_title else target_event.get("title"),
            target_event.get("description", ""),
            new_date if new_date else target_event.get("start_time"),
            new_end_date if new_end_date else target_event.get("end_time"),
            new_location if new_location else target_event.get("location")
        )
        
        return success
        
    except Exception as e:
        print(f"Error modifying appointment: {e}")
        return False