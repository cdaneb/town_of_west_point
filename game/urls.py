from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('lobby/', views.lobby_view, name='lobby'),
    path('lobby/toggle-ready/', views.toggle_ready, name='toggle_ready'),
    path('lobby/start/', views.start_game, name='start_game'),
    path('lobby/reset/', views.reset_game_view, name='reset_game'),
    path('lobby/leave/', views.leave_lobby, name='leave_lobby'),
    path('game/end/', views.end_game_view, name='end_game'),
    path('game/', views.game_view, name='game_room'),
    path('game/vote/<int:target_id>/', views.cast_vote, name='cast_vote'),
    path('game/night-action/<int:target_id>/', views.cast_night_action, name='cast_night_action'),
    path('api/state/', views.game_state_api, name='game_state_api'),
    path('api/messages/', views.get_messages, name='get_messages'),
    path('api/send-message/', views.send_message, name='send_message'),
]