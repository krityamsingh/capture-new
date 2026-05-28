import os
from dotenv import load_dotenv
load_dotenv()

OWNER_IDS = [6228788487, 8496760733, 7878477646, 7976292835, 6118760915]
owner_id  = "6118760915"

TOKEN      = os.environ.get("BOT_TOKEN",   "7686672468:AAFhqx5FomKltXmGGv-5K056v9jQx1psLe4")
api_id     = int(os.environ.get("API_ID",  "20457610"))
api_hash   = os.environ.get("API_HASH",    "b7de0dfecd19375d3f84dbedaeb92537")
MONGO_URL  = os.environ.get("MONGO_URL",   "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0")

SUPPORT_CHAT      = "Devince_Support"
UPDATE_CHAT       = "IndianHelpIine"
BOT_USERNAME      = "CaptureCharacterBot"

CHARA_CHANNEL_ID  = -1002672414862
GROUP_ID          = "-1002313549356"
SUPPORT_GROUP_ID  = "-1002313549356"
SUPPORT_GROUP     = "-1002313549356"
UPDATE_CHANNEL    = "-1003430763556"

LOG_CHAT_ID       = "-1003695209406"
JOINLOGS          = "-1003248939428"
LEAVELOGS         = "-1003248939428"
log_channel       = "-1003248939428"

PHOTO_URL         = ["https://files.catbox.moe/oai7m9.mp4"]
DATABASE_NAME     = "Capture_database"
