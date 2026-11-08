# K-Mystery YouTube Channel - Progress

## Channel
- Name: Korean Mysteries
- Handle: @Korean_Mysteries
- URL: https://www.youtube.com/@Korean_Mysteries

## Video 01: The Korean Prince Locked in a Rice Chest
- Status: Uploaded ✅
- URL: (uploaded)
- Duration: 8:21
- Files: youtube/1/

## Video 02: Korea's Most Haunted Psychiatric Hospital
- Status: Uploaded ✅
- URL: https://youtu.be/TYOcCE4zp30
- Duration: 6:45
- Files: youtube/2/

## Pipeline
1. Script (English documentary style)
2. TTS (EC2 ElevenLabs, Adam voice)
3. Whisper subtitles (English, CPU)
4. Images (Leonardo.ai/Krea/ChatGPT)
5. FFmpeg (Ken Burns + subtitles + audio)
6. BGM (YouTube Audio Library)
7. Intro prepend (intro_5s.mp4)
8. Metadata (title, description, tags, timestamps)
9. Upload (PostWire API)

## Infrastructure
- EC2: 54.116.201.144 (Seoul, t3.micro)
- TTS: port 80 /tts (ElevenLabs)
- Email: port 80 /send-email (Gmail SMTP)
- Nginx reverse proxy

## Next Steps
- Video 03 topic selection
- Channel art/profile image
- SSH port restriction
EOF