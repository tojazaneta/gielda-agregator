from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import json


def scrape_single_stock(playwright, stock_name: str) -> dict:
    """
    Scrapes data for a single stock from MSN Finance.

    Args:
        playwright: Playwright instance (sync).
        stock_name: Name of the stock, possibly with ticker in parentheses.

    Returns:
        Dictionary with keys: 'price', 'msn_recommendation', 'analyst_count'.
        Or 'Error' values if scraping failed.
    """
    print(f"--- Scraping stock: {stock_name} ---")

    # Extract ticker and verification name from the stock_name
    if '(' in stock_name and ')' in stock_name:
        ticker = stock_name.split('(')[0].strip()
        verification_name = stock_name.split('(')[1].replace(')', '').strip()
    else:
        ticker = stock_name.strip()
        verification_name = ticker

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/114.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        page.goto("https://www.msn.com/pl-pl/finanse/rynki", timeout=60000)

        # Accept cookie popup if it appears
        try:
            page.get_by_role("button", name="Akceptuję").click(timeout=7000)
        except PlaywrightTimeoutError:
            pass

        # Find the search box and fill in the ticker
        search_box = page.locator("#topStrip").get_by_role("textbox", name="Wyszukaj akcje i inne")
        search_box.click()
        search_box.fill(ticker)
        page.wait_for_timeout(1500)  # Wait for suggestions to load

        # Try to select the suggested stock matching verification_name
        suggestion_locator = page.get_by_role("option", name=re.compile(verification_name, re.IGNORECASE))
        if suggestion_locator.count() > 0:
            suggestion_locator.first.click()
        else:
            search_box.press("Enter")

        page.wait_for_url("**/fi-**", timeout=20000)
        page.wait_for_timeout(3000)  # Wait for page to stabilize

        # Scrape data
        analyst_card = page.locator("div[data-t*='Anchor_Title_Analyst']")
        recommendation_elem = analyst_card.locator(".cardBody_content_keyWords_analystic-DS-EntryPoint1-1")
        msn_recommendation = recommendation_elem.text_content() or "None"

        analyst_count = 0
        analyst_elem = analyst_card.locator("div").filter(has_text=re.compile(r"\d+\s+analitycy"))
        if analyst_elem.count() > 0:
            match = re.search(r'\d+', analyst_elem.first.text_content() or "")
            if match:
                analyst_count = int(match.group(0))

        price_elem = page.locator("div[class*='mainPrice'][class*='color_']")
        price = price_elem.text_content() or "None"

        if not price or not msn_recommendation:
            raise ValueError("Failed to retrieve price or recommendation.")

        print(f"   OK Success for {stock_name}")
        return {
            "price": price,
            "msn_recommendation": msn_recommendation,
            "analyst_count": analyst_count
        }

    except Exception as e:
        print(f"   X Error for {stock_name}: {e}")
        return {
            "price": "Error",
            "msn_recommendation": "Error",
            "analyst_count": 0
        }
    finally:
        context.close()
        browser.close()


def main():
    print("--- Starting nightly stock scraping... ---")

    stocks_to_check = []
    try:
        with open('./Rekomendacje giełdowe', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[2:]:  # skip first two lines (header likely)
                fields = [field.strip() for field in line.strip().split('|')]
                if len(fields) > 5 and fields[2].lower() == 'kupuj':
                    stocks_to_check.append({
                        "name": fields[1],
                        "br_recommendation": fields[2],
                        "cd_k": fields[5]
                    })
    except FileNotFoundError:
        print("CRITICAL ERROR: Input file not found!")
        return

    final_list = []
    positive_keywords = ["kupuj", "kup", "zdecydowanie kup"]

    with sync_playwright() as p:
        for stock in stocks_to_check:
            if len(final_list) >= 10:
                break

            msn_data = scrape_single_stock(p, stock['name'])
            if "Error" in msn_data['msn_recommendation'] or msn_data['analyst_count'] < 7:
                continue

            if any(keyword in msn_data['msn_recommendation'].lower() for keyword in positive_keywords):
                result = {
                    "name": stock['name'],
                    "br_recommendation": stock['br_recommendation'],
                    "cd_k": stock['cd_k'],
                    "price": msn_data['price'],
                    "msn_recommendation": msn_data['msn_recommendation'],
                    "analyst_count": msn_data['analyst_count']
                }
                final_list.append(result)

    # Overwrite wyniki.json with new results only
    with open('wyniki.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)

    print(f"Results successfully saved to 'wyniki.json'")


if __name__ == "__main__":
    main()
