=====

  Mafia Web App -- Minimum Viable Product
  CDT Christian Dane Beels, CDT Benjamin Doody
  CY300 Computing Fundamentals

=====

Requirements: Python 3, Django

-----

Setup Instructions:

-----

1. Run: 

     python manage.py migrate

3. Create an admin superuser (your credentials):

     python manage.py createsuperuser

4. Run the server:

     python manage.py runserver

5. Navigate to admin subdirectory. (Front-end is blank currently):

     http://127.0.0.1:8000/admin


Testing

-----

To run a game:

1. Under the Game section, click Game States -> Add Game State.
   Leave the phase as LOBBY and save.

2. Click Users -> Add User to create at least 4 players.

3. Click Players -> Add Player to create a Player entry for
   each user you just created.

4. Go to Game States, check the box next to your game, select
   "Move to Next Phase" from the Action dropdown, and click Go.
   The phase will advance to NIGHT and roles (Mafia/Town) will
   be randomly assigned to all players.

5. To simulate voting, open any Player and set their votes field
   to a non-zero number, then advance the phase again. The player
   with the most votes will be eliminated.

6. Continue advancing phases until a winner is declared in the
   winner field of the Game State (either Mafia or Town).


Project Structure

-----

  mvp/
  |-- manage.py
  |-- mvp/
  |   |-- settings.py
  |   |-- urls.py
  |   |-- asgi.py
  |   `-- wsgi.py
  `-- game/
      |-- models.py           GameState and Player data
      |-- admin.py            Admin panel
      |-- phase_change.py     Phase change logic
      `-- role_assignment.py  Role assignment logic

=====
