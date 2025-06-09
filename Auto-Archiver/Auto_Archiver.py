import random
import re
import os
import sys
import keyboard
import subprocess as sp
import time
import requests
from urllib.parse import urlparse
import difflib

# notes for future, if stream is not live but scheduled for a future time, this is the format:
# "upcomingEventData":{"startTime":"[UNIX-TIME]","isReminderSet":false,"upcomingEventText":{"runs":[{"text":"Scheduled for "},{"text":"DATE_PLACEHOLDER"}]}}

def get_channel_name(url):
    # Extract channel name from URL (assumes last path segment is channel)
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
#        print(f"Parsed URL: {parsed}, Path Parts: {path_parts}")  # Debugging line
    if path_parts:
        return path_parts[-1]
    return "UnknownChannel"

def main(args):
    if len(args) < 1:
        print("Usage: Auto_Archiver.py <URL>")
        return
    print("Starting Auto Archiver...")
    #print(args)
    # Set console title
    chaname = get_channel_name(args[0]) if args else "Anon's channel"
    title_str = f"Archiving {chaname}'s streams as they happen..."
    if os.name == 'nt':
        os.system(f'title {title_str}')
    else:
        sys.stdout.write(f"\x1b]2;{title_str}\x07")
    yt_dlp_handler()
    try:
        lurker(args)
    except KeyboardInterrupt:
        print("Terminating process. Goodbye.")
    
def clear_screen():
    # Clear the terminal screen in a cross-platform way
    os.system('cls' if os.name == 'nt' else 'clear')

