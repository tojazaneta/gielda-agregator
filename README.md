# Stock Recommendation Aggregator

This is a simple and quick stock recommendation aggregator I created for personal use.  
It scrapes stock recommendations and analyst data from MSN Finance for companies that have positive buy ratings on BiznesRadar, then presents the results on a clean, responsive web page.

> **Disclaimer:**  
> This project and its analyses are for informational purposes only and should **not** be treated as professional investment advice.  
> Stock markets are volatile and losses can occur. I do **not** take any responsibility for financial decisions made based on this data.

## Features

- Scrapes latest stock recommendations and analyst opinions automatically.
- Filters companies with positive "Buy" ratings and sufficient analyst coverage.
- Saves aggregated data as a JSON file (`wyniki.json`).
- Displays results in a responsive and accessible static HTML page.
- Easily deployable on GitHub Pages with automated updates via GitHub Actions.

## Getting Started

### Prerequisites

- Python 3.8+
- Playwright library
- Input file with BiznesRadar recommendations (`Rekomendacje giełdowe`)

### Setup and Usage

1. Clone this repository:

```bash
git clone https://github.com/tojazaneta/gielda-agregator.git
cd gielda-agregator
```

2. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

3. Place your `Rekomendacje giełdowe` input file in the project root.

4. Run the scraper to generate/update `wyniki.json`:

```bash
python scraper.py
```

5. Open `index.html` in a browser. For local testing, use a simple HTTP server:

```bash
python3 -m http.server 8000
```


Then visit `http://localhost:8000/index.html`.

## Deployment

Use GitHub Actions to automate scraping and updates, and serve the static site with GitHub Pages.  

Check the `.github/workflows` folder for the workflow configuration.

## Accessibility & Responsiveness

- The webpage is designed with accessibility (WCAG) in mind.
- Responsive layout ensures usability on mobile devices.

## License

This project is provided "as-is" without warranty of any kind. Use at your own risk.

---

Feel free to contribute or modify it as needed for your own purposes!



