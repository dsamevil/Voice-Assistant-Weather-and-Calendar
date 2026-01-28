# Voice-Assistant-Weather-and-Calendar


## 1. Clone the repository :

git clone https://github.com/dsamevil/Voice-Assistant-Weather-and-Calendar.git

## 2. Download the necessary Libraries :

pip install -r requirements.txt

## 3. Go to the downloaded path and run the main.py file :

python3 main.py

or

python main.py




### Final_voice_assistant 
This is a docker file for the same project which requires pre recorded audio files inorder to run the code.
Record the audio in .wav format and put the audios in the test_audio folder.

# Build the file everytime the changes is made
docker build -t final-test-submission .

# Run the file
docker run final-test-submission
