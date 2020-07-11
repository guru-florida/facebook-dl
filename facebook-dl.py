#!/usr/bin/env python3
#
# pylint: disable=missing-docstring,trailing-whitespace,invalid-name
#
# By Siddharth Dushantha (sdushantha) 2020
#
# Notice: If you are on Windows, the output of this script might
#         look a little messy and that is because command prompt
#         does not support escape sequences.
#

import re
import sys
import os
import argparse
import requests

# This magic spell lets me erase the current line.
# I can use this to show for example "Downloading..."
# and then "Downloaded" on the line where
# "Downloading..." was.
ERASE_LINE = '\e[2K'

class FaceBookVideo:
    cookies: dict
    meta: dict = {}
    url: str
    type: str
    width: int
    height: int

    outputFilename: str

    def __init__(self, cookies: dict):
        self.cookies = cookies

    # parse a collection of videos for all video links
    def videosBy(self, url: str):
        # request the index for this video
        request = requests.get(url, cookies=self.cookies)

        # parse index metadata
        videos = {}
        links = re.findall(r"<a\s+href=\"([^\"]*)\"\s+aria-label=\"([^\"]*)\"", request.text)
        for link in links:
            # capture 0 is the meta property name and 1 is the property value
            videos[link[0]] = link[1]

        return videos

    def query(self, url: str):
        # clear video specific members
        meta = {}
        type = None
        width = None
        height = None

        if url[0]=='/':
            url = "https://www.facebook.com" + url;

        # request the index for this video
        request = requests.get(url, cookies=self.cookies)

        # parse index metadata
        meta = re.findall(r"<meta\s+property=\"([^\"]*)\"\s+content=\"([^\"]*)\"\s*/>", request.text)
        for prop in meta:
            # capture 0 is the meta property name and 1 is the property value
            self.meta[prop[0]] = prop[1]

        # determine what the video url is from some possibilities
        # we do it with if/else so we can keep priority
        if 'og:video' in self.meta:
            self.url = self.meta['og:video']
        elif 'og:video:url' in self.meta:
            self.url = self.meta['og:video:url']
        elif 'og:video:secure_url' in self.meta:
            self.url = self.meta['og:video:secure_url']
        else:
            print("Cannot determine the video URL from meta: ", self.meta)
            return False

        # parse other metadata we want
        for k, v in self.meta.items():
            if k == 'og:video:width':
                self.width = v
            if k == 'og:video:height':
                self.height = v
            if k == 'og:video:type':
                self.type = v

        # now convert the &amp; in the URL
        self.url = self.url.replace('&amp;', '&')

        # build an output filename
        base_fn = str(re.findall(r"videos/([^?\"]+)", request.text)[-1].replace("/", "").replace(".","-"))
        self.outputFilename = f"{base_fn}x{self.height}.mp4"

        return True

    def download(self, outputFilename=None):
        if outputFilename:
            # use filename given to us
            self.outputFilename = outputFilename

        # fn = re.findall(f"{'sd_src' if args.resolution == 'sd' else 'hd_src'}:\"(.+?)\"", request.text)[0]
        request = requests.get(self.url, cookies=self.cookies)

        # Write the content to the file
        with open(self.outputFilename, "wb") as f:
            f.write(request.content)


# parse cookies as semi-colon separated string
# This is what we pull from Chrome network inspector (Request Headers cookies value) if the videos are not public
# and require a login to access. (You must login under an account that can view the videos and copy your cookies)
def parseCookies(cookiesText: str):
    cookies_parsed = re.findall(r"([a-zA-Z\-_]+)=([^;]*);", cookiesText)
    cookies = {}
    for c in cookies_parsed:
        cookies[c[0]] = c[1]
    return cookies


def main():
    parser = argparse.ArgumentParser(description="Download videos from facebook from your terminal")

    parser.add_argument('url', action="store")
    parser.add_argument('resolution', action="store", nargs="?")

    args = parser.parse_args()

    # Videos marked private may require you to be logged into your account
    # You can use your browser's Network Inspector or Cookies tab to extract your logged in authentication tokens
    # stored in the 'c_user' and 'xs' variables and store in a file as name-value (w/semicolon):
    # c_user=<value>;
    # xs=<value>;
    # You can copy all your cookies in there, it doesnt matter, but only these two should be required.
    cookiefile = None
    if os.path.isfile("cookies"):
        cookiefile = "cookies"
    elif os.path.isfile(os.path.expanduser("~/.facebook-cookies")):
        cookiefile = os.path.expanduser("~/.facebook-cookies")

    cookies = None
    if cookiefile:
        # read the cookies and parse
        print("using facebook cookies from file", cookiefile)
        with open(cookiefile, "r") as f:
            cookies = parseCookies(f.read())

    # create video object of our desired Video
    video = FaceBookVideo(cookies)

    if 'videos_by' in args.url:
        urls = video.videosBy(args.url)
    else:
        urls = {args.url: ''}

    for url,label in urls.items():
        print(f"{url}:     {label}")

        if video.query(url):
            print("   \033[92m✔\033[0m Fetched video metadata ")

            try:
                video.download()
            except IndexError as ie:
                print("   Video could not be downloaded: " + str(ie))
                sys.exit()

            print(f"   \033[92m✔\033[0m Downloaded video {video.outputFilename}")

if __name__ == "__main__":
    main()
