# PDF Storage Setup Guide

This guide explains how to set up and use the PDF download and storage system for the ArXiv Reader.

## Overview

The PDF storage system uses Docker containers to provide:
- **MinIO**: S3-compatible object storage for PDF files
- **MongoDB**: Document database for metadata and relationships
- **Elasticsearch**: Full-text search capabilities
- **Apache Tika**: PDF text extraction service

## Prerequisites

1. Docker and Docker Compose installed
2. At least 10GB of free disk space (more for large collections)
3. Network access to download ArXiv PDFs

## Setup Instructions

### 1. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` to set:
- `NAS_PATH`: Path to your NAS mount point (e.g., `/Volumes/YourNAS/arxiv-papers`)
- Secure passwords for MinIO, MongoDB, and Elasticsearch

### 2. Start Docker Services

```bash
docker-compose up -d
```

This will start all required services. First-time startup may take a few minutes.

### 3. Verify Services

Check that all services are running:

```bash
docker-compose ps
```

You should see all services as "Up" and healthy.

Access the web interfaces:
- MinIO Console: http://localhost:9001
- Elasticsearch: http://localhost:9200

### 4. Migrate Existing Data (Optional)

If you have existing papers in SQLite:

```bash
python pdf_manager.py migrate --sqlite-path arxiv_papers.db
```

## Usage

### Download PDFs

Download PDFs for high-relevance papers (default: relevance > 0.7):

```bash
python main.py pdf download
```

Download with custom parameters:

```bash
# Download papers with relevance > 0.8, limit to 50
python main.py pdf download --min-relevance 0.8 --limit 50

# Download specific papers by ArXiv ID
python main.py pdf download --arxiv-ids 2312.12345 2401.67890
```

### Search Full Text

Search across all downloaded PDFs:

```bash
python main.py pdf search "transformer architecture"
```

### View Statistics

Check storage statistics:

```bash
python main.py pdf stats
```

## Storage Management

### Data Locations

- PDFs are stored in: `${NAS_PATH}/minio/`
- MongoDB data: `${NAS_PATH}/mongodb/`
- Elasticsearch indices: `${NAS_PATH}/elasticsearch/`

### Backup

To backup your data:

1. Stop the services: `docker-compose down`
2. Copy the entire `${NAS_PATH}` directory
3. Restart services: `docker-compose up -d`

### Storage Cleanup

To remove all stored PDFs (keeping metadata):

```bash
docker exec -it arxiv-minio mc rm --recursive --force myminio/arxiv-pdfs
```

## Troubleshooting

### Services Won't Start

Check Docker logs:
```bash
docker-compose logs [service-name]
```

Common issues:
- Port conflicts: Change ports in `docker-compose.yml`
- Permission issues: Ensure NAS mount has write permissions
- Memory issues: Increase Docker memory allocation

### PDF Download Failures

- Check network connectivity
- Verify ArXiv is accessible
- Check MinIO storage space
- Review logs: `python main.py pdf download --log-level DEBUG`

### Search Not Working

Rebuild Elasticsearch indices:
```bash
# In Python
from document_store import DocumentStore
ds = DocumentStore()
# Re-index all documents
```

## Performance Tips

1. **Batch Downloads**: Download in batches to avoid overwhelming ArXiv
2. **Storage**: Use SSD for Elasticsearch data for better search performance
3. **Memory**: Allocate at least 2GB RAM to Docker
4. **Network**: Use wired connection for faster PDF downloads

## Integration with Main Workflow

The PDF storage integrates seamlessly with the existing ArXiv reader:

1. Discover papers: `python main.py discover`
2. Review high-relevance papers: `python main.py list --min-relevance 0.7`
3. Download PDFs: `python main.py pdf download`
4. Search full text: `python main.py pdf search "your query"`

## API Access

For programmatic access:

```python
from pdf_manager import PDFManager

manager = PDFManager()

# Download PDFs
results = manager.download_papers_by_relevance(min_relevance=0.8)

# Search
search_results = manager.search_full_text("neural networks")

# Get paper with full text
paper = manager.get_paper_with_text("2312.12345")
print(paper['full_text'][:1000])
```