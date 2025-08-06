from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Page
import re
import json
import os

def scrape_single_stock(page: Page, stock_name: str) -> dict:
    print(f"--- Scraping stock: {stock_name} ---")

    match = re.match(r'([^(\s]+)\s*\(([^)]+)\)', stock_name)
    if match:
        ticker = match.group(1).strip()
        verification_name = match.group(2).strip()
    else:
        ticker = stock_name.strip()
        verification_name = ticker

    try:
        page.goto("https://www.msn.com/pl-pl/finanse/rynki", timeout=30000)

        try:
            page.get_by_role("button", name="Akceptuję").click(timeout=5000)
        except PlaywrightTimeoutError:
            pass

        search_box = page.locator("#topStrip").get_by_role("textbox", name="Wyszukaj akcje i inne")
        search_box.click()
        search_box.fill(ticker)
        page.wait_for_timeout(1000)

        suggestion_locator = page.get_by_role("option", name=re.compile(verification_name, re.IGNORECASE))
        if suggestion_locator.count() > 0:
            suggestion_locator.first.click()
        else:
            search_box.press("Enter")

        page.wait_for_url("**/fi-**", timeout=15000)
        
        analyst_card = page.locator("div[data-t*='analystRating']")
        analyst_card.wait_for(timeout=10000)

        recommendation_elem = analyst_card.locator(".cardBody_content_keyWords_analystic-DS-EntryPoint1-1")
        msn_recommendation = recommendation_elem.text_content().strip() or "None"

        analyst_count = 0
        analyst_elem = analyst_card.locator("div").filter(has_text=re.compile(r"\d+\s+analitycy"))
        if analyst_elem.count() > 0:
            match = re.search(r'(\d+)', analyst_elem.first.text_content() or "")
            if match:
                analyst_count = int(match.group(1))

        price_elem = page.locator("div[class*='mainPrice'][class*='color_']")
        price = price_elem.text_content().strip() or "None"

        if not price or not msn_recommendation:
            raise ValueError("Failed to retrieve price or recommendation.")

        print(f"   OK -> Success for {stock_name}: Price: {price}, Recommendation: {msn_recommendation}, Analysts: {analyst_count}")
        return {
            "price": price,
            "msn_recommendation": msn_recommendation,
            "analyst_count": analyst_count
        }

    except Exception as e:
        print(f"   X  -> Error for {stock_name}: {e}")
        return {
            "price": "Error",
            "msn_recommendation": "Error",
            "analyst_count": 0
        }

def main():
    print("--- Starting nightly stock scraping... ---")

    stocks_to_check = []
    try:
        with open('Rekomendacje giełdowe', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:
                fields = [field.strip() for field in line.strip().strip('|').split('|')]
                if len(fields) > 1:
                     stocks_to_check.append({
                        "name": fields[0],
                        "br_recommendation": fields[1],
                        "cd_k": fields[4] if len(fields) > 4 else ""
                    })
    except FileNotFoundError:
        print("CRITICAL ERROR: Input file 'Rekomendacje giełdowe' not found!")
        return

    results_dict = {}
    if os.path.exists('wyniki.json'):
        try:
            with open('wyniki.json', 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                for item in existing_results:
                    if 'name' in item:
                        results_dict[item['name']] = item
        except (json.JSONDecodeError, FileNotFoundError):
            print("Warning: 'wyniki.json' found but is empty or corrupted. Starting fresh.")

    print(f"Loaded {len(results_dict)} existing results from 'wyniki.json'.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for stock in stocks_to_check:
            if not stock['name']:
                continue

            was_present = stock['name'] in results_dict
            msn_data = scrape_single_stock(page, stock['name'])
            
            if "Error" in msn_data['msn_recommendation']:
                continue

            msn_rec_lower = msn_data['msn_recommendation'].lower()
            analyst_count = msn_data['analyst_count']

            cond1 = (msn_rec_lower == "zdecydowanie kup" and analyst_count > 5)
            cond2 = (msn_rec_lower == "kup" and analyst_count > 10)

            if cond1 or cond2:
                result = {
                    "name": stock['name'],
                    "br_recommendation": stock['br_recommendation'],
                    "cd_k": stock['cd_k'],
                    "price": msn_data['price'],
                    "msn_recommendation": msn_data['msn_recommendation'],
                    "analyst_count": msn_data['analyst_count']
                }
                results_dict[stock['name']] = result
                if was_present:
                    print(f"   🔄 Updated stock: {result['name']}")
                else:
                    print(f"   ✅ Added new stock: {result['name']}")
            elif was_present:
                results_dict.pop(stock['name'])
                print(f"   🗑️ Removed (conditions not met): {stock['name']}")
        
        input_stock_names = {s['name'] for s in stocks_to_check}
        stocks_to_remove = [name for name in results_dict if name not in input_stock_names]
        for name in stocks_to_remove:
            results_dict.pop(name)
            print(f"   🗑️ Removed (not in source file anymore): {name}")

        context.close()
        browser.close()
    
    final_list = list(results_dict.values())

    if len(final_list) > 20:
        print(f"--- List contains {len(final_list)} items. Truncating to 20. ---")
        final_list = final_list[:20]

    with open('wyniki.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"\nProcessing complete. Results saved to 'wyniki.json'. Total stocks in file: {len(final_list)}.")

if __name__ == "__main__":
    main()
