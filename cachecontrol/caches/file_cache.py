import hashlib
import os
import sys
import warnings

from lockfile import FileLock


def _secure_open_write(filename, fmode):
    # We only want to write to this file, so open it in write only mode
    flags = os.O_WRONLY

    # os.O_CREAT | os.O_EXCL will fail if the file already exists, so we only
    #  will open *new* files.
    # We specify this because we want to ensure that the mode we pass is the
    # mode of the file.
    flags |= os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a symlink that
    # we follow and insecurely open a cache file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # On Windows we'll mark this file as binary
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    # Before we open our file, we want to delete any existing file that is
    # there
    try:
        os.remove(filename)
    except (IOError, OSError):
        # The file must not exist already, so we can just skip ahead to opening
        pass

    # Open our file, the use of os.O_CREAT | os.O_EXCL will ensure that if a
    # race condition happens between the os.remove and this line, that an
    # error will be raised. Because we utilize a lockfile this should only
    # happen if someone is attempting to attack us.
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")
    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise


def warning_on_one_line(message, category, filename, lineno, file=None,
                        line=None):
    return ' %s:%s: %s' % (filename, lineno, message)


class FileCache(object):
    def __init__(self, directory, forever=False, filemode=0o0600,
                 dirmode=0o0700, max_bytes=1000000000):
        self.directory = directory
        self.forever = forever
        self.filemode = filemode
        self.dirmode = dirmode
        self.max_bytes = max_bytes
        self.curr_bytes = 0
        warnings.formatwarning = warning_on_one_line

    @staticmethod
    def encode(x):
        return hashlib.sha224(x.encode()).hexdigest()

    def _fn(self, name):
        hashed = self.encode(name)
        parts = list(hashed[:5]) + [hashed]
        return os.path.join(self.directory, *parts)

    def get(self, key):
        name = self._fn(key)
        if not os.path.exists(name):
            return None

        with open(name, 'rb') as fh:
            return fh.read()

    def set(self, key, value):
        name = self._fn(key)

        new_bytes = sys.getsizeof(value)
        total = (self.curr_bytes + new_bytes)
        if total > self.max_bytes:
            message = "Tried adding %d bytes but %d bytes are currently saved" \
                      " in the cache and the max_bytes is set to %d.\n" % \
                      (new_bytes, self.curr_bytes, self.max_bytes)
            warnings.warn(message)
            return

        # Make sure the directory exists
        try:
            os.makedirs(os.path.dirname(name), self.dirmode)
        except (IOError, OSError):
            pass

        with FileLock(name) as lock:
            # Write our actual file
            with _secure_open_write(lock.path, self.filemode) as fh:
                fh.write(value)
                self.curr_bytes += new_bytes

    def delete(self, key):
        name = self._fn(key)
        value = self.get(key)
        removed_bytes = sys.getsizeof(value)
        if not self.forever:
            os.remove(name)
            self.curr_bytes -= removed_bytes
