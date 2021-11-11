# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import os
from textwrap import dedent
from pathlib import Path
from typing import Optional, Tuple

from ..cache import BaseCache, CacheInterface
from ..controller import CacheController
from ..serialize import Serializer
from ..compat import HTTPResponse


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


def _get_dir_lock_class(use_dir_lock, lock_class):
    if use_dir_lock is not None and lock_class is not None:
        raise ValueError("Cannot use use_dir_lock and lock_class together")

    try:
        from lockfile import LockFile
        from lockfile.mkdirlockfile import MkdirLockFile
    except ImportError:
        notice = dedent(
            """
        NOTE: In order to use the FileCache you must have
        lockfile installed. You can install it via pip:
          pip install lockfile
        """
        )
        raise ImportError(notice)

    else:
        if use_dir_lock:
            lock_class = MkdirLockFile

        elif lock_class is None:
            lock_class = LockFile
    return lock_class


class FileCache(BaseCache):
    """
    A legacy cache for backwards compatibility.  You should use
    ``StreamingFileCache`` instead in new code.
    """
    def __init__(
        self,
        directory,
        forever=False,
        filemode=0o0600,
        dirmode=0o0700,
        use_dir_lock=None,
        lock_class=None,
    ):
        lock_class = _get_dir_lock_class(use_dir_lock, lock_class)
        self.directory = directory
        self.forever = forever
        self.filemode = filemode
        self.dirmode = dirmode
        self.lock_class = lock_class

    @staticmethod
    def encode(x):
        return hashlib.sha224(x.encode()).hexdigest()

    def _fn(self, name):
        # NOTE: This method should not change as some may depend on it.
        #       See: https://github.com/ionrock/cachecontrol/issues/63
        hashed = self.encode(name)
        parts = list(hashed[:5]) + [hashed]
        return os.path.join(self.directory, *parts)

    def get(self, key):
        name = self._fn(key)
        try:
            with open(name, "rb") as fh:
                return fh.read()

        except FileNotFoundError:
            return None

    def set(self, key, value, expires=None):
        name = self._fn(key)

        # Make sure the directory exists
        try:
            os.makedirs(os.path.dirname(name), self.dirmode)
        except (IOError, OSError):
            pass

        with self.lock_class(name) as lock:
            # Write our actual file
            with _secure_open_write(lock.path, self.filemode) as fh:
                fh.write(value)

    def delete(self, key):
        name = self._fn(key)
        if not self.forever:
            try:
                os.remove(name)
            except FileNotFoundError:
                pass


def url_to_file_path(url, filecache: FileCache):
    """Return the file cache path based on the URL.

    This does not ensure the file exists!
    """
    assert isinstance(filecache, FileCache)
    key = CacheController.cache_url(url)
    return filecache._fn(key)


class StreamingFileCache(CacheInterface):
    """
    A file-based cache that uses significantly less memory than ``FileCache``.
    """
    def __init__(
        self,
        directory,
        forever=False,
        filemode=0o0600,
        dirmode=0o0700,
        use_dir_lock=None,
        lock_class=None,
    ):
        lock_class = _get_dir_lock_class(use_dir_lock, lock_class)
        self._directory = Path(directory)
        self._forever = forever
        self._filemode = filemode
        self._dirmode = dirmode
        self._lock_class = lock_class

    def _filenames(self, name: str) -> Tuple[Path, Path]:
        """Returns (metadata path, body path)."""
        hashed = hashlib.sha224(name.encode("utf-8")).hexdigest()
        parts = list(hashed[:5]) + [hashed]
        base_path = self._directory / Path(*parts)
        return base_path.with_suffix(".metadata"), base_path.with_suffix(".body")

    def get_as_file(self, key: str, request, serializer: Serializer) -> HTTPResponse:
        """
        Return tuple of (encoded-metadata file-like, body file-like).
        """
        metadata_path, body_path = self._filenames(key)
        return serializer.loads_separate(request, metadata_path.read_bytes(), body_path.open("rb"))

    def set_from_file(
        self,
        key: str,
        metadata_value: bytes,
        body_path: Path,
        expires: Optional[int] = None,
    ):
        """
        Store a cache entry, with metadata and body being passed in separately,
        the latter as a path to a file.  The metadata is encoded.  Expiration
        time is a duration (from the present moment) in seconds.
        """
        metadata_path, new_body_path = self._filenames(key)

        # Make sure the directories exist:
        metadata_path.parent.mkdir(self._dirmode, parents=True, exists_ok=True)

        with self._lock_class(str(metadata_path)):
            with self._lock_class(str(body_path)):
                with _secure_open_write(metadata_path.path, self._filemode) as f:
                    f.write(metadata_value)
                body_path.rename(new_body_path)
                body_path.chmod(self._filemode)

    def delete(self, key: str):
        """
        Delete an entry.
        """
        if not self._forever:
            metadata_path, new_body_path = self._filenames(key)
            try:
                metadata_path.remove()
            except FileNotFoundError:
                pass
            try:
                new_body_path.remove()
            except FileNotFoundError:
                pass

    def close(self):
        """
        Close the cache.
        """
        pass
