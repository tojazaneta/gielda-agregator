from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route('/')
def index():
    try:
        with open('wyniki.json', 'r', encoding='utf-8') as f:
            rekomendacje = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        rekomendacje = []

    return render_template('index.html', rekomendacje=rekomendacje)

if __name__ == "__main__":
    app.run(debug=True)
