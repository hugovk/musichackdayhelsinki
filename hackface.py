#!/usr/bin/env python
"""
Create a composite face from your most listened bands and artists on Last.fm
"""
import argparse
import glob
import os
import shutil
import sys
import urllib2

# Dependencies:
# imagemagick
# https://github.com/hugovk/pixel-tools/blob/master/pixelator.py
# https://github.com/hugovk/lastfm-tools/blob/master/mylast.py
import cv2.cv as cv
import pyen
import pylast

from mylast import * # Contains API keys and secrets

# Parameters for Haar detection. From the API:
# The default parameters (scale_factor=2, min_neighbors=3, flags=0) are tuned for accurate yet slow object detection. For a faster operation on real video images the settings are:
# scale_factor=1.2, min_neighbors=2, flags=CV_HAAR_DO_CANNY_PRUNING,
# min_size=<minimum possible face size

min_size = (20, 20)
image_scale = 2
haar_scale = 1.2
min_neighbors = 2
haar_flags = cv.CV_HAAR_DO_CANNY_PRUNING


en = pyen.Pyen(ECHO_NEST_API_KEY)

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

def artist_image(artist):
    """
    Return the URL of an artist's image from Echo Nest or Last.fm
    """
    url = None

    if args.imagesource == 'soundcloud':
        artist = artist.item.get_name()
        try:
            response = en.get('artist/images', name=artist)
#             for image in response['images']:
#                 print image['url']
            url = response['images'][0]['url']
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            return None

    else: # lastfm
        try:
            url = artist.item.get_cover_image()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            return None

    print url
    return url


def download(url, dir):
    file_name = url.split('/')[-1]
    file_name = os.path.join(dir, file_name)
    print file_name

    if os.path.exists(file_name):
        print "File already exists, skipping:", file_name
        return file_name
    
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()

#     OpenCV can't handle gif, so convert those to png
    if file_name.lower().endswith(".gif"):
        orig_file_name = file_name
        file_name = file_name + ".png"
        cmd = "convert " + orig_file_name + " " + file_name
        print cmd
        os.system(cmd)
    
    return file_name

