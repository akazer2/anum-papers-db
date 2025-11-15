-- Anum Papers Database Schema
-- SQLite database schema for storing academic publications, presentations, and related work

-- Main entries table for all academic work
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('publication', 'book_chapter', 'patent', 'oral_presentation', 'poster_abstract')),
    title TEXT NOT NULL,
    year INTEGER,
    venue TEXT,  -- journal name, conference, book title, etc.
    volume TEXT,  -- for publications
    issue TEXT,  -- for publications
    pages TEXT,  -- page numbers or range
    doi TEXT,  -- DOI when available
    abstract_number TEXT,  -- for abstracts/posters
    date TEXT,  -- for presentations (e.g., "October 2025")
    location TEXT,  -- for presentations (e.g., "Seattle, WA")
    status TEXT,  -- for patents (e.g., "pending")
    abstract TEXT,  -- paper abstract
    url TEXT,  -- URL to paper
    keywords TEXT,  -- comma-separated keywords
    subject_area TEXT,  -- subject area/category
    citation_count INTEGER,  -- number of citations
    anum_position INTEGER,  -- Anum's author position (1-based, NULL if not an author)
    project_area TEXT,  -- project area assignment (tme_evolution, pet_mri, ex_vivo_biology, response_modeling)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_anum BOOLEAN DEFAULT 0
);

-- Many-to-many relationship between entries and authors
CREATE TABLE IF NOT EXISTS entry_authors (
    entry_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    position INTEGER NOT NULL,  -- author order (1-based)
    is_first_author BOOLEAN DEFAULT 0,  -- marked with * in data
    is_corresponding BOOLEAN DEFAULT 0,  -- if determinable
    PRIMARY KEY (entry_id, author_id),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type);
CREATE INDEX IF NOT EXISTS idx_entries_year ON entries(year);
CREATE INDEX IF NOT EXISTS idx_entries_venue ON entries(venue);
CREATE INDEX IF NOT EXISTS idx_entry_authors_entry_id ON entry_authors(entry_id);
CREATE INDEX IF NOT EXISTS idx_entry_authors_author_id ON entry_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_authors_is_anum ON authors(is_anum);
CREATE INDEX IF NOT EXISTS idx_entries_anum_position ON entries(anum_position);
CREATE INDEX IF NOT EXISTS idx_entries_project_area ON entries(project_area);

