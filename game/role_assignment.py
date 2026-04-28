import random
from .models import Player


def assign_roles():
    players = list(Player.objects.all())
    random.shuffle(players)

    if not players:
        return

    num_mafia = max(1, len(players) // 4)

    for i, player in enumerate(players):
        player.role = 'Mafia' if i < num_mafia else 'Town'
        player.is_alive = True
        player.is_ready = False
        player.votes = 0
        player.has_voted = False
        player.save()