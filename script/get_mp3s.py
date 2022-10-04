import re
import sqlite3
import shutil
import unicodedata
from pathlib import Path

def to_path_name(name: str):
    return re.sub(r"\s", "-", re.sub(r"[^a-z0-9\s_\-?]", "", name.lower()))

def main():
    # Get Podcasts app base path.
    candidates = list(Path("~/Library/Group Containers/").expanduser().glob("*.apple.podcasts"))
    if len(candidates) != 1:
        paths = "\n\t".join([str(c) for c in candidates])
        raise RuntimeError(f"Cannot find Podcasts path. Zero or Multiple paths found:\n\t{paths}")
    base_path = candidates[0]
    mp3_path = base_path / "Library" / "cache"

    # Get a list of local MP3 files.
    files = {p.name.replace(".mp3", ""): p for p in mp3_path.glob("*.mp3")}

    # Connect to the metadata database
    db = sqlite3.connect(str(base_path / "Documents" / "MTLibrary.sqlite"))
    cur = db.cursor()

    # Get the names of the podcasts for the available MP3s
    cur.execute(f"""
        SELECT DISTINCT ZMTPODCAST.ZTITLE, ZMTPODCAST.ZUUID
        FROM ZMTEPISODE
        LEFT JOIN ZMTPODCAST ON ZMTEPISODE.ZPODCASTUUID = ZMTPODCAST.ZUUID
        WHERE ZMTEPISODE.ZUUID IN ({",".join(["?"] * len(files))})
        ORDER BY ZMTPODCAST.ZTITLE;
        """,
        list(files.keys()),
    )
    podcasts = [
        (unicodedata.normalize("NFKD", x[0]).encode("ascii", "ignore").decode(), x[1])
        for x in cur.fetchall()
    ]

    # Ask user which podcast to export
    num = None
    while num is None:
        print("\n".join([f"{i}) {n[0]}" for i, n in enumerate(podcasts, 1)]))
        user_response = input("Which podcast would you like to export? (Enter a number):")
        try:
            num = int(user_response) - 1
        except ValueError:
            pass
    podcast_name, podcast_uuid = podcasts[num]

    cur.execute(f"""
        SELECT ZTITLE, ZSEASONNUMBER, ZEPISODENUMBER, ZUUID
        FROM ZMTEPISODE
        WHERE ZPODCASTUUID = ? AND ZUUID IN ({",".join(["?"] * len(files))})
        ORDER BY ZSEASONNUMBER, ZEPISODENUMBER;
        """,
        [podcast_uuid] + list(files.keys()),
    )
    metadata = [
        (unicodedata.normalize("NFKD", x[0]).encode("ascii", "ignore").decode(), *x[1:])
        for x in cur.fetchall()
    ]

    podcast_path_name = to_path_name(re.sub(r"[^A-z0-9 \-]", "", podcast_name))
    outpath = parent = Path(__file__).resolve().parent / "data" / "podcasts" / podcast_path_name
    if not outpath.exists():
        outpath.mkdir(parents=True)
    for title, season, episode, uuid in metadata:
        if ":" in title:
            title = title.split(":")[-1].strip()
        filename = "_".join([str(x) if x else "?" for x in (podcast_path_name, season, episode, title)])
        shutil.copyfile(mp3_path / f"{uuid}.mp3", outpath / f"{to_path_name(filename)}.mp3")


if __name__ == "__main__":
    main()
