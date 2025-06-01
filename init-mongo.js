// MongoDB initialization script
db = db.getSiblingDB('arxiv_papers');

// Create collections
db.createCollection('papers');
db.createCollection('pdfs');
db.createCollection('citations');
db.createCollection('full_text');

// Create indexes for better performance
db.papers.createIndex({ "arxiv_id": 1 }, { unique: true });
db.papers.createIndex({ "title": "text", "abstract": "text" });
db.papers.createIndex({ "relevance_score": -1 });
db.papers.createIndex({ "published_date": -1 });
db.papers.createIndex({ "categories": 1 });

db.pdfs.createIndex({ "arxiv_id": 1 }, { unique: true });
db.pdfs.createIndex({ "download_date": -1 });
db.pdfs.createIndex({ "file_size": 1 });

db.full_text.createIndex({ "arxiv_id": 1 }, { unique: true });
db.full_text.createIndex({ "content": "text" });

db.citations.createIndex({ "citing_paper": 1 });
db.citations.createIndex({ "cited_paper": 1 });

print("MongoDB initialized with arxiv_papers database and indexes");