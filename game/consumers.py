import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Player, ChatMessage
from .phase_change import get_game


class PublicChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "public_chat"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        player = await self.get_player()
        game = await self.get_game()

        if not player or not player.is_alive or game.phase != "DAY":
            return

        await self.create_message(player.id, game.id, "public", message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "username": self.user.username,
                "message": message,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_player(self):
        return Player.objects.filter(user=self.user).first()

    @database_sync_to_async
    def get_game(self):
        return get_game()

    @database_sync_to_async
    def create_message(self, player_id, game_id, chat_type, content):
        player = Player.objects.get(id=player_id)
        game = get_game()
        ChatMessage.objects.create(game=game, sender=player, chat_type=chat_type, content=content)


class MafiaChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "mafia_chat"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        player = await self.get_player()
        if not player or player.role != "Mafia":
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        player = await self.get_player()
        game = await self.get_game()

        if not player or not player.is_alive or player.role != "Mafia" or game.phase != "NIGHT":
            return

        await self.create_message(player.id, game.id, "mafia", message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "username": self.user.username,
                "message": message,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_player(self):
        return Player.objects.filter(user=self.user).first()

    @database_sync_to_async
    def get_game(self):
        return get_game()

    @database_sync_to_async
    def create_message(self, player_id, game_id, chat_type, content):
        player = Player.objects.get(id=player_id)
        game = get_game()
        ChatMessage.objects.create(game=game, sender=player, chat_type=chat_type, content=content)