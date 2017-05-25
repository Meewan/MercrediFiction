# API management
TOOT_LIMIT = "40"
GET_TAG = "https://%(domain)s/api/v1/timelines/tag/%(tag)s?limit=" + TOOT_LIMIT
MAX_ID = "&max_id=%(max_id)s"
SINCE_ID = "&since_id=%(since_id)s"
