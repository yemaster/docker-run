from flask import Flask, render_template
import platform

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", sys_version=platform.python_version())

if __name__ == "__main__":
    app.run(port=8000)