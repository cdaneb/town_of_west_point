from django.test import TestCase

# Create your tests here.
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from game.models import GameState, Player, Vote, NightAction, ChatMessage


@pytest.mark.django_db
class TestMafiaMechanics:

    def test_seconds_remaining_logic(self):
        """
        Tests the 'seconds_remaining' method in GameState.
        Ensures the timer counts down correctly and never returns negative numbers.
        """
        from django.utils import timezone
        from datetime import timedelta

        # 1. Setup: Create a game ending 60 seconds from now
        future_time = timezone.now() + timedelta(seconds=60)
        game = GameState.objects.create(phase='DAY', phase_ends_at=future_time)

        # 2. Assertions
        remaining = game.seconds_remaining()
        assert 58 <= remaining <= 60  # Account for micro-delays in execution

        # Test expired phase returns 0
        game.phase_ends_at = timezone.now() - timedelta(seconds=10)
        assert game.seconds_remaining() == 0

    def test_duplicate_vote_prevention(self):
        """
        Tests the database integrity: A single voter should not be able
        to cast two votes in the same game instance.
        """
        # 1. Setup
        game = GameState.objects.create(phase='DAY')
        user1 = User.objects.create_user(username="voter_bob")
        user2 = User.objects.create_user(username="target_alice")
        user3 = User.objects.create_user(username="target_charlie")

        p1 = Player.objects.create(user=user1)
        p2 = Player.objects.create(user=user2)
        p3 = Player.objects.create(user=user3)

        # 2. Action: Create the first vote
        Vote.objects.create(game=game, voter=p1, target=p2)

        # 3. Assertion: Attempting a second vote from same user should raise IntegrityError
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Vote.objects.create(game=game, voter=p1, target=p3)


@pytest.mark.django_db
class TestUserAuth:

    def test_register_valid(self, client):
        resp = client.post(reverse('register'), {
            'username': 'newplayer',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        assert resp.status_code == 302
        assert User.objects.filter(username='newplayer').exists()
        assert Player.objects.filter(user__username='newplayer').exists()

    def test_register_invalid_password_mismatch(self, client):
        resp = client.post(reverse('register'), {
            'username': 'baduser',
            'password1': 'TestPass123!',
            'password2': 'WrongPass!',
        })
        assert resp.status_code == 200  # re-renders with errors
        assert not User.objects.filter(username='baduser').exists()

    def test_login_valid(self, client):
        User.objects.create_user(username='loginuser', password='TestPass123!')
        resp = client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'TestPass123!',
        })
        assert resp.status_code == 302
        assert resp['Location'] == reverse('lobby')

    def test_login_invalid_credentials(self, client):
        User.objects.create_user(username='realuser', password='TestPass123!')
        resp = client.post(reverse('login'), {
            'username': 'realuser',
            'password': 'WrongPassword!',
        })
        assert resp.status_code == 200  # re-renders with errors


@pytest.mark.django_db
class TestLobby:

    def _make_player(self, username, ready=False):
        user = User.objects.create_user(username=username, password='pass')
        p = Player.objects.create(user=user, is_ready=ready)
        return user, p

    def test_ready_up_toggle(self, client):
        user, player = self._make_player('p1')
        client.force_login(user)
        assert not player.is_ready
        client.post(reverse('toggle_ready'))
        player.refresh_from_db()
        assert player.is_ready
        client.post(reverse('toggle_ready'))
        player.refresh_from_db()
        assert not player.is_ready

    def test_start_game_requires_two_players(self, client):
        user, _ = self._make_player('only1', ready=True)
        GameState.objects.get_or_create(id=1, defaults={'phase': 'LOBBY'})
        client.force_login(user)
        resp = client.post(reverse('start_game'))
        assert resp.status_code == 403

    def test_start_game_transitions_to_night(self, client):
        GameState.objects.get_or_create(id=1, defaults={'phase': 'LOBBY'})
        users = []
        for i in range(4):
            u, _ = self._make_player(f'sp{i}', ready=True)
            users.append(u)
        client.force_login(users[0])
        resp = client.post(reverse('start_game'))
        assert resp.status_code == 302
        game = GameState.objects.get(id=1)
        assert game.phase == 'NIGHT'


