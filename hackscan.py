#!/usr/bin/env python
"""
TODO
"""
import argparse
import glob
import os
import shutil
import urllib2

# Dependencies:
# ffmpeg
# slitscan.py # https://github.com/hugovk/pixel-tools/blob/master/slitscan.py
# pyen
import pafy

# Get yours from https://developer.echonest.com/account/profile
ECHO_NEST_API_KEY = "TODO_FILL_YOURS_IN_HERE"

def remove_dir(dir):
    print "Remove dir:", dir
    try:
        shutil.rmtree(dir)
    except:
        pass

def create_dirs(dir):
    print "Create dir:", dir
    import os
    import shutil
    if not os.path.isdir(dir):
        os.makedirs(dir)


def filename_no_ext(filename):
    return os.path.splitext(filename)[0]

def artist_video(artist):
    """
    Return the URL of an artist's video from Echo Nest
    """
    url = None

    import pyen
    en = pyen.Pyen(ECHO_NEST_API_KEY)

    try:
        response = en.get('artist/video', name=artist)
#             for video in response['videos']:
#                 print image['url']
        url = response['video'][0]['url']
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        return None

    print url
    return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TODO.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-a', '--artist',
        help='Artist name')
    parser.add_argument('-u', '--url', 
        help='Or YouTube URL')

    parser.add_argument('-r', '--framerate', metavar='fps',
         default=25, type=int,
        help='Framerate')

    parser.add_argument('-g', '--greedy', action='store_true',
        help="Make output video as wide as there are frames (warning: super slow!). Otherwise width is same as input video")
    parser.add_argument('-o', '--outfile', 
        default='hackscan',
        help='Prefix for output filename')

    args = parser.parse_args()

    try: import timing # Optional, http://stackoverflow.com/a/1557906/724176
    except: None
    print args

    if args.url:
        url = args.url
    elif args.artist:
        url = artist_video(args.artist)
        if not args.outfile:
            args.outfile = args.artist
    else:
        sys.exit("Please give an artist name or YouTube URL")
    
    # Get video info from YouTube
    video = pafy.new(url)
    print video.title
    
    # Only the best!
    best = video.getbest()

    # But let's see if there's something a bit smaller...
    for s in video.streams:
        if "640x" in s.resolution:
            best = s
    
    print best.resolution, best.extension
    
    print video
    
    # Download the best
    original_video = args.outfile + "." + best.extension
    print "Downloading video to", original_video
    original_video = best.download(filepath=original_video)
    
    # Create temp dir for frames
    tempdir = os.path.join("/tmp", args.outfile, "frames")
    print "Temp dir:", tempdir
    remove_dir(tempdir)
    create_dirs(tempdir)
    
    # Split into frames
    output = os.path.join(tempdir, "%6d.jpg")
    cmd = "ffmpeg -i " + original_video + " -r " + str(args.framerate) + " -q:v 1 " + output
    print cmd
    os.system(cmd)
    
    # Slitscan
    inspec = os.path.join(tempdir, "*.jpg")
    cmd = 'slitscan.py -i "' + inspec + '" --supercombo'
    print cmd
    os.system(cmd)

    # Slitscan all
    slitdir = os.path.join("/tmp", args.outfile, "slitscans")
    print "Slitscan tempdir:", slitdir
    remove_dir(slitdir)
    create_dirs(slitdir)
    cmd = 'slitscan.py -i "' + inspec + '" --mode all --keepfree 30 --outfile ' + slitdir + "/out"  # --hack 70"
    if args.greedy:
        cmd += " --greedy"
    print cmd
    os.system(cmd)

    # Make a new video
    inspec = os.path.join(slitdir, "*.jpg")
    silent_remix_video = args.outfile + "2.mp4"
    cmd = "ffmpeg -y -f image2 -pattern_type glob -r " + str(args.framerate) + " -i '" + inspec + "' -c:v libx264 " + silent_remix_video
    print cmd
    os.system(cmd)

    # Add back audio (from original_video) and that's a wrap!
    noisy_remix_video = args.outfile + "3.mp4"
    cmd = "ffmpeg -y -i " + silent_remix_video + " -i " + original_video + ' -map 0:v:0 -map 1:a:0 -codec copy -shortest     -af "afade=t=out:st=3:30:d=2" ' + noisy_remix_video
    print cmd
    os.system(cmd)
    

# End of file