def detect_and_save(input_name, cascade, outdir, duplicates=0):
    count = 0
    img = cv.LoadImage(input_name, 1)
    # Allocate temporary images
    gray = cv.CreateImage((img.width,img.height), 8, 1)
    small_img = cv.CreateImage((cv.Round(img.width / image_scale),
        cv.Round (img.height / image_scale)), 8, 1)

    # Convert color input image to grayscale
    cv.CvtColor(img, gray, cv.CV_BGR2GRAY)

    # Scale input image for faster processing
    cv.Resize(gray, small_img, cv.CV_INTER_LINEAR)

    cv.EqualizeHist(small_img, small_img)

    if(cascade):
        t = cv.GetTickCount()
        faces = cv.HaarDetectObjects(small_img, cascade, cv.CreateMemStorage(0),
                                     haar_scale, min_neighbors, haar_flags, min_size)
        t = cv.GetTickCount() - t
        print "detection time = %gms" % (t/(cv.GetTickFrequency()*1000.))
        if faces:
            for ((x, y, w, h), n) in faces:
                # The input to cv.HaarDetectObjects was resized, so scale the
                # bounding box of each face and convert it to two CvPoints

                w = int(w * image_scale)
                h = int(h * image_scale)
                x = int(x * image_scale)
                y = int(y * image_scale)
                x0,y0,w0,h0 = x,y,w,h
                # print x,y,w,h
                if not args.tight_crop:
                    # Widen box
                    x = int(x - w*0.5)
                    # x = int(x - w)
                    y = int(y - h*0.5)
                    w = int(w * 2)
                    # w = int(w * 3)
                    h = int(h * 2)
                    # h = int(h * 3.5)
                # Validate
                if x < 0: x = 0
                if y < 0: y = 0
                if x + w > img.width: w = img.width - x
                if y + h > img.height: h = img.height - y
                # print x,y,w,h

                # This code draws a box on the original around the detected face
                if args.show:
                    # pt1 = (int(x * image_scale), int(y * image_scale))
                    pt1 = (x0, y0)
                    # pt2 = (int((x + w) * image_scale), int((y + h) * image_scale))
                    pt2 = ((x0 + w0), (y0 + h0))
                    cv.Rectangle(img, pt1, pt2, cv.RGB(255, 0, 0), 3, 8, 0)

                cropped = cv.CreateImage((w, h), img.depth, img.nChannels)
                src_region = cv.GetSubRect(img, (x, y, w, h))
                cv.Copy(src_region, cropped)
                if args.show:
                    cv.ShowImage("result", cropped)
                    cv.WaitKey(0)
                head, tail = os.path.split(input_name)
                outfile = os.path.join(outdir, tail + "_" + str(count) + ".jpg")
                if not os.path.isfile(outfile):
                    print "Save to", outfile
                    cv.SaveImage(outfile, cropped)
                
                # Duplicate files if we care about weights
                for i in range(int(duplicates)):
                    dupename = outfile + "_d" + str(i) + ".jpg"
                    shutil.copy2(outfile, dupename)

                count += 1

    # This code is show/save the original with boxes around detected faces
    if args.show:
        cv.ShowImage("result", img)
        # outfile = os.path.join(outdir, input_name)
        # cv.SaveImage(outfile, img)
    return count



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a composite face from your most listened bands and artists on Last.fm.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-u', '--username', default='hvk',
        help='Last.fm username')
    parser.add_argument('-os', '--outsize', help='Output image size', default="350,450")
    parser.add_argument('-p', '--period', default='overall', choices=('overall', '7day', '1month', '3month', '6month', '12month'),
        help="The time period over which to retrieve top artists for.")
    parser.add_argument('-imgsrc', '--imagesource', default='echonest', choices=('lastfm', 'echonest'),
        help="Data source for images")
    parser.add_argument('-n', '--number', type=int, default=100,
        help="Limit to this number.")
    parser.add_argument('-w', '--weighted', action='store_true',
        help="Weigh images by number of plays (warning: slow)")

    # OpenCV
    parser.add_argument('-c', '--cascade', 
#         default='D:\\temp\\opencv\\data\\haarcascades\\haarcascade_frontalface_alt.xml',
        default='/usr/local/Cellar/opencv/2.4.5/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml',
        help='Haar cascade file')
    parser.add_argument('-t', '--tight_crop', action='store_true',
        help='Crop image tight around detected feature (otherwise a margin is added)')
    parser.add_argument('-s', '--show', action='store_true',
        help='Show detected image with box')
    args = parser.parse_args()

    try: import timing # Optional, http://stackoverflow.com/a/1557906/724176
    except: None
    print args

    outfile = "hackface_" + args.username + "_top" + str(args.number)
    if os.path.exists(outfile):
        sys.exit(Outfile, "already exists, exiting")

    outdir = os.path.join("/tmp/hackface/", args.username)
    facedir = os.path.join(outdir, "faces")
    print outdir
#     remove_dir(outdir)
    remove_dir(facedir)
    create_dirs(outdir)
    create_dirs(facedir)

    user = lastfm_network.get_user(args.username)
    print "Get top artists from Last.fm"
    artists = user.get_top_artists(period=args.period, limit=args.number)
    if len(artists) == 0:
        sys.exit("No artists found")

    cascade = cv.Load(args.cascade)

    total_found = 0
    for i, artist in enumerate(artists):
        print i, artist.item.get_name(), artist.weight
        url = artist_image(artist)
        if not url:
            continue

        filename = None
        try:
            filename = download(url, outdir)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            continue

        if args.show:
            cv.NamedWindow("result", 1)

        try:
            if args.weighted:
                total_found += detect_and_save(filename, cascade, facedir, int(artist.weight))
            else:
                total_found += detect_and_save(filename, cascade, facedir)
        except Exception,e:
            print os.getcwd()
            print "Cannot detect:", file
            print str(e)
            print repr(e)
            continue

        if args.show:
            cv.WaitKey(0)
            cv.DestroyWindow("result")

    print "Total faces found:", total_found
    inspec = os.path.join(facedir, "*.jpg")
    if args.weighted:
        outfile = outfile + "_weighted"
    outfile = outfile + ".jpg"
    
    cmd = "pixelator.py --batch-size auto --inspec \"" + inspec + "\" --normalise " + args.outsize + " --outfile " + outfile
    print cmd
    os.system(cmd)

    # Auto-level to bring out the colours
    cmd = "convert -auto-level " + outfile + " " + outfile
    print cmd
    os.system(cmd)



# End of file
