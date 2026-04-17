from django.contrib import admin
from .models import GameState, Player, Vote, NightAction, ChatMessage
from .phase_change import advance_game_phase


@admin.action(description="Move to Next Phase")
def move_phase(modeladmin, request, queryset):
    advance_game_phase()


@admin.action(description="Reset game to lobby")
def reset_to_lobby(modeladmin, request, queryset):
    game = GameState.objects.first()
    if game:
        game.phase = 'LOBBY'
        game.winner = None
        game.phase_started_at = None
        game.phase_ends_at = None
        game.save()
    Player.objects.update(role='', is_alive=True, is_ready=False, votes=0, has_voted=False)
    Vote.objects.all().delete()
    NightAction.objects.all().delete()
    ChatMessage.objects.all().delete()


class GameStateAdmin(admin.ModelAdmin):
    list_display = ['phase', 'winner', 'phase_started_at', 'phase_ends_at']
    actions = [move_phase, reset_to_lobby]


admin.site.register(GameState, GameStateAdmin)
admin.site.register(Player)
admin.site.register(Vote)
admin.site.register(NightAction)
admin.site.register(ChatMessage)