@pytest.mark.django_db
class TestRoleAssignment:

    def _create_ready_players(self, count):
        for i in range(count):
            u = User.objects.create_user(username=f'rp{i}', password='pass')
            Player.objects.create(user=u, is_ready=True)

    def test_role_ratio(self):
        from game.role_assignment import assign_roles
        self._create_ready_players(8)
        assign_roles()
        mafia = Player.objects.filter(role='Mafia').count()
        town = Player.objects.filter(role='Town').count()
        assert mafia == 2  # 8 // 4 = 2
        assert town == 6
        assert mafia + town == 8

    def test_no_player_without_role(self):
        from game.role_assignment import assign_roles
        self._create_ready_players(5)
        assign_roles()
        roleless = Player.objects.filter(role='').count()
        assert roleless == 0

    def test_minimum_one_mafia(self):
        from game.role_assignment import assign_roles
        # 2 players -> max(1, 2//4) = max(1,0) = 1 mafia
        for i in range(2):
            u = User.objects.create_user(username=f'min{i}', password='pass')
            Player.objects.create(user=u, is_ready=True)
        assign_roles()
        assert Player.objects.filter(role='Mafia').count() == 1


@pytest.mark.django_db
class TestPhaseTransitions:

    def _setup_game_with_players(self, n_mafia=1, n_town=3):
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'LOBBY'})
        game.phase = 'NIGHT'
        game.save()
        players = []
        for i in range(n_mafia):
            u = User.objects.create_user(username=f'mafia{i}', password='pass')
            p = Player.objects.create(user=u, role='Mafia', is_alive=True)
            players.append(p)
        for i in range(n_town):
            u = User.objects.create_user(username=f'town{i}', password='pass')
            p = Player.objects.create(user=u, role='Town', is_alive=True)
            players.append(p)
        return game, players

    def test_night_to_day_transition(self):
        from game.phase_change import advance_game_phase
        game, _ = self._setup_game_with_players()
        advance_game_phase()
        game.refresh_from_db()
        assert game.phase == 'DAY'

    def test_day_to_night_transition(self):
        from game.phase_change import advance_game_phase
        game, _ = self._setup_game_with_players()
        # Move to day first
        game.phase = 'DAY'
        game.save()
        advance_game_phase()
        game.refresh_from_db()
        assert game.phase == 'NIGHT'


@pytest.mark.django_db
class TestDayVoting:

    def _setup(self):
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'DAY'})
        game.phase = 'DAY'
        game.save()
        users = [User.objects.create_user(username=f'dv{i}', password='pass') for i in range(4)]
        players = [Player.objects.create(user=u, role='Town', is_alive=True) for u in users]
        # Give first player a Mafia role for win detection
        players[0].role = 'Mafia'
        players[0].save()
        return game, players

    def test_voted_player_eliminated(self):
        from game.phase_change import resolve_day
        game, players = self._setup()
        target = players[1]
        # Three votes against target
        for voter in [players[0], players[2], players[3]]:
            Vote.objects.create(game=game, voter=voter, target=target)
        resolve_day()
        target.refresh_from_db()
        assert not target.is_alive

    def test_tie_vote_no_elimination(self):
        from game.phase_change import resolve_day
        game, players = self._setup()
        Vote.objects.create(game=game, voter=players[0], target=players[1])
        Vote.objects.create(game=game, voter=players[2], target=players[3])
        resolve_day()
        for p in players:
            p.refresh_from_db()
        assert all(p.is_alive for p in players)

    def test_votes_cleared_after_resolve(self):
        from game.phase_change import resolve_day
        game, players = self._setup()
        Vote.objects.create(game=game, voter=players[0], target=players[1])
        resolve_day()
        assert Vote.objects.filter(game=game).count() == 0


@pytest.mark.django_db
class TestNightAction:

    def _setup(self):
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'NIGHT'})
        game.phase = 'NIGHT'
        game.save()
        mu = User.objects.create_user(username='mafia_na', password='pass')
        tu = User.objects.create_user(username='town_na', password='pass')
        mafia = Player.objects.create(user=mu, role='Mafia', is_alive=True)
        town = Player.objects.create(user=tu, role='Town', is_alive=True)
        return game, mafia, town

    def test_mafia_kill_eliminates_target(self):
        from game.phase_change import resolve_night
        game, mafia, town = self._setup()
        NightAction.objects.create(game=game, mafia_player=mafia, target=town)
        resolve_night()
        town.refresh_from_db()
        assert not town.is_alive

    def test_night_actions_cleared_after_resolve(self):
        from game.phase_change import resolve_night
        game, mafia, town = self._setup()
        NightAction.objects.create(game=game, mafia_player=mafia, target=town)
        resolve_night()
        assert NightAction.objects.filter(game=game).count() == 0


