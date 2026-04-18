from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.db.models import Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import GameState, Player, Vote, NightAction, ChatMessage
from .phase_change import get_game, advance_game_phase


def login_view(request):
    if request.user.is_authenticated:
        return redirect('lobby')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        auth_login(request, form.get_user())
        return redirect('lobby')

    return render(request, 'game/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def lobby_view(request):
    game = get_game()
    player, _ = Player.objects.get_or_create(user=request.user)

    players = Player.objects.all().order_by('joined_at')
    return render(request, 'game/lobby.html', {
        'game': game,
        'player': player,
        'players': players,
    })


@login_required
@require_POST
def toggle_ready(request):
    player, _ = Player.objects.get_or_create(user=request.user)
    player.is_ready = not player.is_ready
    player.save()
    return redirect('lobby')


@login_required
@require_POST
def start_game(request):
    game = get_game()
    ready_players = Player.objects.filter(is_ready=True).count()

    if game.phase != 'LOBBY':
        return redirect('game_room')

    # use 1 for solo testing, change back to 4 later
    if ready_players < 1:
        return HttpResponseForbidden("At least 1 ready player required.")

    advance_game_phase()
    game.refresh_from_db()

    if game.phase == 'LOBBY':
        return HttpResponseForbidden("Game did not leave the lobby.")

    return redirect('/game/')


@login_required
def game_view(request):
    game = get_game()
    player, _ = Player.objects.get_or_create(user=request.user)

    if game.phase == 'LOBBY':
        return redirect('lobby')

    players = Player.objects.all().order_by('user__username')
    public_messages = ChatMessage.objects.filter(game=game, chat_type__in=['public', 'system']).order_by('created_at')
    mafia_messages = ChatMessage.objects.filter(game=game, chat_type__in=['mafia', 'system']).order_by('created_at') if player.role == 'Mafia' else []

    return render(request, 'game/game.html', {
        'game': game,
        'player': player,
        'players': players,
        'public_messages': public_messages,
        'mafia_messages': mafia_messages,
    })


@login_required
@require_POST
def cast_vote(request, target_id):
    game = get_game()
    player = Player.objects.get(user=request.user)

    if game.phase != 'DAY' or not player.is_alive:
        return HttpResponseForbidden("Voting is not allowed right now.")

    target = Player.objects.filter(id=target_id, is_alive=True).first()
    if not target or target == player:
        return HttpResponseForbidden("Invalid vote target.")

    Vote.objects.update_or_create(
        game=game,
        voter=player,
        defaults={'target': target}
    )
    return redirect('game_room')


@login_required
@require_POST
def cast_night_action(request, target_id):
    game = get_game()
    player = Player.objects.get(user=request.user)

    if game.phase != 'NIGHT' or not player.is_alive or player.role != 'Mafia':
        return HttpResponseForbidden("Night action is not allowed right now.")

    target = Player.objects.filter(id=target_id, is_alive=True, role='Town').first()
    if not target:
        return HttpResponseForbidden("Invalid target.")

    NightAction.objects.update_or_create(
        game=game,
        mafia_player=player,
        defaults={'target': target}
    )
    return redirect('game_room')


@login_required
def game_state_api(request):
    game = get_game()
    players = Player.objects.all().order_by('user__username')

    return JsonResponse({
        'phase': game.phase,
        'winner': game.winner,
        'seconds_remaining': game.seconds_remaining(),
        'players': [
            {
                'username': p.user.username,
                'is_alive': p.is_alive,
                'role': p.role if request.user == p.user or game.phase == 'GAME_OVER' else None,
            }
            for p in players
        ]
    })