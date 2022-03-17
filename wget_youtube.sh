#!/bin/bash -e

# Download YouTube audio from the input URL. Convert it to 16kHz single-channel .wav file.
# Trim the beginning and end 90 seconds because these regions may contain music or reporter voice.
# You may need to install youtube-dl, sox, and ffmpeg on your Linux system.
# Example: 
#   scripts/wget_youtube.sh "https://youtu.be/lbOoNipiiT0" corpus/background/recordings/rec0087.wav

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <url> <wavfile>"
    exit
fi
url=$1
wavfile=$2

dirname=`dirname ${wavfile}`
mkdir -p $dirname
rm -rf /tmp/$dirname
mkdir -p /tmp/$dirname
rm -f ${wavfile}

# Download YouTube audio from URL and save the audio to /tmp/$wavfile
youtube-dl -x --audio-format wav --output /tmp/${wavfile} $url

# Extract the first channel from /tmp/${wavfile}, convert it to 16kHz, and save 
# the resulting file to $wavfile
echo "Saving 16kHz single-channel audio to $wavfile"
ffmpeg -i /tmp/${wavfile} -ar 16000 -acodec pcm_s16le -af "pan=mono|FC=FR" ${wavfile}

# Trim audio and normalize volume
length=`soxi -D ${wavfile}`
length=${length%.*}
if [ "$length" -gt "180" ]; then
    echo "Trim beginning and end of $wavfile"
    sox --norm=-1 ${wavfile} /tmp/${wavfile} trim 90 -90
else
    sox --norm=-1 ${wavfile} /tmp/${wavfile}
fi
sox /tmp/${wavfile} ${wavfile} silence -l 1 0.1 1% -1 0.1 1% reverse
sox ${wavfile} /tmp/${wavfile} silence 1 0.1 1% reverse
cp /tmp/${wavfile} ${wavfile}

# Remove tmp file
rm -rf /tmp/$dirname 


