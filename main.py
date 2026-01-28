from speech_module import record_audio, transcribe_audio, speak_text as _speak_text
from api_client import get_weather_forecast, get_appointments, create_appointment, delete_appointment, modify_appointment, delete_all_appointments
import re
import datetime
import time

# Wrap speak_text to log responses
def speak_text(text):
    _speak_text(text)
    log_response(text)

# --- GLOBAL CONTEXT ---
last_location = None 
last_day_index = 0
last_created_title = None
conversation_history = []  # NEW: Store full conversation 

# --- MAPPINGS & TRIGGERS ---
CONDITION_MAPPING = {
    "thunder": "thunderstorm", "storm": "thunderstorm", "lightning": "thunderstorm",
    "raining": "rain", "rainy": "rain", "drizzle": "shower rain",
    "snowing": "snow", "snowy": "snow", "sunny": "clear sky",
    "clear": "clear sky", "cloudy": "scattered clouds", "fog": "mist", "misty": "mist"
}
API_CONDITIONS = ["clear sky", "few clouds", "scattered clouds", "broken clouds", "shower rain", "rain", "thunderstorm", "snow", "mist"]

BASE_TRIGGERS = ["weather", "wether", "rain", "forecast", "temperature", "hot", "cold", "tomorrow", "today", "next", "yesterday", "about"]
CONDITION_TRIGGERS = API_CONDITIONS + list(CONDITION_MAPPING.keys())

# --- HELPER FUNCTIONS ---
def text_to_int(text):
    mapping = {
        "one": "1", "two": "2", "three": "3", "four": "4", 
        "five": "5", "six": "6", "seven": "7", "twelfth": "12",
        "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
        "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
        "eleventh": "11", "twelfth": "12", "thirteenth": "13", "fourteenth": "14",
        "fifteenth": "15", "twentieth": "20", "thirtieth": "30"
    }
    for word, digit in mapping.items():
        text = text.replace(f" {word} ", f" {digit} ")
        if text.startswith(word + " "): text = text.replace(word + " ", digit + " ", 1)
        if text.endswith(" " + word): text = text.replace(" " + word, " " + digit, 1)
    return text

