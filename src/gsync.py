'''
Created on 27 Mar 2011

@author: gareth

Modded FROM: http://talk.maemo.org/archive/index.php/t-27504.html

FIXME: Security improvements
find system way of SAFE storing / retrieving credentials
mangle the username using md5 / sha / whatever when creating the top folder

TODO: Script improvements

Limit downloads by:
* Only get images with highest rating
* Start with the latest uploads and work backwards
* Be able to pick which albums to sync
** devise some kind of scheme to do this!!!

Limit cache dir to certain size
* by limiting downloads (see above)
* Use Max screen width / height as a hint for resizing
* Deleting oldest files (off disk, not picasaweb)

TODO: DB indexing
* Use SQLite to 
* index what's been downloaded and help skip re-doing it
* store comments to display on the saver

TODO: Other feeds
* People you follow, friends etc
Commonlise the GetFeatured one! - how to resize them!!!???

'''

from threading import Thread
import gdata.geo
import gdata.media
import gdata.photos.service
import os
import socket
import urllib2


APPNAME = 'pycsync'


# FIXME: find system way of storing / retreiving credentials and replace this crap!
class Logins:
    username = 'joe.mangle'
    email = username + '@gmail.com'
    password = 'ramseystreetrocks'


gd_client = gdata.photos.service.PhotosService()


def GetFeatured(imgmax=None, limit=None):
    """Load the first 100 found and 
    Delete old ones"""
    # TODO: resizing this lot
    uri = 'https://picasaweb.google.com/data/feed/base/featured'
    album_dir = GetCacheDir('featured')
    current_dir = InitSyncDir(album_dir)

#    if not imgmax:
    photos = gd_client.GetFeed(uri)
#    else:
#        photos = gd_client.GetFeed("%s&imgmax=%s" % (album.GetPhotosUri(), imgmax))

    new_files = DownloadPhotos(photos, album_dir, limit=limit)
    RemoveFiles(current_dir - set(new_files), album_dir)


def InitSyncDir(album_dir):
    """ensure the dir exists
    create if not
    return the contents list"""
    if not os.path.exists(album_dir):
        os.makedirs(album_dir)
    return set(os.listdir(album_dir))


def FormatFileName(file_name):
    fn, ext = os.path.splitext(file_name)
    if len(fn) < 2: return ''
    replace = [' ', ';', ':', '"', "'", '!', '?', ',', '.',
               '#', '%', '$', r'/', '\\',
               'http', 'www', 'com']
    for r in replace: fn = fn.replace(r, '')
    if len(fn) > 36: fn = fn[:36]
    return fn + ext


def DoClientLogin():
    """The parameters here will determine what gets downloaded
    if password is not given then only public albums will get downloaded
    """
    gd_client.email = Logins.email
    gd_client.password = Logins.password
    gd_client.source = APPNAME
    gd_client.ProgrammaticLogin()


def sync(username, limit=None, imgmax=None,
         exclusions=['Fireworks', 'Blog', 'Tech']):
    #FIXME: replace the excusions hack with a proper album selection method
    prefix = GetCacheDir(username.text)
    try:
        album_list = gd_client.GetUserFeed(user=username, limit=limit)
        for album in reversed(album_list.entry):
            include = True
            for exclusion in exclusions:
                if exclusion in album.title.text: include = False
            if include:
                sync_album(album, prefix, imgmax)
    except socket.error:
        print 'interwebs is currently down, go make a panad'



def GetFriendFeeds(username, imgmax=None, limit=None):
    """Load the first 100 found and 
    Delete old ones"""
    for friend in gd_client.GetContacts(username).entry:
        prefix = GetCacheDir(friend.title.text)
        uri = friend.GetAlbumsUri()
        album_list = gd_client.GetFeed(uri)
        for album in album_list.entry:
            sync_album(album, prefix, imgmax)


def GetAlbumDir(album, prefix):
    if not os.path.isdir(prefix):
        print "Creating directory %s" % (prefix)
        os.makedirs(prefix)
    album_dir = os.path.join(prefix, "%d" % (album.timestamp.datetime().year),
                             "%d-%02d-%02d %s" % (album.timestamp.datetime().year,
                                                  album.timestamp.datetime().month,
                                                  album.timestamp.datetime().day,
                                                  album.title.text))
    return album_dir.replace(' ', '_')


def sync_album(album, prefix, imgmax):
    """
    download the album photos to the dir under prefix
    @param album: the gdata album object
    @param prefix: the root folder where the albums will exist
    @param imgmax: used to resize photos before downloading
    """
    album_dir = GetAlbumDir(album, prefix)
    InitSyncDir(album_dir)

    if not imgmax:
        photos = gd_client.GetFeed(album.GetPhotosUri())
    else:
        photos = gd_client.GetFeed("%s&imgmax=%s" % (album.GetPhotosUri(), imgmax))

    DownloadPhotos(photos, album_dir)


def RemoveFiles(files, album_dir):
    for name in files:
        print "Deleting unused file %s" % (os.path.join(album_dir, name))
        os.remove(os.path.join(album_dir, name))


def DownloadPhotos(photos, album_dir, limit=None):
    """download any new pictures and return the list of them
    Counter is required for the featured feed which doesn't seem to like
    it in the uri"""
    new_files = []
    i = 0
    for photo in photos.entry:
        fn = FormatFileName(photo.title.text)
        if not os.path.exists(os.path.join(album_dir, fn)):
            print "Downloading: %s -> %s" % (photo.content.src, os.path.join(album_dir, fn))
            download(photo.content.src, os.path.join(album_dir, fn))
            new_files.append(fn)
            i += 1
        if limit and i > limit: break
    return new_files


def download(url, destination):
    out = open(destination, 'w')
    out.write(urllib2.urlopen(url).read())


def GetCacheDir(username):
    """where to store the photos"""
#    TODO: mangle the username
    homedir = os.path.expanduser('~')
    return os.path.join(homedir, 'pwebc', username)


def main(own=True, friends=True, featured=False):
    DoClientLogin()
    if own:
        Thread(target=sync,
        args=(Logins.username, GetCacheDir(Logins.username)),
        kwargs=dict(imgmax='800u')
        ).start()

    if friends:
        Thread(target=GetFriendFeeds,
               args=(Logins.username,),
               kwargs=dict(imgmax='800u', limit=100)
        ).start()

    if featured:
        Thread(target=GetFeatured,
        kwargs=dict(imgmax='800u', limit=100)
        ).start()


if __name__ == '__main__':
    main(True, False, False)
