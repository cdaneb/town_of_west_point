from collections import Counter
from django.utils import timezone
from .models import GameState, Player, Vote, NightAction, ChatMessage
from .role_assignment import assign_roles


def get_game():
    game, _ = GameState.objects.get_or_create(
        id=1,
        defaults={"phase": "LOBBY", "is_active": True}
    )
    return game


def reset_game():
    """Reset the game back to LOBBY state so a new game can be started."""
    game = get_game()
    game.phase = 'LOBBY'
    game.winner = None
    game.phase_started_at = None
    game.phase_ends_at = None
    game.save()
    # Reset all players but keep their accounts
    Player.objects.update(role='', is_alive=True, is_ready=False, votes=0, has_voted=False)
    # Clear game-round data
    Vote.objects.filter(game=game).delete()
    NightAction.objects.filter(game=game).delete()
    ChatMessage.objects.filter(game=game).delete()


def check_for_winner():
    """
    Returns 'Town' if all Mafia are dead, 'Mafia' if Mafia count >= Town count,
    or None if the game should continue.

    Players with blank roles (e.g. before role assignment) are intentionally
    excluded so a blank-role edge case doesn't trigger a false win.
    """
    mafia_alive = Player.objects.filter(is_alive=True, role='Mafia').count()
    town_alive = Player.objects.filter(is_alive=True, role='Town').count()

    # Don't evaluate if no one has roles yet
    if mafia_alive == 0 and town_alive == 0:
        return None

    if mafia_alive == 0:
        return 'Town'
    if mafia_alive >= town_alive:
        return 'Mafia'
    return None


def add_system_message(game, text):
    ChatMessage.objects.create(
        game=game,
        sender=None,
        chat_type='system',
        content=text
    )


def start_phase_timer(game):
    now = timezone.now()
    game.phase_started_at = now

    if game.phase == 'DAY':
        game.phase_ends_at = now + timezone.timedelta(seconds=game.day_length_seconds)
    elif game.phase == 'NIGHT':
        game.phase_ends_at = now + timezone.timedelta(seconds=game.night_length_seconds)
    else:
        game.phase_ends_at = None

    game.save()


def resolve_night():
    game = get_game()

    target_counts = Counter(
        NightAction.objects.filter(game=game).values_list('target_id', flat=True)
    )
    if target_counts:
        target_id, _ = target_counts.most_common(1)[0]
        target = Player.objects.filter(id=target_id, is_alive=True).first()
        if target:
            target.is_alive = False
            target.save()
            add_system_message(game, f"{target.user.username} was killed during the night.")

    NightAction.objects.filter(game=game).delete()


def resolve_day():
    game = get_game()

    target_counts = Counter(
        Vote.objects.filter(game=game).values_list('target_id', flat=True)
    )

    if target_counts:
        most_common = target_counts.most_common()
        highest = most_common[0][1]
        top_targets = [target_id for target_id, count in most_common if count == highest]

        if len(top_targets) == 1:
            target = Player.objects.filter(id=top_targets[0], is_alive=True).first()
            if target:
                target.is_alive = False
                target.save()
                add_system_message(game, f"{target.user.username} was voted out.")
        else:
            add_system_message(game, "Day vote ended in a tie. No one was eliminated.")

    Vote.objects.filter(game=game).delete()


def advance_game_phase():
    game = get_game()

    if game.phase == 'LOBBY':
        assign_roles()

        # Safety: need at least 1 Mafia and 1 Town for a valid game
        town_count = Player.objects.filter(role='Town').count()
        mafia_count = Player.objects.filter(role='Mafia').count()
        if town_count == 0 or mafia_count == 0:
            # Roll back roles so the lobby stays open
            Player.objects.update(role='', is_alive=True, is_ready=False)
            add_system_message(game, "Not enough players for a valid game. Need at least 1 Mafia and 1 Town (min 2 players).")
            return

        game.phase = 'NIGHT'
        game.winner = None
        game.save()
        add_system_message(game, "The game has started. Night begins.")
        start_phase_timer(game)
        return

    if game.phase == 'NIGHT':
        resolve_night()
        winner = check_for_winner()
        if winner:
            game.phase = 'GAME_OVER'
            game.winner = winner
            game.phase_started_at = None
            game.phase_ends_at = None
            game.save()
            add_system_message(game, f"{winner} wins.")
            return

        game.phase = 'DAY'
        game.save()
        add_system_message(game, "Day has begun.")
        start_phase_timer(game)
        return

    if game.phase == 'DAY':
        resolve_day()
        winner = check_for_winner()
        if winner:
            game.phase = 'GAME_OVER'
            game.winner = winner
            game.phase_started_at = None
            game.phase_ends_at = None
            game.save()
            add_system_message(game, f"{winner} wins.")
            return

        game.phase = 'NIGHT'
        game.save()
        add_system_message(game, "Night has begun.")
        start_phase_timer(game)
        return


def advance_if_timer_expired():
    game = get_game()
    if game.phase in ['DAY', 'NIGHT'] and game.phase_ends_at and timezone.now() >= game.phase_ends_at:
        advance_game_phase()