# ArXiv Paper Reader

A Python tool to automatically discover, score, and store relevant research papers from arXiv based on your interests.

## Features

- **Automated Discovery**: Fetches recent papers from arXiv based on configurable categories and keywords
- **Relevance Scoring**: Uses keyword matching, category filtering, and semantic analysis to score paper relevance
- **Local Storage**: Stores papers in a SQLite database with metadata and relevance scores
- **Paper Management**: Mark papers as read, star favorites, and add notes
- **Search Functionality**: Search for specific papers and topics
- **Configurable**: Easily customize keywords, categories, and scoring thresholds

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.py` to customize:

- **RELEVANCE_KEYWORDS**: Keywords that indicate papers of interest
- **SUBJECT_CATEGORIES**: arXiv categories to monitor (e.g., "cs.AI", "cs.LG")
- **MIN_RELEVANCE_SCORE**: Minimum score threshold for storing papers
- **DAYS_LOOKBACK**: How many days back to search for new papers

## Usage

### Discover New Papers
```bash
python main.py discover
python main.py discover --days 14  # Look back 14 days
```

### List Stored Papers
```bash
python main.py list
python main.py list --limit 10 --summary
python main.py list --min-relevance 0.5
```

### Search for Specific Papers
```bash
python main.py search "transformer language models"
python main.py search "computer vision" --limit 50
```

### View Statistics
```bash
python main.py stats
```

### Mark Papers
```bash
python main.py mark PAPER_ID read
python main.py mark PAPER_ID star
python main.py mark PAPER_ID unstar
```

## How It Works

1. **Paper Fetching**: Uses arXiv's API to fetch recent papers from specified categories
2. **Relevance Scoring**: Combines three scoring methods:
   - **Keyword Matching**: Exact and partial matches with your interest keywords
   - **Category Scoring**: Relevance based on arXiv subject categories
   - **Semantic Similarity**: TF-IDF cosine similarity between paper content and keywords
3. **Storage**: Papers above the relevance threshold are stored with metadata
4. **Management**: Track reading status, star favorites, and add personal notes

## Database Schema

Papers are stored with the following fields:
- Paper ID, title, summary, authors
- Publication dates and arXiv categories
- Relevance score and added date
- Reading status, starred status, and personal notes

## Logging

Set log level with `--log-level DEBUG|INFO|WARNING|ERROR` for detailed output during development.

## Examples

```bash
# Daily workflow: discover new papers
python main.py discover

# Review high-relevance papers
python main.py list --min-relevance 0.7 --summary

# Search for papers on a specific topic
python main.py search "federated learning"

# Check your reading progress
python main.py stats
```