#!/usr/bin/env python
# 
# Upload videos to Youtube from the command-line using APIv3.
#
# Author: Arnau Sanchez <pyarnau@gmail.com>
# Project: https://github.com/tokland/youtube-upload
"""
Upload a video to Youtube from the command-line.

    $ youtube-upload --title="A.S. Mutter playing" \
                     --description="Anne Sophie Mutter plays Beethoven" \
                     --category=Music \
                     --tags="mutter, beethoven" \
                     anne_sophie_mutter.flv
    pxzZ-fYjeYs
"""

import os
import sys
import time
import optparse
import collections
import webbrowser
import tempfile

import googleapiclient.errors
import oauth2client

from . import auth
from . import upload_video
from . import categories
from . import lib
from . import playlists

# http://code.google.com/p/python-progressbar (>= 2.3)
try:
    import progressbar
except ImportError:
    progressbar = None

class InvalidCategory(Exception): pass
class OptionsError(Exception): pass
class AuthenticationError(Exception): pass
class RequestError(Exception): pass

EXIT_CODES = {
    OptionsError: 2,
    InvalidCategory: 3,
    RequestError: 3,
    AuthenticationError: 4,
    oauth2client.client.FlowExchangeError: 4,
    NotImplementedError: 5,
}

WATCH_VIDEO_URL = "https://www.youtube.com/watch?v={id}"

debug = lib.debug
struct = collections.namedtuple

def open_link(url):
    """Opens a URL link in the client's browser."""
    webbrowser.open(url)
    
def get_progress_info():
    """Return a function callback to update the progressbar."""
    progressinfo = struct("ProgressInfo", ["callback", "finish"])

    if progressbar:
        bar = progressbar.ProgressBar(widgets=[
            progressbar.Percentage(), ' ',
            progressbar.Bar(), ' ',
            progressbar.FileTransferSpeed(),
        ])
        def _callback(total_size, completed):
            if not hasattr(bar, "next_update"):
                if hasattr(bar, "maxval"):
                    bar.maxval = total_size
                else:
                    bar.max_value = total_size
                bar.start()
            bar.update(completed)
        def _finish():
            if hasattr(bar, "next_update"):
                return bar.finish()
        return progressinfo(callback=_callback, finish=_finish)
    else:
        return progressinfo(callback=None, finish=lambda: True)

def get_category_id(category):
    """Return category ID from its name."""
    if category:
        if category in categories.IDS:
            ncategory = categories.IDS[category]
            debug("Using category: {0} (id={1})".format(category, ncategory))
            return str(categories.IDS[category])
        else:
            msg = "{0} is not a valid category".format(category)
            raise InvalidCategory(msg)

def upload_youtube_video(youtube, options, video_path, total_videos, index):
    """Upload video with index (for split videos)."""
    u = lib.to_utf8
    title = u(options.title)
    if hasattr(u('string'), 'decode'):   
        description = u(options.description or "").decode("string-escape")
    else:
        description = options.description
    if options.publish_at:    
      debug("Your video will remain private until specified date.")
      
    tags = [u(s.strip()) for s in (options.tags or "").split(",")]
    ns = dict(title=title, n=index+1, total=total_videos)
    title_template = u(options.title_template)
    complete_title = (title_template.format(**ns) if total_videos > 1 else title)
    progress = get_progress_info()
    category_id = get_category_id(options.category)
    request_body = {
        "snippet": {
            "title": complete_title,
            "description": description,
            "categoryId": category_id,
            "tags": tags,
            "defaultLanguage": options.default_language,
            "defaultAudioLanguage": options.default_audio_language,

        },
        "status": {
            "privacyStatus": ("private" if options.publish_at else options.privacy),
            "publishAt": options.publish_at,

        },
        "recordingDetails": {
            "location": lib.string_to_dict(options.location),
            "recordingDate": options.recording_date,
        },
    }

    debug("Start upload: {0}".format(video_path))
    try:
        video_id = upload_video.upload(youtube, video_path, 
            request_body, progress_callback=progress.callback, 
            chunksize=options.chunksize)
    finally:
        progress.finish()
    return video_id

# def get_caption_tempfile(file):
#     """will return a caption file as text"""
#     supported = [".srt"] #TODO: implement verification if it's a text file

#     #open a temporary file because google only allow txt files#
#     with open(file, 'rb') as text:
#         string_return = text.read()
#     temp_file = tempfile.NamedTemporaryFile(suffix=".txt")
#     temp_file.write(string_return)

