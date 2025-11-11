# Anum Papers Database

A simple SQLite database layer for storing and managing academic publications, presentations, and related work.

## Overview

This database stores rich metadata about academic work including:
- Publications (journal articles)
- Book chapters
- Patent applications
- Oral presentations
- Poster presentations and abstracts

## Database Schema

The database consists of three main tables:

1. **entries** - Main table storing all academic work with metadata
2. **authors** - Author information
3. **entry_authors** - Many-to-many relationship between entries and authors with ordering

See `schema.sql` for complete schema definition.

## Setup

1. Initialize the database:
```python
from db import Database

db = Database("anum_papers.db")
db.initialize()  # Creates tables from schema.sql
db.close()
```

Or use as a context manager:
```python
with Database("anum_papers.db") as db:
    db.initialize()
```

## Usage

### Creating Entries

```python
from db import Database
from models import Entry, Author, EntryAuthor

with Database("anum_papers.db") as db:
    # Create an entry
    entry = Entry(
        type="publication",
        title="Time to Enhancement Measured From Ultrafast Dynamic Contrast-Enhanced MRI",
        year=2025,
        venue="Journal of Breast Imaging",
        doi="10.1093/jbi/wbae089"
    )
    entry_id = db.create_entry(entry)
    
    # Create authors
    author1 = Author(name="Kazerouni, A. S.", is_anum=True)
    author1_id = db.create_author(author1)
    
    author2 = Author(name="Chen, Y. A.")
    author2_id = db.create_author(author2)
    
    # Link authors to entry
    db.add_entry_author(EntryAuthor(
        entry_id=entry_id,
        author_id=author1_id,
        position=1,
        is_first_author=True
    ))
    db.add_entry_author(EntryAuthor(
        entry_id=entry_id,
        author_id=author2_id,
        position=2,
        is_first_author=True
    ))
```

### Querying Entries

```python
with Database("anum_papers.db") as db:
    # Get all publications
    publications = db.get_all_entries(entry_type="publication")
    
    # Get entries from a specific year
    entries_2025 = db.get_all_entries(year=2025)
    
    # Get a specific entry
    entry = db.get_entry(entry_id=1)
    
    # Get authors for an entry
    authors = db.get_entry_authors(entry_id=1)
    
    # Get all entries by an author
    author = db.get_author_by_name("Kazerouni, A. S.")
    if author:
        entries = db.get_entries_by_author(author.id)
```

### Updating and Deleting

```python
with Database("anum_papers.db") as db:
    # Update an entry
    entry = db.get_entry(entry_id=1)
    if entry:
        entry.title = "Updated Title"
        db.update_entry(entry)
    
    # Delete an entry (cascades to entry_authors)
    db.delete_entry(entry_id=1)
```

## Citation Parsing

The database includes a sophisticated citation parser that uses multiple strategies:

1. **GROBID** (optional) - Best parser for free-form citations. Requires GROBID server running.
2. **Crossref** (habanero) - DOI lookup and metadata enrichment
3. **OpenAlex** (pyalex) - Alternative metadata source when DOI unavailable
4. **Fallback regex parser** - Works when services unavailable

### Setting up GROBID (Optional but Recommended)

GROBID provides the most accurate citation parsing. To use it:

1. **Install GROBID** (requires Java):
   ```bash
   # Using Docker (recommended)
   docker pull lfoppiano/grobid:0.8.1
   docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1
   
   # Or download from: https://github.com/kermitt2/grobid
   ```

2. **Verify GROBID is running**:
   ```bash
   curl http://localhost:8070/api/isalive
   ```

3. The parser will automatically detect and use GROBID if available.

**Note**: GROBID is optional. The parser will fall back to Crossref/OpenAlex/regex if GROBID is not available.

## Streamlit App

A simple web interface for searching and browsing the database.

### Running the App

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure the database is initialized (see Setup above)

3. (Optional) Start GROBID server for best parsing accuracy:
```bash
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1
```

4. Run the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your browser with:
- Search functionality (by title, venue, keywords)
- Filters by entry type, year, and author
- Statistics sidebar
- Expandable entry details with author information
- **Citation parsing** - Paste citations to automatically extract metadata
  - Single citation input
  - Bulk upload (paste multiple citations)
  - Live query via Crossref API

## File Structure

- `schema.sql` - Database schema definitions
- `models.py` - Python data models (Entry, Author, EntryAuthor)
- `db.py` - Database connection and CRUD operations
- `app.py` - Streamlit web interface
- `requirements.txt` - Python dependencies

## Future Extensions

This database layer is designed to be extended with:
- Additional metadata fields
- Export capabilities
- Advanced search features
- Data import/export tools

