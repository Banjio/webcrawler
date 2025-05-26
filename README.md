# Webcrawler

This is a vibe coded web crawler using claude sonnet 4. 

## Basic Usage

```bash
# Basic crawling with 60s limit
python src/cli.py https://example.com

# Custom time limit and depth
python src/cli.py https://example.com --max-time 120 --max-depth 3

# Filter results and save to file
python src/cli.py https://example.com --filter "python" --output results.json

# Quiet mode (no progress output)
python src/cli.py https://example.com --quiet
```