Fork: caption/subtitles support
============
This is a fork from the original [Youtube-upload by tokland ](https://github.com/tokland/youtube-upload), the main reason for this fork's existence is to add suport for captions to be uploaded to youtube alongside the video. If you used the original youtube-upload you'll have to delete your ".youtube-upload-credentials.json" file, as this new version requires more scopes.

The implementation isn't very good and you guys can see I'm not having time to work on it to make it good enough for a pull request, but the changes are functional (kinda). More on how to use ahead v

Introduction
============
_Youtube-upload_ is a command line Python script that uploads videos to Youtube (it should work on any platform -GNU/Linux, BSD, OS X, Windows, ...- that runs Python) using theYoutube [APIv3](https://developers.google.com/youtube/v3/).

Dependencies
============

  * [Python 2.6/2.7/3.x](http://www.python.org).
  * Packages: [google-api-python-client](https://developers.google.com/api-client-library/python), [progressbar2](https://pypi.python.org/pypi/progressbar2) (optional).

Check if your operating system provides those packages (check also those [deb/rpm/mac files](https://github.com/qiuwei/youtube-upload/releases)), otherwise install them with `pip`:

```
$ sudo pip install --upgrade google-api-python-client progressbar2
```

Install
=======
As there are no new releases yet, you'll have to clone the repository:
```
$ git clone https://github.com/evertonstz/youtube-upload.git
$ cd youtube-upload-master
$ sudo python setup.py install
```

  * Or run directly from sources:

```
$ cd youtube-upload-master
$ PYTHONPATH=. python bin/youtube-upload ...
```

Authentication
==============

You'll see that there is no email/password options. Instead, the Youtube API uses [OAuth 2.0](https://developers.google.com/accounts/docs/OAuth2) to authenticate the upload. The first time you try to upload a video, you will be asked to follow a URL in your browser to get an authentication token. If you have multiple channels for the logged in user, you will also be asked to pick which one you want to upload the videos to. You can use multiple credentials, just use the option ```--credentials-file```. Also, check the [token expiration](https://developers.google.com/youtube/v3/) policies.

The package includes a default ```client_secrets.json``` file. If you plan to make a heavy use of the script, please [create and use your own OAuth 2.0 file](https://developers.google.com/youtube/registering_an_application), it's a free service. Steps:

* Go to the Google [console](https://console.developers.google.com/).
* _Create project_.
* Side menu: _APIs & auth_ -> _APIs_
* Top menu: _Enabled API(s)_: Enable all Youtube APIs.
* Side menu: _APIs & auth_ -> _Credentials_.
* _Create a Client ID_: Add credentials -> OAuth 2.0 Client ID -> Other -> Name: youtube-upload -> Create -> OK
* _Download JSON_: Under the section "OAuth 2.0 client IDs". Save the file to your local system. 
* Use this JSON as your credentials file: ```--client-secrets=CLIENT_SECRETS```

About the captions/subtitles
========
When uploading a video with subtitle it'll take more time, beucase the program has to wait for the video to be processed by youtube before uploading the captions, I didn't find a workaround to be able to upload while the vide is being processed, if you have any info please let me know! There are basically no info about this lib online. For now only srt is supported.

* UPLOAD A VIDEO AND A CAPTION: you can specify both a video and a caption file path to send to youtube, you can also specify the name and language of the caption. Example:
```
youtube-upload --caption-file=/foo/bar/caption_folder/my_sub.srt --caption-lang="en" /foo/bar/video_folder/my_video.mkv

#will upload my_video.mkv and my_sub.srt (named "english subtitle") to youtube.
```
* AUTO SEARCH FOR CAPTION: using ```--caption-file="auto"``` the program will try to find a srt with a filename that matches the video's. Both files have to be in the same foder. Example:
```
youtube-upload --caption-file="auto" --caption-lang="en" /foo/bar/video_folder/my_video.mkv

#will upload my_video.mkv to youtube, try to find my_video.srt so it can also be uploaded to youtube as an English captions
```
* MULTIPLE VIDEOS: the videos and captions have to be in the same directory and with the same name (exemple: video_legal.mkv and video_legal.srt, video_chato.mkv and video_chato.srt). Make sure to use ```--caption-file="auto"```. Example:
```
youtube-upload --caption-file="auto" --caption-lang="en" /foo/bar/video_folder/*

#will upload all the videos in the folder to youtube, try to find all srt files with matching names and also upload it to youtube as English captions
```

* All commands available for captions
```
  --caption-file=FILE   Caption srt file
  --caption-lang=string
                        Default language the for caption is en (ISO 639-1: en
                        | fr | de | ...)
  --caption-name=string
                        Default name for the caption is "Uplodaded from youtube-
                        upload"
  --caption-asdraft=string
                        As default the caption is uploaded and published, by
                        using "yes" in this option the caption will be
                        uplodaded as draft
```

Examples
========
* Upload a video:

```
$ youtube-upload --title="A.S. Mutter" anne_sophie_mutter.flv
pxzZ-fYjeYs
```

* Upload a video with extra metadata, with your own client secrets and credentials file, and to a playlist (if not found, it will be created):

```
$ youtube-upload \
  --title="A.S. Mutter" 
  --description="A.S. Mutter plays Beethoven" \
  --category=Music \
  --tags="mutter, beethoven" \
  --recording-date="2011-03-10T15:32:17.0Z" \
  --default-language="en" \
  --default-audio-language="en" \
  --client-secrets=my_client_secrets.json \
  --credentials-file=my_credentials.json \
  --playlist "My favorite music" \
  anne_sophie_mutter.flv
tx2Zb-145Yz
```
*Other extra medata available :* 
 ```
 --privacy (public | unlisted | private)  
 --publish-at (YYYY-MM-DDThh:mm:ss.sZ)  
 --location (latitude=VAL,longitude=VAL[,altitude=VAL])  
 --thumbnail (string)  
 ```

* Upload a video using a browser GUI to authenticate:

```
$ youtube-upload --title="A.S. Mutter" --auth-browser anne_sophie_mutter.flv
```

* Split a video with _ffmpeg_

If your video is too big or too long for Youtube limits, split it before uploading:

```
$ bash examples/split_video_for_youtube.sh video.avi
video.part1.avi
video.part2.avi
video.part3.avi
```
* Use a HTTP proxy

Set environment variables *http_proxy* and *https_proxy*:

```
$ export http_proxy=http://user:password@host:port
$ export https_proxy=$http_proxy
$ youtube-upload ....
```

Get available categories
========================

* Go to the [API Explorer](https://developers.google.com/apis-explorer)
- Search "youtube categories" -> *youtube.videoCategories.list*
- This bring you to [youtube.videoCategories.list service](https://developers.google.com/apis-explorer/#search/youtube%20categories/m/youtube/v3/youtube.videoCategories.list)
- part: `id,snippet`
- regionCode: `es` (2 letter code of your country)
- _Authorize and execute_

And see the JSON response below. Note that categories with the attribute `assignable` equal to `false` cannot be used.

Using `shoogle`:

```
$ shoogle execute --client-secret-file client_secret.json \
                  youtube:v3.videoCategories.list <(echo '{"part": "id,snippet", "regionCode": "es"}')  | 
    jq ".items[] | select(.snippet.assignable) | {id: .id, title: .snippet.title}"
```

Notes for developers
====================

* Main logic of the upload: [main.py](youtube_upload/main.py) (function ```upload_video```).
* Check the [Youtube Data API](https://developers.google.com/youtube/v3/docs/).
* Some Youtube API [examples](https://github.com/youtube/api-samples/tree/master/python) provided by Google.

Alternatives
============

* [shoogle](https://github.com/tokland/shoogle) can send requests to any Google API service, so it can be used not only to upload videos, but also to perform any operation regarding the Youtube API.

* [youtubeuploader](https://github.com/porjo/youtubeuploader) uploads videos to Youtube from local disk or from the web. It also provides rate-limited uploads.

More
====

* License: [GNU/GPLv3](http://www.gnu.org/licenses/gpl.html).

Feedback
========

* [Donations](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=pyarnau%40gmail%2ecom&lc=US&item_name=youtube%2dupload&no_note=0&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHostedGuest).
* If you find a bug, [open an issue](https://github.com/tokland/youtube-upload/issues).
* If you want a new feature to be added, you'll have to send a pull request (or find a programmer to do it for you), currently I am not adding new features.
