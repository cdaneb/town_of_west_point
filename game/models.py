from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class GameState(models.Model):
    PHASES = [
        ('LOBBY', 'Lobby'),
        ('NIGHT', 'Mafia Night'),
        ('DAY', 'Daytime Discussion'),
        ('GAME_OVER', 'Game Over'),
    ]

    phase = models.CharField(max_length=20, choices=PHASES, default='LOBBY')
    winner = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    phase_started_at = models.DateTimeField(null=True, blank=True)
    phase_ends_at = models.DateTimeField(null=True, blank=True)

    day_length_seconds = models.PositiveIntegerField(default=120)
    night_length_seconds = models.PositiveIntegerField(default=120)

    def __str__(self):
        return f"GameState({self.phase})"

    def seconds_remaining(self):
        if not self.phase_ends_at:
            return 0
        delta = int((self.phase_ends_at - timezone.now()).total_seconds())
        return max(delta, 0)


class Player(models.Model):
    ROLE_CHOICES = [
        ('Mafia', 'Mafia'),
        ('Town', 'Town'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True)
    is_alive = models.BooleanField(default=True)
    is_ready = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    # kept for compatibility with your old code path
    votes = models.IntegerField(default=0)
    has_voted = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Vote(models.Model):
    game = models.ForeignKey(GameState, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_cast')
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'voter')

    def __str__(self):
        return f"{self.voter} -> {self.target}"


class NightAction(models.Model):
    game = models.ForeignKey(GameState, on_delete=models.CASCADE, related_name='night_actions')
    mafia_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='night_actions_cast')
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='night_actions_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'mafia_player')

    def __str__(self):
        return f"{self.mafia_player} -> {self.target}"


class ChatMessage(models.Model):
    CHAT_CHOICES = [
        ('public', 'Public'),
        ('mafia', 'Mafia'),
        ('system', 'System'),
    ]

    game = models.ForeignKey(GameState, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True
    )
    chat_type = models.CharField(max_length=10, choices=CHAT_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender_name = self.sender.user.username if self.sender else "SYSTEM"
        return f"[{self.chat_type}] {sender_name}: {self.content[:30]}"