"""Fetch individual VizWiz images out of the official archives without downloading them.

The image archives are 3.5 GB (val) and 11.3 GB (train). Both training and negative
sampling need a few hundred to a few thousand images, so transferring either archive in
full is absurd. The server supports HTTP range requests, so `zipfile` can read the central
directory and then pull only the members actually wanted.

`lmms-lab/VizWiz-VQA` on Hugging Face is an *evaluation* dataset: it publishes `test` and
`val` only. Anything that needs the 20,523-pair **train** split has to come from here.

    from vizwiz_images import fetch
    fetch('train', ['VizWiz_train_00000000.jpg', ...], Path('images/'))
"""

from __future__ import annotations

import http.client
import io
import urllib.parse
import zipfile
from pathlib import Path

BASE = "https://vizwiz.cs.colorado.edu/VizWiz_final/images"


class HttpRangeFile(io.RawIOBase):
    """A seekable read-only file backed by HTTP range requests.

    `zipfile` needs only seek and read, and the archives are served with
    `Accept-Ranges: bytes`, so the whole file never has to be transferred.

    The connection is held open across reads. An earlier version opened a fresh one per
    read via `urllib` and managed about six images a minute -- TLS setup dominated, since
    each request moves roughly 100 KB. Reuse turned that into about eighty-four.
    """

    def __init__(self, url: str):
        self.url = url
        self._pos = 0
        parts = urllib.parse.urlsplit(url)
        self._host = parts.netloc
        self._path = parts.path + (f"?{parts.query}" if parts.query else "")
        self._connection: http.client.HTTPSConnection | None = None

        response = self._request("HEAD")
        self.size = int(response.headers["Content-Length"])
        response.read()
        if response.headers.get("Accept-Ranges") != "bytes":
            raise SystemExit(f"{url} does not advertise range support; download it instead")

    def _connect(self) -> http.client.HTTPSConnection:
        if self._connection is None:
            self._connection = http.client.HTTPSConnection(self._host, timeout=120)
        return self._connection

    def _request(self, method: str, headers: dict | None = None):
        for attempt in (1, 2):
            try:
                connection = self._connect()
                connection.request(method, self._path, headers=headers or {})
                return connection.getresponse()
            except (http.client.HTTPException, OSError):
                # A kept-alive connection can be closed by the server between reads; drop
                # it and retry once before giving up.
                if self._connection is not None:
                    self._connection.close()
                self._connection = None
                if attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        super().close()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self.size}[whence]
        self._pos = max(0, min(self.size, base + offset))
        return self._pos

    def readinto(self, buffer) -> int:
        if self._pos >= self.size:
            return 0
        end = min(self._pos + len(buffer) - 1, self.size - 1)
        response = self._request("GET", {"Range": f"bytes={self._pos}-{end}"})
        chunk = response.read()
        buffer[: len(chunk)] = chunk
        self._pos += len(chunk)
        return len(chunk)


def fetch(split: str, names, out: Path, zip_path: Path | None = None,
          progress_every: int = 100) -> dict[str, int]:
    """Extract `names` from the `split` archive into `out`. Returns a small tally.

    Files already present are skipped, so an interrupted run resumes rather than
    restarting -- which matters when the alternative is re-fetching thousands of images.
    """
    out.mkdir(parents=True, exist_ok=True)
    wanted = list(names)
    tally = {"written": 0, "skipped": 0, "missing": 0}

    source = zip_path if zip_path else HttpRangeFile(f"{BASE}/{split}.zip")
    handle = source if zip_path else io.BufferedReader(source, buffer_size=1 << 20)

    with zipfile.ZipFile(handle) as archive:
        members = {Path(n).name: n for n in archive.namelist()}
        for name in wanted:
            target = out / name
            if target.exists():
                tally["skipped"] += 1
                continue
            member = members.get(name)
            if member is None:
                tally["missing"] += 1
                continue
            target.write_bytes(archive.read(member))
            tally["written"] += 1
            if progress_every and tally["written"] % progress_every == 0:
                print(f"  {tally['written']} fetched", flush=True)

    return tally
