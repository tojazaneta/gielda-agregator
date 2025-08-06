from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Page
import re
import json

def scrape_single_stock(page: Page, stock_name: str) -> dict:
    """
    Scrapes data for a single stock from MSN Finance using an existing page.

    Args:
        page: An active Playwright page object.
        stock_name: Name of the stock, possibly with ticker in parentheses.

    Returns:
        Dictionary with keys: 'price', 'msn_recommendation', 'analyst_count'.
        Or 'Error' values if scraping failed.
    """
    print(f"--- Scraping stock: {stock_name} ---")

    # Assumes format "TICKER (NAME)" e.g. "1AT (ATAL)"
    match = re.match(r'([^(\s]+)\s*\(([^)]+)\)', stock_name)
    if match:
        ticker = match.group(1).strip()
        verification_name = match.group(2).strip()
    else:
        # Fallback for simple names without parentheses
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
            
            for line in lines[2:]:
                fields = [field.strip() for field in line.strip().split('|')]
                if len(fields) > 5:
                    stocks_to_check.append({
                        "name": fields[1],
                        "br_recommendation": fields[2],
                        "cd_k": fields[5]
                    })

    except FileNotFoundError:
        print("CRITICAL ERROR: Input file 'Rekomendacje giełdowe' not found!")
        return

    final_list = []
    
    with sync_playwright() as p:
        # IMPORTANT: Launch the browser only once for performance.
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for stock in stocks_to_check:
            if len(final_list) >= 10:
                print("--- Reached the limit of 10 results. Stopping. ---")
                break
            
            if not stock['name']:
                continue

            msn_data = scrape_single_stock(page, stock['name'])
            
            if "Error" in msn_data['msn_recommendation']:
                continue

            msn_rec_lower = msn_data['msn_recommendation'].lower()
            analyst_count = msn_data['analyst_count']

            cond1 = (msn_rec_lower == "zdecydowanie kupuj" and analyst_count > 5)
            cond2 = (msn_rec_lower == "kupuj" and analyst_count > 10)

            if cond1 or cond2:
                result = {
                    "name": stock['name'],
                    "br_recommendation": stock['br_recommendation'],
                    "cd_k": stock['cd_k'],
                    "price": msn_data['price'],
                    "msn_recommendation": msn_data['msn_recommendation'],
                    "analyst_count": msn_data['analyst_count']
                }
                final_list.append(result)
                # --- NEW: Log entry addition ---
                print(f"   ✅ Added: {result['name']}. Current count: {len(final_list)}/10")
        
        context.close()
        browser.close()

    with open('wyniki.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"\nResults successfully saved to 'wyniki.json'. Found {len(final_list)} matching stocks.")


if __name__ == "__main__":
    main()
