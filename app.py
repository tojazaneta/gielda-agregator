from flask import Flask, render_template
import json

app = Flask(__name__)

# Ta sama ścieżka do pliku z wynikami, co w scraperze
OUTPUT_FILE = '/var/data/wyniki.json'

@app.route('/')
def index():
    print(f"--- Strona odświeżona. Wczytuję ostatnie wyniki z pliku '{OUTPUT_FILE}'... ---")
    
    dane_rekomendacji = []
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            dane_rekomendacji = json.load(f)
    except FileNotFoundError:
        print(f"   -> Plik '{OUTPUT_FILE}' nie został jeszcze utworzony.")
    except json.JSONDecodeError:
        print(f"   -> Błąd odczytu pliku '{OUTPUT_FILE}'.")

    return render_template('index.html', rekomendacje=dane_rekomendacji)