@pytest.mark.django_db
class TestWinDetection:

    def test_town_wins_when_all_mafia_dead(self):
        from game.phase_change import check_for_winner
        u1 = User.objects.create_user(username='deadmafia', password='pass')
        u2 = User.objects.create_user(username='alivetown', password='pass')
        Player.objects.create(user=u1, role='Mafia', is_alive=False)
        Player.objects.create(user=u2, role='Town', is_alive=True)
        assert check_for_winner() == 'Town'

    def test_mafia_wins_when_equal_count(self):
        from game.phase_change import check_for_winner
        u1 = User.objects.create_user(username='mafiawin', password='pass')
        u2 = User.objects.create_user(username='townlose', password='pass')
        Player.objects.create(user=u1, role='Mafia', is_alive=True)
        Player.objects.create(user=u2, role='Town', is_alive=True)
        assert check_for_winner() == 'Mafia'

    def test_mafia_wins_when_outnumber_town(self):
        from game.phase_change import check_for_winner
        for i in range(2):
            u = User.objects.create_user(username=f'mw{i}', password='pass')
            Player.objects.create(user=u, role='Mafia', is_alive=True)
        u = User.objects.create_user(username='tw0', password='pass')
        Player.objects.create(user=u, role='Town', is_alive=True)
        assert check_for_winner() == 'Mafia'

    def test_no_winner_when_game_ongoing(self):
        from game.phase_change import check_for_winner
        for i in range(2):
            u = User.objects.create_user(username=f'mg{i}', password='pass')
            Player.objects.create(user=u, role='Mafia', is_alive=True)
        for i in range(4):
            u = User.objects.create_user(username=f'tg{i}', password='pass')
            Player.objects.create(user=u, role='Town', is_alive=True)
        assert check_for_winner() is None


@pytest.mark.django_db
class TestGameReset:

    def test_reset_clears_votes_actions_messages(self):
        from game.phase_change import reset_game
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'DAY'})
        game.phase = 'DAY'
        game.save()

        u1 = User.objects.create_user(username='res1', password='pass')
        u2 = User.objects.create_user(username='res2', password='pass')
        p1 = Player.objects.create(user=u1, role='Mafia', is_alive=True)
        p2 = Player.objects.create(user=u2, role='Town', is_alive=True)

        Vote.objects.create(game=game, voter=p1, target=p2)
        NightAction.objects.create(game=game, mafia_player=p1, target=p2)
        ChatMessage.objects.create(game=game, sender=None, chat_type='system', content='test')

        reset_game()
        game.refresh_from_db()

        assert game.phase == 'LOBBY'
        assert Vote.objects.filter(game=game).count() == 0
        assert NightAction.objects.filter(game=game).count() == 0
        assert ChatMessage.objects.filter(game=game).count() == 0

    def test_reset_clears_player_roles_and_readiness(self):
        from game.phase_change import reset_game
        GameState.objects.get_or_create(id=1, defaults={'phase': 'DAY'})
        u = User.objects.create_user(username='rp_reset', password='pass')
        p = Player.objects.create(user=u, role='Mafia', is_alive=False, is_ready=True)
        reset_game()
        p.refresh_from_db()
        assert p.role == ''
        assert p.is_alive
        assert not p.is_ready


@pytest.mark.django_db
class TestEarlyEndGame:

    def test_end_game_more_town_than_mafia(self, client):
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'DAY'})
        game.phase = 'DAY'
        game.save()

        mu = User.objects.create_user(username='eg_mafia', password='pass')
        tu1 = User.objects.create_user(username='eg_town1', password='pass')
        tu2 = User.objects.create_user(username='eg_town2', password='pass')
        Player.objects.create(user=mu, role='Mafia', is_alive=True)
        Player.objects.create(user=tu1, role='Town', is_alive=True)
        Player.objects.create(user=tu2, role='Town', is_alive=True)

        client.force_login(mu)
        resp = client.post(reverse('end_game'))
        assert resp.status_code == 302
        game.refresh_from_db()
        assert game.phase == 'GAME_OVER'
        assert game.winner == 'Town'

    def test_end_game_mafia_equal_town(self, client):
        game, _ = GameState.objects.get_or_create(id=1, defaults={'phase': 'DAY'})
        game.phase = 'DAY'
        game.save()

        mu = User.objects.create_user(username='eq_mafia', password='pass')
        tu = User.objects.create_user(username='eq_town', password='pass')
        Player.objects.create(user=mu, role='Mafia', is_alive=True)
        Player.objects.create(user=tu, role='Town', is_alive=True)

        client.force_login(mu)
        resp = client.post(reverse('end_game'))
        assert resp.status_code == 302
        game.refresh_from_db()
        assert game.winner == 'Mafia'
