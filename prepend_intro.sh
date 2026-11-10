#!/bin/bash
# Usage: ./prepend_intro.sh <video.mp4> <output.mp4>
# Prepends the K-Mystery intro to any video
INTRO="intro_5s.mp4"
if [ ! -f "$INTRO" ]; then
  echo "Error: intro_5s.mp4 not found"
  exit 1
fi
if [ $# -lt 2 ]; then
  echo "Usage: $0 <input_video> <output_video>"
  exit 1
fi
# Create concat list
echo "file '$INTRO'" > /tmp/concat_list.txt
echo "file '$1'" >> /tmp/concat_list.txt
ffmpeg -f concat -safe 0 -i /tmp/concat_list.txt -c copy "$2" -y
echo "Done: $2"
