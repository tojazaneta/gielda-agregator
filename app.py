from flask import Flask, render_template, jsonify
import json
import threading

# Importujemy naszą funkcję-robota
from scraper import uruchom_polowanie

app = Flask(__name__)

# Ta sama ścieżka, co w scraperze
OUTPUT_FILE = '/tmp/wyniki.json'

@app.route('/')
def index():
    dane_rekomendacji = []
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            dane_rekomendacji = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass # Ignorujemy błędy, jeśli plik nie istnieje lub jest pusty
    return render_template('index.html', rekomendacje=dane_rekomendacji)

@app.route('/uruchom-robota')
def trigger_scrape_endpoint():
    def run_in_background():
        print("--- Otrzymano sygnał do uruchomienia robota w tle... ---")
        uruchom_polowanie()

    thread = threading.Thread(target=run_in_background)
    thread.start()
    
    return jsonify({"status": "Robot uruchomiony w tle."}), 202