def parse_appointment_details(text):
    """
    Advanced Parser: Handles "at [Loc] on [Date]" AND "[Date] at [Loc]"
    """
    original_text = text
    text = text.lower()
    text = text_to_int(text)
    
    today = datetime.date.today()
    
    # 1. Identify Date Logic (Month, Weekday, Relative)
    months = ["january", "february", "march", "april", "may", "june", 
              "july", "august", "september", "october", "november", "december"]
    relative_dates = ["tomorrow", "today", "next"]
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    month_num = today.month
    day_num = today.day + 1
    year = today.year
    
    # Check for specific date triggers in the whole text
    has_date_keywords = False
    
    # Weekdays
    for i, day_name in enumerate(weekdays):
        if day_name in text:
            has_date_keywords = True
            days_ahead = i - today.weekday()
            if days_ahead <= 0: days_ahead += 7
            if "next " + day_name in text: days_ahead += 7 # Optional logic for "next monday"
            target_date = today + datetime.timedelta(days=days_ahead)
            month_num, day_num, year = target_date.month, target_date.day, target_date.year
            break # Assume one date per command

    # Months (Specific Date)
    if not has_date_keywords:
        for m_val, m_name in enumerate(months, 1):
            if m_name in text:
                has_date_keywords = True
                month_num = m_val
                # Look for day number before "of [Month]" or just before [Month]
                # Regex to find "15th" or "15" near the month
                # We search around the month index
                idx = text.find(m_name)
                pre_text = text[:idx]
                day_match = re.search(r'(\d+)(st|nd|rd|th)?(\s+of)?\s*$', pre_text)
                if day_match:
                    day_num = int(day_match.group(1))
                else:
                    # Look after?
                    post_text = text[idx+len(m_name):]
                    day_match = re.search(r'^\s*(\d+)', post_text)
                    if day_match: day_num = int(day_match.group(1))
                
                if month_num < today.month: year += 1
                break

    # Relative
    if not has_date_keywords:
        for rel in relative_dates:
            if rel in text:
                has_date_keywords = True
                if rel == "tomorrow": 
                    target = today + datetime.timedelta(days=1)
                    month_num, day_num, year = target.month, target.day, target.year
                elif rel == "today": 
                    month_num, day_num, year = today.month, today.day, today.year
                break

    start_time = f"{year}-{month_num:02d}-{day_num:02d}T10:00"
    end_time = f"{year}-{month_num:02d}-{day_num:02d}T11:00"

    # 2. Extract Title and Location
    location = "Not specified"
    clean_title = "New Meeting"
    
    # Remove action verbs and articles more carefully
    noise_words = ["create", "add", "new", "appointment", "meeting", "schedule", "event", "reminder", "an", "a"]
    
    # Remove words at start
    words = text.split()
    while words and words[0] in noise_words:
        words.pop(0)
    
    # Rebuild text
    text = " ".join(words)
    
    # Handle "titled" or "called"
    if "titled" in text: 
        text = text.split("titled", 1)[1].strip()
    elif "called" in text: 
        text = text.split("called", 1)[1].strip()
    
    # Split by " at "
    parts = text.split(" at ")
    
    # Part 0 is usually Title
    clean_title = parts[0].strip()
    
    # Remove date words from title
    for month in months:
        clean_title = clean_title.replace(month, "").strip()
    for day in weekdays:
        clean_title = clean_title.replace(day, "").strip()
    for rel in relative_dates:
        clean_title = clean_title.replace(rel, "").strip()
    
    # Remove "on", "for", "the", "of", numbers (dates)
    clean_title = re.sub(r'\b(on|for|the|of|\d+st|\d+nd|\d+rd|\d+th|\d+)\b', '', clean_title).strip()
    
    # Remove multiple spaces
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    # Remove trailing periods and other punctuation
    clean_title = clean_title.rstrip('.?!,;:').strip()
    
    # Capitalize properly
    if clean_title:
        clean_title = clean_title.capitalize()
    else:
        clean_title = "New Meeting"
    
    # Extract location from remaining parts
    for part in parts[1:]:
        # Check if this part contains date info
        is_date_part = False
        if any(m in part for m in months) or any(w in part for w in weekdays) or any(r in part for r in relative_dates):
            is_date_part = True
        
        # Check if it is a number (like "at 5") -> Time (ignore for now or treat as date)
        if re.search(r'^\d', part.strip()):
            is_date_part = True
            
        if not is_date_part:
            # If it's not a date, it's the location!
            location = part.strip().capitalize()

    return clean_title, start_time, end_time, location

def parse_target_day_index(user_text, forecast_list, current_index):
    user_text = user_text.lower()
    if "yesterday" in user_text: return -1
    elif "day after tomorrow" in user_text: return 2
    elif "tomorrow" in user_text: return 1
    elif "today" in user_text: return 0
    for i, entry in enumerate(forecast_list):
        if entry.get('day', '').lower() in user_text: return i
    if "next" in user_text and "days" in user_text: return 0
    return current_index

def get_forecast_summary(forecast_list, user_text, city, start_index):
    user_text = text_to_int(user_text.lower())
    match = re.search(r'next (\d+) days', user_text)
    if match:
        requested_count = int(match.group(1))
        if start_index >= len(forecast_list): start_index = 0
        available_days = len(forecast_list) - start_index
        count = min(requested_count, available_days)
        msg = f"I can only provide {available_days} days. " if requested_count > available_days else ""
        response = f"{msg}Here is the weather in {city} starting {forecast_list[start_index].get('day')} for the next {count} days:\n"
        for i in range(count):
            day = forecast_list[start_index+i]
            response += f"• {day.get('day').capitalize()}: {day.get('weather')}, {day.get('temperature',{}).get('min')} to {day.get('temperature',{}).get('max')} degrees.\n"
        return response
    
    if start_index >= len(forecast_list): start_index = 0
    day = forecast_list[start_index]
    actual = day.get('weather','').lower()
    day_name = day.get('day', 'today') 
    temps = day.get('temperature', {})
    temp_string = f"with temperatures between {temps.get('min','?')} and {temps.get('max','?')} degrees"

    asked = None
    for c in API_CONDITIONS: 
        if c in user_text: asked = c; break
    if not asked:
        for k,v in CONDITION_MAPPING.items(): 
            if k in user_text: asked = v; break
            
    if asked:
        match = (asked == actual) or ("rain" in asked and "rain" in actual) or (asked=="sunny" and actual=="clear sky")
        if match: 
            return f"Yes, on {day_name}, it will be {actual} in {city} {temp_string}."
        else: 
            return f"No, on {day_name}, it won't be {asked}, it will be {actual} in {city} {temp_string}."
    
    return f"The weather in {city} on {day.get('day')} is {actual} {temp_string}."

