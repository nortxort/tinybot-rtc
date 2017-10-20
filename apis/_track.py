import time


class Track:
    def __init__(self, video_id='', video_time=0, video_title='', image='', owner=None, video_type='youTube'):
        self.id = video_id
        self.time = video_time
        self.title = video_title
        self.image = image
        self.owner = owner
        self.type = video_type
        self.rq_time = time.time()
        self.start = 0
        self.pause = 0
