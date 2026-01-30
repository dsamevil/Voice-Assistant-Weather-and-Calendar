# Voice-Assistant-Weather-and-Calendar


## 1. Clone the repository :

git clone https://github.com/dsamevil/Voice-Assistant-Weather-and-Calendar.git

## 2. Download the necessary Libraries :

pip install -r requirements.txt

## 3. Go to the downloaded path and run the main.py file :

python3 main.py

or

python main.py

#Note !!!
change the API Key (TEAM_ID) in api_client.py while you use


# Final_voice_assistant 
This is a docker file for the same project which requires pre recorded audio files inorder to run the code.
Record the audio in .wav format and put the audios in the test_audio folder.

## Build the file everytime the changes is made
docker build -t voice-assistant .

## Run the file
### Scenario A: Default (Only internal files) Runs just your test_audio files.
docker run voice-assistant

### Scenario B: Multiple Files (Mount a Folder) This maps a folder on your computer to /app/user_input. The script sees it's a folder and runs all files inside one by one. Rename C:\Users\ASUS\Desktop\my_audios to your location
docker run -v "C:\Users\ASUS\Desktop\my_audios:/app/user_input" voice-assistant

### Scenario C: Single File (Mount a File) This maps a single file on your computer to /app/user_input. The script sees it's a file and runs it immediately. Rename C:\Users\ASUS\Desktop\my_audios\command.wav to your location
docker run -v "C:\Users\ASUS\Desktop\my_audios\command.wav:/app/user_input" voice-assistant

