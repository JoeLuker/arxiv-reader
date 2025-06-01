# ArXiv Paper Reader

A comprehensive Python tool to automatically discover, score, store, and search relevant research papers from arXiv with full PDF download and full-text search capabilities.

## Features

### Core Functionality
- **Automated Discovery**: Fetches recent papers from arXiv based on configurable categories and keywords
- **Advanced Relevance Scoring**: Uses semantic embeddings, keyword matching, and citation analysis
- **Local Storage**: Stores papers in SQLite database with metadata and relevance scores
- **Paper Management**: Mark papers as read and star favorites

### PDF Storage & Search System
- **PDF Download**: Automatically download and store PDFs for high-relevance papers
- **Full-Text Extraction**: Extract text content from PDFs using Apache Tika
- **Full-Text Search**: Search across downloaded paper content using ZincSearch
- **Distributed Storage**: MinIO (S3-compatible), MongoDB, and ZincSearch in Docker containers
- **NAS Integration**: Configure storage to use your Network Attached Storage

## Installation

### Basic Setup
1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### PDF Storage Setup (Optional)
For full PDF download and search capabilities:

1. Install Docker and Docker Compose
2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env to set your NAS path and secure passwords
   ```
3. Start Docker services:
   ```bash
   docker-compose up -d
   ```

See [PDF_STORAGE_README.md](PDF_STORAGE_README.md) for detailed setup instructions.

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

### PDF Management
```bash
# Download PDFs for high-relevance papers
python main.py pdf download --min-relevance 0.7

# Download specific papers
python main.py pdf download --arxiv-ids 2312.12345 2401.67890

# Search full-text content
python main.py pdf search "transformer architecture"

# View PDF storage statistics
python main.py pdf stats
```

## How It Works

### Paper Discovery & Scoring
1. **Paper Fetching**: Uses arXiv's API to fetch recent papers from specified categories
2. **Advanced Relevance Scoring**: Combines multiple scoring methods:
   - **Semantic Similarity**: Uses sentence transformers (all-MiniLM-L6-v2) for semantic matching
   - **Keyword Matching**: Exact and partial matches with your interest keywords
   - **Citation Analysis**: Evaluates citation patterns and academic impact
   - **Category Scoring**: Relevance based on arXiv subject categories
3. **Storage**: Papers above the relevance threshold are stored with metadata
4. **Management**: Track reading status and star favorites

### PDF Storage & Search Architecture
1. **PDF Download**: Downloads PDFs from arXiv for high-relevance papers
2. **Text Extraction**: Uses Apache Tika to extract full text from PDFs
3. **Storage Distribution**:
   - **MinIO**: S3-compatible object storage for PDF files
   - **MongoDB**: Document metadata, relationships, and extracted text
   - **ZincSearch**: Lightweight full-text search index
4. **Search**: Fast full-text search across all downloaded papers

## Storage Schema

### SQLite Database (Core Papers)
- Paper ID, title, summary, authors
- Publication dates and arXiv categories  
- Relevance score and added date
- Reading status and starred status

### PDF Storage System
- **MinIO**: Raw PDF files organized by ArXiv ID
- **MongoDB Collections**:
  - `papers`: Paper metadata and relationships
  - `pdfs`: PDF download tracking and file metadata
  - `full_text`: Extracted text content from PDFs
- **ZincSearch**: Full-text search index with paper content

## Logging

Set log level with `--log-level DEBUG|INFO|WARNING|ERROR` for detailed output during development.

## Examples

### Basic Workflow
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

### Advanced PDF Workflow
```bash
# Start PDF storage services
docker-compose up -d

# Download PDFs for papers you're interested in
python main.py pdf download --min-relevance 0.8

# Search full-text content across downloaded PDFs
python main.py pdf search "mechanistic interpretability"
python main.py pdf search "sparse autoencoder"

# Check storage usage
python main.py pdf stats
```

## Services & Ports

When using the PDF storage system, the following services run in Docker:

- **ZincSearch**: http://localhost:4080 (search interface)
- **MinIO Console**: http://localhost:9001 (file storage management) 
- **MongoDB**: localhost:27017 (document database)
- **Apache Tika**: localhost:9998 (text extraction service)

## Contributing

This tool is designed for mechanistic interpretability research. Feel free to customize the keywords, categories, and scoring methods in `config.py` to match your research interests.