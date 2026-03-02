from flask import Flask, render_template, send_from_directory
import subprocess
import os

app = Flask(__name__)

GAMES = {
    "Fruit Ninja": "game.py",
    "Balloon Shooter": "gun.py",
    "Gunship Battle": "war.py",
    "Ping Pong" : "pingpong.py",
    "Bug Smasher" : "bug.py"
}

@app.route('/')
def home():
    return render_template("index.html", games=GAMES)


@app.route("/assets/<path:filename>")
def assets(filename: str):
    """
    Serve image assets that currently live alongside the templates.
    This lets the HTML use /assets/<file> paths for previews.
    """
    templates_dir = os.path.join(app.root_path, "templates")
    return send_from_directory(templates_dir, filename)

@app.route('/play/<game>')
def play(game):
    file = GAMES.get(game)
    if file:
        subprocess.Popen(["python3.9", os.path.join(file)])
        return f"{game} Launched!"
    return "Game Not Found"

if __name__ == '__main__':
    app.run(port=5000, debug=True)