def yt_dlp_handler():
    capout = sp.run("yt-dlp --version", shell=True, capture_output=True, text=True)
    version = capout.stdout.strip()
    # Check if version matches YYYY.MM.DD format
    if not re.match(r"^\d{4}\.\d{2}\.\d{2}$", version):
        # Detect OS
        if sys.platform.startswith("win"):
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            ytdlp_filename = "yt-dlp.exe"
        elif sys.platform.startswith("linux"):
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
            ytdlp_filename = "yt-dlp"
        elif sys.platform.startswith("darwin"):
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
            ytdlp_filename = "yt-dlp_macos"
        else:
            print("Unsupported OS for yt-dlp download.")
            return
        # Download yt-dlp
        try:
            print(f"Downloading yt-dlp from {ytdlp_url}...")
            response = requests.get(ytdlp_url, stream=True)
            response.raise_for_status()
            with open(ytdlp_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            # Make executable if not Windows
            if not sys.platform.startswith("win"):
                os.chmod(ytdlp_filename, 0o755)
            print(f"yt-dlp downloaded as {ytdlp_filename}.")
        except Exception as e:
            print(f"Failed to download yt-dlp: {e}")
    else:
        # Ensure yt-dlp is updated with admin privileges
        if sys.platform.startswith("win"):
            sp.run('powershell -Command "Start-Process yt-dlp -ArgumentList \'-U\' -Verb RunAs"', shell=True)
        else:
            # On Unix-like systems, use sudo
            sp.run("sudo yt-dlp -U", shell=True)
        print(f"yt-dlp version is up to date: {version}")

def loadSettings():
    # Locate and read the contents of "settings.txt" in the current directory
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.txt")
    if not os.path.isfile(settings_path):
        print(f"Settings file not found: {settings_path}")
        user_home = os.path.expanduser("~")
        default_archive_location = os.path.join(user_home, "Videos")
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(f'archiveLocation="{default_archive_location}/"\n')
            f.write('yt-dlp-Args-Default=""\n')
    with open(settings_path, "r", encoding="utf-8") as f:
        contents = f.read()
    settings = []
    for line in contents.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            settings.append((key.strip(), value.strip()))
    print(settings)
    return [settings[0],settings[1]]
    
#Lurker is going to be the running thing that checks to see if there is a stream live, if there is, it will begin archiving until the stream is over, if it is not live it will wait for the appropriate time to attempt it
#Lurker once stream capture has begun, lurker will put the executed command into its own thread, then listen for other input
def lurker(channel):
    first_run = 1
    chaname = get_channel_name(channel[0])
    yt_settings = loadSettings()

    # Change working directory to the save location from yt_settings[0]
    save_location = yt_settings[0][1]
    workingFolder = find_or_create_channel_folder(save_location,chaname)
    print(workingFolder)
    if os.path.isdir(save_location):
        # Find or create the channel folder
        channel_folder = find_or_create_channel_folder(save_location, chaname)
        os.chdir(channel_folder)
    else:
        print(f"Save location does not exist: {save_location}")
    currVid = []
    check_again_interval: list[int] = [60, 120, 180, 240, 300, 900, 1800, 3600]
    check_this_time = check_again_interval[random.randint(0, len(check_again_interval) - 1)]
    title = ""
    last_check_time = None
    next_check_time = None
    while 1:
        current_time = int(time.time())
            
        clear_screen()
            
        last_check_time = time.time()
        next_check_time = last_check_time + check_again_interval[random.randint(0, len(check_again_interval) - 1)]
        gatVids = getVideoURL(channel)
        is_multidimensional = (
            isinstance(gatVids, list) and
            len(gatVids) > 0 and
            isinstance(gatVids[0], (list, tuple))
        )
        clear_screen()
        if not len(gatVids) ==0:
            if is_multidimensional:
                currVid = gatVids[0]
            else:
                currVid = [gatVids[0], gatVids[1]]
            fullURL = "https://youtube.com/watch?v="+currVid[0]
            title = getVideoTitle(currVid[0])
            print(fullURL)
            if checkTime(int(currVid[1])):
                print("The stream is live! Beginning archive...")
                arguments = yt_settings[1][1]
                match = re.search(r'\{(.*?)\}', yt_settings[1][1])
                if match:
                    arguments = match.group(1).replace('"', '')
                else:
                    arguments = ""
                #print(f"yt-dlp {fullURL} {arguments}")
                sp.run(f"yt-dlp {fullURL} {arguments}",shell=True,cwd=workingFolder)
                print("Stream archived. Waiting for next stream...")
        else:
            print("No streams available to archive right now... going back to waiting...")
        
        
        # Format current_time as a 10 minute countdown timer (MM:SS)
        seconds_left = int(next_check_time - time.time())
        while seconds_left > 0:
            minutes = seconds_left // 60
            seconds = seconds_left % 60
            timer_str = f"{minutes:02d}:{seconds:02d}"
            if title:
                print(f"{title} is not live yet, checking again in {timer_str}")
            else:
                print(f"There is no stream yet, checking again in {timer_str}")
            print("Press 'CTRL+C' to stop")
            time.sleep(1)
            clear_screen()
        

def find_or_create_channel_folder(base_path, chaname):
    # Remove '@' characters from base_path if present
    bp = base_path.replace('@', '')
    # Remove '@' characters from chaname if present
    cn = chaname.replace('@', '')
    # List all directories in bp
    dirs = [d for d in os.listdir(bp) if os.path.isdir(os.path.join(bp, d))]
    # Use difflib to find the closest match
    match = difflib.get_close_matches(cn, dirs, n=1, cutoff=0.6)
    if not match:
        # Try to find a folder with a similar character sequence (subsequence match)
        def is_subsequence(short, long):
            it = iter(long.lower())
            return all(c.lower() in it for c in short.lower())
        subseq_matches = [d for d in dirs if is_subsequence(cn, d) or is_subsequence(d, cn)]
        if subseq_matches:
            folder = subseq_matches[0]
        else:
            folder = cn
            os.makedirs(os.path.join(bp, folder), exist_ok=True)
    else:
        folder = match[0]
    return os.path.join(bp, folder)



def getVideoTitle(vidID):
        
    response = requests.get(f"https://youtube.com/watch?v={vidID}")
    title = re.findall(rb'<meta name="title" content="(.*?)">',response.content)
    title = title[0]
    print(title)
    return title

def checkTime(t):
    return (int)(time.time()) >= t
       
# returns live video, and if none is available, returns the next planned stream.
def getVideoURL(args):
    url = args[0]+"/streams"
#      print(url)
    channel_name = get_channel_name(args[0])
#        print(channel_name)
    try:
        response = requests.get(url)
        response.raise_for_status()
        # print(response)
            

        # Extract all relevant fields from response.content
        is_alive = re.findall(rb'"iconType":"LIVE"',response.content)
        video_ids = re.findall(rb'"videoId":"(.*?)"', response.content)
        startTimes = re.findall(rb'"startTime":"(.*?)"', response.content)
        ret = []


        # Check if "is_alive" has an entry and find the nearest "videoId" to "iconType":"LIVE"
        live_video_id = None
#           print(is_alive)
        if is_alive:
            # Find all occurrences of "iconType":"LIVE" and their positions
            live_positions = [m.start() for m in re.finditer(rb'"iconType":"LIVE"', response.content)]
            if live_positions:
                # For each live position, find the nearest preceding "videoId"
                for pos in live_positions:
                    # Find all "videoId" matches before this position
                    video_id_matches = list(re.finditer(rb'"videoId":"(.*?)"', response.content[:pos]))
                    if video_id_matches:
                        # Take the last videoId before the LIVE iconType
                        nearest_video_id = video_id_matches[-1].group(1).decode('utf-8')
                        live_video_id = nearest_video_id
                        break  # Only grab the first LIVE found
            ret = [live_video_id,0]
#                print(f"Live video id: {live_video_id}")
        else:
            
            # Deduplicate video_ids and startTimes while preserving order
            def dedup_list(seq):
                seen = set()
                return [x for x in seq if not (x in seen or seen.add(x))]

            video_ids = dedup_list(video_ids)
            startTimes = dedup_list(startTimes)


            # Remove video_ids entries after the last entry count in startTimes
            if len(video_ids) > len(startTimes):
                video_ids = video_ids[:len(startTimes)]

            # Pair up video_ids and startTimes for returning
            for vid, st in zip(video_ids, startTimes):
                ret.append((vid.decode('utf-8'), st.decode('utf-8')))

            # Sort ret by the smallest second value if ret contains tuples
            if ret and isinstance(ret[0], tuple):
                ret.sort(key=lambda x: int(x[1]))
        return ret


            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    

if __name__ == "__main__":
    main(sys.argv[1:])