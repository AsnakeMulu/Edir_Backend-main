from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime


class CustomDailyFileHandler(TimedRotatingFileHandler):

    def rotation_filename(self, default_name):
        base, ext = os.path.splitext(self.baseFilename)
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{base}_{date_str}{ext}"
