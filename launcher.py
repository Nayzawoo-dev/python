
from flask import Flask, render_template, send_from_directory
import subprocess
import os
import sys

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAMES = {
    "Fruit Ninja": "games/fruit_ninja/game.py",
    "Balloon Shooter": "games/balloon_shooter/gun.py",
    "Gunship Battle": "games/gunship_battle/war.py",
    "Ping Pong": "games/ping_pong/pingpong.py",
    "Bug Smasher": "games/bug_smasher/bug.py",
    "Metal Slug": "games/metal_slug/main.py",
}

# Preview image for each game: served via /game-image/<dir>/<file>
GAME_IMAGES = {
    "Fruit Ninja":     "/game-image/fruit_ninja/fruit_game.png",
    "Balloon Shooter": "/game-image/balloon_shooter/ballon_game.png",
    "Gunship Battle":  "/game-image/gunship_battle/gunship_battle_game.png",
    "Ping Pong":       "/game-image/ping_pong/ping_pong_game.png",
    "Bug Smasher":     "/game-image/bug_smasher/bug_smasher_game.png",
    "Metal Slug":      "/game-image/metal_slug/metal_slug_game.png",
}


@app.route('/')
def home():
    return render_template("index.html", games=GAMES, game_images=GAME_IMAGES)


@app.route('/guide')
def guide():
    return render_template("guide.html")


@app.route('/game-image/<game_dir>/<filename>')
def game_image(game_dir, filename):
    image_dir = os.path.join(BASE_DIR, 'games', game_dir)
    return send_from_directory(image_dir, filename)


@app.route('/play/<game>')
def play(game):
    rel_path = GAMES.get(game)

    if rel_path:
        abs_path = os.path.join(BASE_DIR, rel_path)
        game_dir = os.path.dirname(abs_path)

        env = os.environ.copy()
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

        # Use the same Python interpreter running Flask
        subprocess.Popen(
            [sys.executable, abs_path],
            env=env,
            cwd=game_dir
        )

        return f"{game} Launched!"

    return "Game Not Found"


if __name__ == '__main__':
    app.run(port=5000, debug=True)

