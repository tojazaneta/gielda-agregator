from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import json

# Definiujemy stałą ścieżkę do folderu, który będzie współdzielony
# na Render.com. To jest najlepsza praktyka.
DATA_DIR = '/var/data'
INPUT_FILE = './Rekomendacje giełdowe' # Plik wejściowy jest w tym samym folderze co skrypt
OUTPUT_FILE = f'{DATA_DIR}/wyniki.json'


def scrapuj_jedna_spolke(nazwa_spolki: str):
    print(f"--- Rozpoczynam profesjonalny scraping dla: {nazwa_spolki} ---")
    
    if '(' in nazwa_spolki and ')' in nazwa_spolki:
        ticker = nazwa_spolki.split('(')[0].strip()
        nazwa_do_weryfikacji = nazwa_spolki.split('(')[1].replace(')', '').strip()
    else:
        ticker = nazwa_spolki.strip()
        nazwa_do_weryfikacji = ticker
    print(f"   ...Wyodrębniono Ticker: '{ticker}' i Nazwę do weryfikacji: '{nazwa_do_weryfikacji}'")

    with sync_playwright() as p:
        # WAŻNE: Nie ma już 'executable_path'! Render instaluje przeglądarkę globalnie.
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        try:
            page.goto("https://www.msn.com/pl-pl/finanse/rynki", timeout=60000)
            
            try:
                page.get_by_role("button", name="Akceptuję").click(timeout=7000)
                print("   ...Krok 1: Przycisk cookie kliknięty.")
            except PlaywrightTimeoutError:
                print("   ...Krok 1: Przycisk cookie nie pojawił się.")
                pass
            
            search_box = page.locator("#topStrip").get_by_role("textbox", name="Wyszukaj akcje i inne")
            search_box.click()
            search_box.fill(ticker)
            page.wait_for_timeout(1500)

            suggestion_locator = page.get_by_role("option", name=re.compile(nazwa_do_weryfikacji, re.IGNORECASE))
            if suggestion_locator.count() > 0:
                suggestion_locator.first.click()
            else:
                search_box.press("Enter")

            page.wait_for_url("**/fi-**", timeout=20000)
            page.wait_for_timeout(3000)

            analyst_card = page.locator("div[data-t*='Anchor_Title_Analyst']")
            rekomendacja_elem = analyst_card.locator(".cardBody_content_keyWords_analystic-DS-EntryPoint1-1")
            rekomendacja = rekomendacja_elem.text_content() if rekomendacja_elem.count() > 0 else "Brak"

            analyst_count = 0
            analyst_elem = analyst_card.locator("div").filter(has_text=re.compile(r"\d+\s+analitycy"))
            if analyst_elem.count() > 0:
                analyst_text = analyst_elem.first.text_content()
                match = re.search(r'\d+', analyst_text)
                if match:
                    analyst_count = int(match.group(0))
            
            cena_elem = page.locator("div[class*='mainPrice'][class*='color_']")
            cena = cena_elem.text_content() if cena_elem.count() > 0 else "Brak"

            if not cena or not rekomendacja:
                 raise ValueError("Nie udało się pobrać ceny lub rekomendacji.")
            
            print(f"   ✅ Sukces dla {nazwa_spolki}: Cena={cena}, Rekomendacja={rekomendacja}, Analitycy={analyst_count}")
            return {"cena": cena, "rekomendacja_msn": rekomendacja, "analyst_count": analyst_count}

        except Exception as e:
            print(f"   ❌ Błąd dla {nazwa_spolki}: {e}")
            return {"cena": "Błąd", "rekomendacja_msn": "Błąd", "analyst_count": 0}
        finally:
            context.close()
            browser.close()

def main():
    print("--- Rozpoczynam nocne polowanie na spółki... ---")
    
    spolki_do_sprawdzenia = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f.readlines()[2:]:
                pola = [pole.strip() for pole in line.strip().split('|')]
                if len(pola) > 5 and pola[2].lower() == 'kupuj':
                    spolki_do_sprawdzenia.append({
                        "nazwa": pola[1], "rekomendacja_br": pola[2], "cd_k": pola[5]
                    })
    except FileNotFoundError:
        print(f"KRYTYCZNY BŁĄD: Nie znaleziono pliku wejściowego: '{INPUT_FILE}'!")
        return

    finalna_lista = []
    index_spolki = 0
    pozytywne_rekomendacje = ["kupuj", "zdecydowanie", "przeważaj"]

    while len(finalna_lista) < 10 and index_spolki < len(spolki_do_sprawdzenia):
        spolka = spolki_do_sprawdzenia[index_spolki]
        index_spolki += 1
        print(f"\n({len(finalna_lista) + 1}/10) Sprawdzam spółkę #{index_spolki}: {spolka['nazwa']}")
        wynik_msn = scrapuj_jedna_spolke(spolka['nazwa'])

        if "Błąd" in wynik_msn['rekomendacja_msn'] or wynik_msn['analyst_count'] < 5:
            continue
            
        if any(keyword in wynik_msn['rekomendacja_msn'].lower() for keyword in pozytywne_rekomendacje):
            spolka.update(wynik_msn)
            finalna_lista.append(spolka)

    print(f"\n--- Zakończono polowanie! Znaleziono {len(finalna_lista)} spółek. ---")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(finalna_lista, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Wyniki zostały pomyślnie zapisane do pliku '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()
