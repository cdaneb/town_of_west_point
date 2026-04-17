from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('lobby/', views.lobby_view, name='lobby'),
    path('lobby/toggle-ready/', views.toggle_ready, name='toggle_ready'),
    path('lobby/start/', views.start_game, name='start_game'),
    path('game/', views.game_view, name='game_room'),
    path('game/vote/<int:target_id>/', views.cast_vote, name='cast_vote'),
    path('game/night-action/<int:target_id>/', views.cast_night_action, name='cast_night_action'),
    path('api/state/', views.game_state_api, name='game_state_api'),
]