#     #return tempfile 
#     return temp_file

def upload_caption(youtube, options, video_id):
    """Will upload the caption as draft"""

    with open(options.caption_file, 'r') as text:
        string_return = text.read()

    #making a temporary file as google seems to only acept .txt file
    temp_file = tempfile.NamedTemporaryFile(suffix=".txt",delete=False) #had to use delete=False because of Windows
    temp_file.write(string_return.encode())
    file = temp_file.name

    language = options.caption_lang
    name = options.caption_name

    if options.caption_status.lower() in ["no", "n"]:
        is_draft = False
    elif options.caption_status.lower() is ["yes", "y"]:
        is_draft = True

    insert_result = youtube.captions().insert(
    part="snippet",
    body=dict(
        snippet=dict(
            videoId=video_id,
            language=language,
            name=name,
            isDraft=is_draft
            )
        ),
        media_body=file
    ).execute()

    id = insert_result["id"]
    name = insert_result["snippet"]["name"]
    language = insert_result["snippet"]["language"]
    status = insert_result["snippet"]["status"]

    #removing tempfile manually
    temp_file.close()
    try:
        os.remove(file)
    except:
        pass

    return {"caption_id":id, "caption_name":name, "caption_status":status}

def get_youtube_handler(options):
    """Return the API Youtube object."""
    home = os.path.expanduser("~")
    default_client_secrets = lib.get_first_existing_filename(
        [sys.prefix, os.path.join(sys.prefix, "local")],
        "share/youtube_upload/client_secrets.json")  
    default_credentials = os.path.join(home, ".youtube-upload-credentials.json")
    client_secrets = options.client_secrets or default_client_secrets or \
        os.path.join(home, ".client_secrets.json")
    credentials = options.credentials_file or default_credentials
    debug("Using client secrets: {0}".format(client_secrets))
    debug("Using credentials file: {0}".format(credentials))
    get_code_callback = (auth.browser.get_code 
        if options.auth_browser else auth.console.get_code)
    return auth.get_resource(client_secrets, credentials,
        get_code_callback=get_code_callback)

def parse_options_error(parser, options):
    """Check errors in options."""
    required_options = ["title"]
    missing = [opt for opt in required_options if not getattr(options, opt)]
    if missing:
        parser.print_usage()
        msg = "Some required option are missing: {0}".format(", ".join(missing))
        raise OptionsError(msg)

def video_upload_status(youtube, options, video_id):
    status_dict = youtube.videos().list(part="status", id=video_id, maxResults=5).execute()
    upload_status = status_dict['items'][0]['status']['uploadStatus']
    return upload_status
    #uploaded/processed/rejected
    #TODO figure something out when the video gets rejected

def run_main(parser, options, args, output=sys.stdout):
    """Run the main scripts from the parsed options/args."""
    parse_options_error(parser, options)
    youtube = get_youtube_handler(options)

    if youtube:
        for index, video_path in enumerate(args):
            video_id = upload_youtube_video(youtube, options, video_path, len(args), index)
            video_url = WATCH_VIDEO_URL.format(id=video_id)
            debug("Video URL: {0}".format(video_url))
            if options.open_link:
                open_link(video_url) #Opens the Youtube Video's link in a webbrowser
                
            if options.thumb:
                youtube.thumbnails().set(videoId=video_id, media_body=options.thumb).execute()
            if options.playlist:
                playlists.add_video_to_playlist(youtube, video_id, 
                    title=lib.to_utf8(options.playlist), privacy=options.privacy)

            """this will add the caption to the video via the video id"""
            if options.caption_file:
                #this will wait the video ends processing every 30 seconds, because google wont allow the caption to be added while it's not ended
                print("Waiting for the video to process to upload the caption:\n", "Caption Name:", options.caption_name, "\nCaption File:", options.caption_file, "\nCaption Language:", options.caption_lang, "\nIs Draft:", options.caption_status)
                video_status = video_upload_status(youtube, options, video_id)

                #loop until video_status is processed
                while video_status != "processed":
                    time.sleep(30)
                    video_status = video_upload_status(youtube, options, video_id)
                    #print for debug
                    print(video_status)

                print("Processed! Uploading Captions")
                #now it's pricessed will upload the caption
                caption_upload_out = upload_caption(youtube, options, video_id)
                print("Done!\n Caption ID:", caption_upload_out["caption_id"])

            output.write("Done for ID:" + video_id + "\n")
    else:
        raise AuthenticationError("Cannot get youtube resource")

