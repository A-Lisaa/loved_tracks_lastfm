import attr


@attr.define(hash=True)
class TrackData:
    artist: str
    title: str

@attr.define(hash=True)
class LocalTrackData(TrackData):
    path: str
    filename: str

@attr.define(hash=True)
class InternetTrackData(TrackData):
    artist_url: str
    track_url: str