def log_response(response_text):
    """Helper to log assistant responses to conversation history"""
    global conversation_history
    if conversation_history:
        conversation_history[-1]["assistant"] = response_text

def handle_command(text):
    global last_location, last_day_index, last_created_title, conversation_history
    text = text.lower()
    
    # Log user input to conversation history
    conversation_history.append({
        "turn": len(conversation_history) + 1,
        "user": text,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    # CRITICAL: Check appointment/calendar keywords FIRST (before weather)
    # This prevents "create event" or "add reminder" from triggering weather
    appointment_keywords = ["appointment", "calendar", "schedule", "event", "reminder", "meeting", "remainder"]
    if any(keyword in text for keyword in appointment_keywords):
        # Check if this is about ADDING a field (location) to existing appointment
        if "add" in text and ("location" in text or "place" in text):
            # This is about adding location to existing appointment
            events = get_appointments()
            target_title_search = None
            
            # Check which appointment to modify
            if "first" in text and events:
                target_title_search = events[0].get('title')
            elif "second" in text and len(events) > 1:
                target_title_search = events[1].get('title')
            elif "third" in text and len(events) > 2:
                target_title_search = events[2].get('title')
            elif "last" in text and events:
                target_title_search = events[-1].get('title')
            elif "previous" in text or "recently" in text:
                if last_created_title:
                    target_title_search = last_created_title
                elif events:
                    target_title_search = events[-1].get('title')
            else:
                # Try to find appointment by name in the command
                for event in events:
                    event_title = event.get('title', '').lower()
                    if event_title in text:
                        target_title_search = event.get('title')
                        break
            
            if target_title_search:
                speak_text("What is the location?")
                print(">>> Waiting for location...")
                loc_file = record_audio(silence_duration=2.0)
                if loc_file:
                    loc_text = transcribe_audio(loc_file)
                    if loc_text:
                        new_location = loc_text.strip(" .?!").capitalize()
                        speak_text(f"Adding location {new_location} to {target_title_search}.")
                        success = modify_appointment(target_title_search, new_location=new_location)
                        if success:
                            speak_text("Location added.")
                        else:
                            speak_text("Could not update.")
            else:
                speak_text("Could not find the appointment.")
            return True
        
        # First check if this is about CLEARING a field (not deleting appointment)
        if ("remove" in text or "delete" in text or "clear" in text) and any(field in text for field in ["location", "place", "time"]):
            # This is about clearing a field, not deleting the appointment
            clear_location = "location" in text or "place" in text
            clear_time = "time" in text
            
            # Find target appointment
            events = get_appointments()
            target_title_search = None
            
            if events:
                if "previous" in text or "last" in text or "recently" in text:
                    if last_created_title:
                        target_title_search = last_created_title
                    else:
                        target_title_search = events[-1].get('title')
                else:
                    target_title_search = events[0].get('title')
            
            if target_title_search:
                if clear_location:
                    speak_text(f"Removing location from {target_title_search}.")
                    success = modify_appointment(target_title_search, new_location="Not specified")
                    if success:
                        speak_text("Location cleared.")
                    else:
                        speak_text("Could not update.")
                elif clear_time:
                    speak_text("I cannot remove the time from an appointment. Time is required. You can change the date or time instead.")
            else:
                speak_text("Could not find the appointment.")
            return True
        
        # Now handle actual appointment deletion
        if "delete" in text or "remove" in text or "cancel" in text:
            if "all" in text or "everything" in text:
                speak_text("Deleting all appointments...")
                count = delete_all_appointments()
                time.sleep(2.0)  # Extra wait for server sync
                speak_text(f"Deleted {count} appointments. Calendar is empty.")
                last_created_title = None  # Reset tracking
                return True
            
            # Check for "delete last X appointments"
            match = re.search(r'last (\d+|two|three|four|five)', text)
            if match:
                count_word = match.group(1)
                word_to_num = {"two": 2, "three": 3, "four": 4, "five": 5}
                delete_count = word_to_num.get(count_word, int(count_word) if count_word.isdigit() else 1)
                
                events = get_appointments()
                if len(events) < delete_count:
                    speak_text(f"You only have {len(events)} appointments.")
                    delete_count = len(events)
                
                speak_text(f"Deleting last {delete_count} appointments...")
                deleted = 0
                for i in range(delete_count):
                    if events:
                        target = events[-(i+1)].get('title')
                        if delete_appointment(target):
                            deleted += 1
                            time.sleep(0.5)
                
                speak_text(f"Deleted {deleted} appointments.")
                if last_created_title: last_created_title = None
                return True

            events = get_appointments()
            target_title = None

            ordinals = {
                "first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
                "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9
            }
            found_ordinal = False
            for word, index in ordinals.items():
                if word in text:
                    if len(events) > index: target_title = events[index].get('title')
                    found_ordinal = True
                    break
            
            if not found_ordinal:
                if "last" in text:
                    if events: target_title = events[-1].get('title')
                elif "previous" in text or "recently" in text:
                    if last_created_title: target_title = last_created_title
                    elif events: target_title = events[-1].get('title')
                elif "titled" in text or "called" in text or "named" in text:
                    try:
                        if "titled" in text: target_title = text.split("titled")[1].strip().capitalize()
                        elif "called" in text: target_title = text.split("called")[1].strip().capitalize()
                        elif "named" in text: target_title = text.split("named")[1].strip().capitalize()
                    except: pass
                else:
                    # Try to extract appointment name from "delete the appointment X"
                    for event in events:
                        event_title = event.get('title', '').lower()
                        if event_title in text:
                            target_title = event.get('title')
                            break

            if target_title:
                speak_text(f"Deleting appointment: {target_title}...")
                success = delete_appointment(target_title)
                time.sleep(1.0)  # Wait for API to sync
                if success: 
                    speak_text("Done.")
                    if target_title == last_created_title: last_created_title = None
                else: 
                    speak_text("Could not find that appointment.")
            else:
                speak_text("Which appointment should I delete?")
                print(">>> Waiting for appointment name...")
                title_file = record_audio(silence_duration=2.0)
                if title_file:
                    title_text = transcribe_audio(title_file)
                    if title_text:
                        target_title = title_text.strip(" .?!").capitalize()
                        speak_text(f"Deleting appointment: {target_title}...")
                        success = delete_appointment(target_title)
                        time.sleep(1.0)
                        if success: 
                            speak_text("Done.")
                            if target_title == last_created_title: last_created_title = None
                        else: 
                            speak_text("Could not find that appointment.")

        
        elif "change" in text or "modify" in text or "move" in text or "rename" in text:
            new_location = None
            new_title = None
            new_date = None
            
            # Check what needs to be changed
            change_location = "place" in text or "location" in text or "move" in text
            change_title = "title" in text or "name" in text or "rename" in text
            change_date = "date" in text or "time" in text or "day" in text
            
            # Check if new value is provided in command
            if " to " in text:
                after_to = text.split(" to ", 1)[1].strip(" .?!")
                
                if change_title:
                    new_title = after_to.capitalize()
                elif change_location:
                    new_location = after_to.capitalize()
                elif change_date:
                    # Parse date from after_to
                    new_date = after_to
            
            # If no new value provided, ask for it
            if change_location and not new_location:
                speak_text("What is the new location?")
                print(">>> Waiting for new location...")
                loc_file = record_audio(silence_duration=2.0)
                if loc_file:
                    loc_text = transcribe_audio(loc_file)
                    if loc_text:
                        new_location = loc_text.strip(" .?!").capitalize()
            
            if change_title and not new_title:
                speak_text("What is the new title?")
                print(">>> Waiting for new title...")
                title_file = record_audio(silence_duration=2.0)
                if title_file:
                    title_text = transcribe_audio(title_file)
                    if title_text:
                        new_title = title_text.strip(" .?!").capitalize()
            
            if change_date and not new_date:
                speak_text("What is the new date?")
                print(">>> Waiting for new date...")
                date_file = record_audio(silence_duration=2.0)
                if date_file:
                    date_text = transcribe_audio(date_file)
                    if date_text:
                        new_date = date_text.strip(" .?!")
            
            # Find target appointment
            events = get_appointments()
            target_title_search = None
            
            if events:
                # Try to match by date first if date is mentioned
                months = ["january", "february", "march", "april", "may", "june", 
                         "july", "august", "september", "october", "november", "december"]
                weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                
                date_mentioned = None
                for month in months:
                    if month in text:
                        date_mentioned = month
                        break
                for day in weekdays:
                    if day in text:
                        date_mentioned = day
                        break
                if "tomorrow" in text:
                    date_mentioned = "tomorrow"
                    
                if date_mentioned:
                    # Find appointment with matching date
                    today = datetime.date.today()
                    tomorrow = today + datetime.timedelta(days=1)
                    
                    for e in events:
                        start = e.get('start_time', '')
                        if date_mentioned == "tomorrow" and str(tomorrow) in start:
                            target_title_search = e.get('title')
                            break
                        elif date_mentioned in start.lower():
                            target_title_search = e.get('title')
                            break
                
                # Fallback to last created or first appointment
                if not target_title_search:
                    if last_created_title:
                        for e in events:
                            if e.get('title') == last_created_title:
                                target_title_search = last_created_title
                                break
                        if not target_title_search: last_created_title = None

                if not target_title_search:
                    if "previous" in text or "last" in text or "recently" in text:
                        target_title_search = events[-1].get('title')
                    else:
                        target_title_search = events[0].get('title')

            if target_title_search and (new_location or new_title or new_date):
                # Check if change is actually needed
                if new_title and new_title.lower() == target_title_search.lower():
                    speak_text(f"The title is already {new_title}.")
                else:
                    if new_title:
                        speak_text(f"Changing title of {target_title_search} to {new_title}.")
                        success = modify_appointment(target_title_search, new_title=new_title)
                        if success: 
                            last_created_title = new_title
                            speak_text("Updated.")
                        else: 
                            speak_text("Could not update.")
                    elif new_location:
                        speak_text(f"Moving appointment {target_title_search} to {new_location}.")
                        success = modify_appointment(target_title_search, new_location=new_location)
                        if success:
                            speak_text("Updated.")
                        else:
                            speak_text("Could not update.")
                    elif new_date:
                        # Parse the new date
                        _, start_time, end_time, _ = parse_appointment_details(f"appointment on {new_date}")
                        speak_text(f"Changing date of {target_title_search} to {start_time.split('T')[0]}.")
                        success = modify_appointment(target_title_search, new_date=start_time, new_end_date=end_time)
                        if success:
                            speak_text("Updated.")
                        else:
                            speak_text("Could not update.")
            else:
                speak_text("I need to know what to change, or the appointment was not found.")


        elif "add" in text or "create" in text or "new" in text:
            title, start, end, loc = parse_appointment_details(text)
            msg = f"Adding appointment called {title}"
            if loc != "Not specified": msg += f" at {loc}"
            msg += f" on {start.split('T')[0]}."
            speak_text(msg)
            create_appointment(title, "Voice Entry", start, end, loc)
            time.sleep(1.0)  # Wait for API to sync
            last_created_title = title 
            speak_text("Appointment created successfully.")

        elif any(w in text for w in ["read", "what", "list", "where", "show", "display", "check", "when"]):
            time.sleep(1.0)  # Longer delay to ensure latest data
            raw_events = get_appointments()
            events = [e for e in raw_events if e.get('title') and e.get('title').strip()]
            
            if not events: 
                speak_text("You have no appointments.")
            else:
                if "where" in text:
                    next_evt = events[0]
                    location = next_evt.get('location', 'Not specified')
                    speak_text(f"Your next appointment is at {location}.")
                elif "when" in text or "time" in text:
                    next_evt = events[0]
                    start_time = next_evt.get('start_time', 'Not specified')
                    if 'T' in start_time:
                        date_part, time_part = start_time.split('T')
                        speak_text(f"Your next appointment is on {date_part} at {time_part}.")
                    else:
                        speak_text(f"Your next appointment is on {start_time}.")
                else:
                    # Print full details to console
                    count = len(events)
                    print(f"\n{'='*60}")
                    print(f"APPOINTMENTS ({count} total):")
                    print('='*60)
                    for i, evt in enumerate(events, 1):
                        title = evt.get('title', 'Untitled')
                        date = evt.get('start_time', 'No date').split('T')[0] if 'T' in evt.get('start_time', '') else 'No date'
                        time_str = evt.get('start_time', 'No time').split('T')[1] if 'T' in evt.get('start_time', '') else 'No time'
                        location = evt.get('location', 'No location')
                        
                        print(f"{i}. {title}")
                        print(f"   Date: {date}")
                        print(f"   Time: {time_str}")
                        print(f"   Location: {location}")
                        print()
                    print('='*60)
                    
                    # Speak only count and titles
                    if count == 1:
                        title = events[0].get('title', 'Untitled')
                        speak_text(f"You have 1 appointment: {title}.")
                    else:
                        titles = [f"{i+1}. {e.get('title', 'Untitled')}" for i, e in enumerate(events)]
                        titles_spoken = ", ".join(titles)
                        speak_text(f"You have {count} appointments: {titles_spoken}.")
        return True

    # WEATHER SECTION - Only trigger if NOT an appointment command
    appointment_keywords = ["appointment", "calendar", "schedule", "event", "reminder", "meeting"]
    has_appointment_keyword = any(keyword in text for keyword in appointment_keywords)
    
    if not has_appointment_keyword and any(t in text for t in BASE_TRIGGERS + CONDITION_TRIGGERS):
        city = None
        words = text.split()
        if "in" in words: 
            try: city = words[words.index("in")+1].strip("?.!").capitalize(); last_location = city
            except: pass
        if not city and "about" in words:
            try: 
                c = words[words.index("about")+1].strip("?.!")
                if c not in ["tomorrow","today"]: city=c.capitalize(); last_location = city
            except: pass
        if not city: city = last_location
        
        if not city:
            speak_text("Please tell me the location.")
            print(">>> Waiting for location input...")
            loc_file = record_audio(silence_duration=2.0)
            if loc_file:
                loc_text = transcribe_audio(loc_file)
                if loc_text:
                    temp_words = loc_text.split()
                    if "in" in temp_words:
                        try: city = temp_words[temp_words.index("in")+1].strip("?.!").capitalize()
                        except: city = loc_text.strip("?.!").capitalize()
                    else:
                        city = loc_text.strip("?.!").capitalize()
                    last_location = city
        
        if not city:
            speak_text("I didn't hear a location. Canceling.")
            return True

        print(f"Weather query for: {city}")
        data = get_weather_forecast(city)
        if data and 'forecast' in data:
            new_index = parse_target_day_index(text, data['forecast'], last_day_index)
            if new_index != -1: last_day_index = new_index
            speak_text(get_forecast_summary(data['forecast'], text, city, last_day_index))
        else:
            speak_text(f"I couldn't find weather data for {city}.")
        return True

    if "stop" in text or "exit" in text:
        speak_text("Goodbye.")
        return False
    
    # NEW: Show conversation history - flexible matching for mishearings
    # Removed "previous" to avoid conflicts with "delete previous appointment"
    history_triggers = ["history", "story", "hesprey", "hisprey", "histry", "estory", "conversation"]
    if any(trigger in text for trigger in history_triggers):
        if not conversation_history:
            speak_text("No conversation history yet.")
        else:
            print("\n" + "="*60)
            print("CONVERSATION HISTORY:")
            print("="*60)
            for entry in conversation_history[-10:]:  # Show last 10 turns
                timestamp_display = entry['timestamp'].split('T')[1][:8] if 'T' in entry['timestamp'] else ""
                print(f"\nTurn {entry['turn']} ({timestamp_display}):")
                print(f"  You: {entry['user']}")
                if 'assistant' in entry:
                    # Truncate long responses
                    response = entry['assistant']
                    if len(response) > 100:
                        response = response[:100] + "..."
                    print(f"  Assistant: {response}")
            print("="*60)
            
            count = len(conversation_history)
            speak_text(f"I've shown the last {min(count, 10)} conversation turns on screen.")
        return True
        
    speak_text("I didn't understand.")
    return True

if __name__ == "__main__":
    try:
        # delete_all_appointments()
        pass
    except Exception:
        pass
    
    speak_text("System ready")
    running = True
    while running:
        input("\nPress Enter to activate microphone...")
        fn = record_audio()
        if fn:
            ut = transcribe_audio(fn)
            if ut: running = handle_command(ut)