from flask import Flask, render_template
import subprocess
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAMES = {
    "Fruit Ninja":     "games/fruit_ninja/game.py",
    "Balloon Shooter": "games/balloon_shooter/gun.py",
    "Gunship Battle":  "games/gunship_battle/war.py",
    "Ping Pong":       "games/ping_pong/pingpong.py",
    "Bug Smasher":     "games/bug_smasher/bug.py",
}

@app.route('/')
def home():
    return render_template("index.html", games=GAMES)

@app.route('/play/<game>')
def play(game):
    rel_path = GAMES.get(game)
    if rel_path:
        abs_path = os.path.join(BASE_DIR, rel_path)
        game_dir = os.path.dirname(abs_path)   # each game's own folder as cwd
        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = "coreaudio"   # macOS CoreAudio for pygame sound
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        subprocess.Popen(["python3.9", abs_path], env=env, cwd=game_dir)
        return f"{game} Launched!"
    return "Game Not Found"

if __name__ == '__main__':
    app.run(port=5000, debug=True)
