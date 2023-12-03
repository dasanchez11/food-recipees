"""
Django command for waiting for DB.
"""
import time
from psycopg2 import OperationalError as psycopg2Error
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django command to wait for database"""

    def handle(self, *args, **options):
        """Entry point from command"""
        self.stdout.write("Wai ting for database ...")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=["default"])
                db_up = True
            except (psycopg2Error, OperationalError):
                self.stdout.write("Database unavailable, waitin 1 second")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available"))
