from flask import Flask, render_template
import subprocess
import os

app = Flask(__name__)

GAMES = {
    "Fruit Ninja": "game.py",
    "Balloon Shooter": "gun.py",
    "Gunship Battle": "war.py",
    "Ping Pong" : "hand_tracker.py",
    "Bug Smasher" : "bug.py"
}

@app.route('/')
def home():
    return render_template("index.html", games=GAMES)

@app.route('/play/<game>')
def play(game):
    file = GAMES.get(game)
    if file:
        subprocess.Popen(["python", os.path.join(file)])
        return f"{game} Launched!"
    return "Game Not Found"

if __name__ == '__main__':
    app.run(port=5000, debug=True)