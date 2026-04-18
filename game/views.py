from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login as auth_login
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import GameState, Player, Vote, NightAction, ChatMessage
from .phase_change import get_game, advance_game_phase, reset_game


def login_view(request):
    if request.user.is_authenticated:
        return redirect('lobby')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        auth_login(request, form.get_user())
        return redirect('lobby')

    return render(request, 'game/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('lobby')

    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Player.objects.get_or_create(user=user)
        auth_login(request, user)
        return redirect('lobby')

    return render(request, 'game/register.html', {'form': form})


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

    # Minimum 2 ready players required: 1 Mafia + 1 Town.
    # For a fun game recommend 5+. With 2 players Mafia wins after the first night.
    if ready_players < 2:
        return HttpResponseForbidden("At least 2 ready players required for a valid game.")

    advance_game_phase()
    game.refresh_from_db()

    if game.phase == 'LOBBY':
        return HttpResponseForbidden("Game did not leave the lobby.")

    return redirect('game_room')


@login_required
def game_view(request):
    game = get_game()
    player, _ = Player.objects.get_or_create(user=request.user)

    if game.phase == 'LOBBY':
        return redirect('lobby')

    players = Player.objects.all().order_by('user__username')
    public_messages = ChatMessage.objects.filter(
        game=game,
        chat_type__in=['public', 'system']
    ).order_by('created_at')

    mafia_messages = []
    if player.role == 'Mafia':
        mafia_messages = ChatMessage.objects.filter(
            game=game,
            chat_type__in=['mafia', 'system']
        ).order_by('created_at')

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
@require_POST
def end_game_view(request):
    game = get_game()
    if game.phase not in ('DAY', 'NIGHT'):
        return redirect('game_room')

    mafia_alive = Player.objects.filter(is_alive=True, role='Mafia').count()
    town_alive = Player.objects.filter(is_alive=True, role='Town').count()

    game.winner = 'Mafia' if mafia_alive > town_alive else 'Town'
    game.phase = 'GAME_OVER'
    game.phase_ends_at = None
    game.save()

    ChatMessage.objects.create(
        game=game,
        sender=None,
        chat_type='system',
        content=f'The game was ended early. {game.winner} wins!'
    )
    return redirect('game_room')


@login_required
@require_POST
def reset_game_view(request):
    """Reset the game to LOBBY so a new round can be started."""
    reset_game()
    return redirect('lobby')


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