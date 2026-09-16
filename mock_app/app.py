# Import the necessary paths
import json
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

# Get members.json
DATA_FILE = Path(__file__).parent / "data" / "members.json"

# load the members from the members.json into a python list
def load_members():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["members"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search_member():
    member_id = request.form.get("member_id", "").strip()
    members = load_members()
    member = next(
        (member for member in members if member["member_id"] == member_id),
        None
    )

    if member is None:
        return render_template(
            "index.html",
            error="Member not found."
        )
    return render_template(
        "member.html",
        member=member
    )

@app.route("/operator")
def operator():
    return render_template("operator.html")

if __name__ == "__main__":
    app.run(debug=True)