def main(arguments):
    """Upload videos to Youtube."""
    usage = """Usage: %prog [OPTIONS] VIDEO [VIDEO2 ...]

    Upload videos to Youtube."""
    parser = optparse.OptionParser(usage)

    # Video metadata
    parser.add_option('-t', '--title', dest='title', type="string",
        help='Video title')
    parser.add_option('-c', '--category', dest='category', type="string",
        help='Video category')
    parser.add_option('-d', '--description', dest='description', type="string",
        help='Video description')
    parser.add_option('', '--description-file', dest='description_file', type="string", 
        help='Video description file', default=None)
    parser.add_option('', '--tags', dest='tags', type="string",
        help='Video tags (separated by commas: "tag1, tag2,...")')
    parser.add_option('', '--privacy', dest='privacy', metavar="STRING",
        default="public", help='Privacy status (public | unlisted | private)')
    parser.add_option('', '--publish-at', dest='publish_at', metavar="datetime",
       default=None, help='Publish date (ISO 8601): YYYY-MM-DDThh:mm:ss.sZ')
    parser.add_option('', '--location', dest='location', type="string",
        default=None, metavar="latitude=VAL,longitude=VAL[,altitude=VAL]",
        help='Video location"')
    parser.add_option('', '--recording-date', dest='recording_date', metavar="datetime",
        default=None, help="Recording date (ISO 8601): YYYY-MM-DDThh:mm:ss.sZ")
    parser.add_option('', '--default-language', dest='default_language', type="string",
        default=None, metavar="string", 
        help="Default language (ISO 639-1: en | fr | de | ...)")
    parser.add_option('', '--default-audio-language', dest='default_audio_language', type="string",
        default=None, metavar="string", 
        help="Default audio language (ISO 639-1: en | fr | de | ...)")
    parser.add_option('', '--thumbnail', dest='thumb', type="string", metavar="FILE", 
        help='Image file to use as video thumbnail (JPEG or PNG)')
    parser.add_option('', '--playlist', dest='playlist', type="string",
        help='Playlist title (if it does not exist, it will be created)')
    parser.add_option('', '--title-template', dest='title_template',
        type="string", default="{title} [{n}/{total}]", metavar="string",
        help='Template for multiple videos (default: {title} [{n}/{total}])')

    #basic caption option implemented
    parser.add_option('', '--caption-file', dest='caption_file',
        type="string", metavar="FILE",
        help='Caption srt file')   
    parser.add_option('', '--caption-lang', dest='caption_lang',
        type="string", default="en", metavar="string",
        help='Default language the for caption is en (ISO 639-1: en | fr | de | ...)')
    parser.add_option('', '--caption-name', dest='caption_name',
        type="string", default="Uplodaded from youtube-upload", metavar="string",
        help='Default name for the caption "Uplodaded from youtube-upload"')
    parser.add_option('', '--caption-asdraft', dest='caption_status',
        type="string", default="no", metavar="string",
        help='As default the caption is uploaded and published, by using "yes" in this option the caption will be uplodade as draft') 

    # Authentication
    parser.add_option('', '--client-secrets', dest='client_secrets',
        type="string", help='Client secrets JSON file')
    parser.add_option('', '--credentials-file', dest='credentials_file',
        type="string", help='Credentials JSON file')
    parser.add_option('', '--auth-browser', dest='auth_browser', action='store_true',
        help='Open a GUI browser to authenticate if required')


    #Additional options
    parser.add_option('', '--chunksize', dest='chunksize', type="int", 
        default = 1024*1024*8, help='Update file chunksize')
    parser.add_option('', '--open-link', dest='open_link', action='store_true',
        help='Opens a url in a web browser to display the uploaded video')

    options, args = parser.parse_args(arguments)
    
    if options.description_file is not None and os.path.exists(options.description_file):
        with open(options.description_file, encoding="utf-8") as file:
            options.description = file.read()

    try:
        print(1,args,1)
        if options.caption_file != None and len(args) > 1:
            print("Multiple uploads are not supported when uploading a caption file.")
            exit(1)
        
        run_main(parser, options, args)
        
    except googleapiclient.errors.HttpError as error:
        response = bytes.decode(error.content, encoding=lib.get_encoding()).strip()
        raise RequestError("Server response: {0}".format(response))

def run():
    sys.exit(lib.catch_exceptions(EXIT_CODES, main, sys.argv[1:]))
  
if __name__ == '__main__':
    run()