from django.core.management.base import BaseCommand
import time
from game.phase_change import advance_if_timer_expired

class Command(BaseCommand):
    help = "Runs the Mafia game phase timer loop"

    def handle(self, *args, **options):
        self.stdout.write("Starting game timer loop...")
        while True:
            advance_if_timer_expired()
            time.sleep(1)