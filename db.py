"""Database layer for Anum Papers Database."""

import sqlite3
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from models import Entry, Author, EntryAuthor


class Database:
    """Database connection and operations."""
    
    def __init__(self, db_path: str = "anum_papers.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def _ensure_connected(self):
        """Ensure database connection is active."""
        if not self.conn:
            self.connect()
        try:
            # Test the connection
            self.conn.execute("SELECT 1").fetchone()
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            # Connection is dead, reconnect
            self.connect()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def initialize(self, schema_path: str = "schema.sql"):
        """Initialize database schema from SQL file.
        
        Args:
            schema_path: Path to schema SQL file
        """
        if not self.conn:
            self.connect()
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        self.conn.executescript(schema_sql)
        self.conn.commit()
    
    # Entry operations
    
    def check_duplicate(self, entry: Entry) -> Optional[int]:
        """Check if an entry already exists in the database.
        
        Checks for duplicates using:
        1. DOI (if available) - most reliable
        2. Title + year (if no DOI)
        3. Title + first author (if no year)
        
        Args:
            entry: Entry object to check
            
        Returns:
            Entry ID if duplicate found, None otherwise
        """
        if not self.conn:
            self.connect()
        
        # Strategy 1: Check by DOI (most reliable)
        if entry.doi:
            row = self.conn.execute(
                "SELECT id FROM entries WHERE doi = ?", (entry.doi,)
            ).fetchone()
            if row:
                return row['id']
        
        # Strategy 2: Check by title + year
        if entry.title and entry.year:
            # Normalize title for comparison (lowercase, strip whitespace)
            title_normalized = entry.title.lower().strip()
            rows = self.conn.execute(
                "SELECT id FROM entries WHERE LOWER(TRIM(title)) = ? AND year = ?",
                (title_normalized, entry.year)
            ).fetchall()
            
            if rows:
                # If we have multiple matches, also check authors if available
                # Get authors for this entry (if we have them)
                # For now, return first match
                return rows[0]['id']
        
        # Strategy 3: Check by title + first author
        if entry.title:
            title_normalized = entry.title.lower().strip()
            # Try to find entries with same title and check if they have matching authors
            rows = self.conn.execute(
                "SELECT id FROM entries WHERE LOWER(TRIM(title)) = ?",
                (title_normalized,)
            ).fetchall()
            
            if rows:
                # If we have author information, we could check authors here
                # For now, if title matches exactly and no year/DOI, consider it a potential duplicate
                # Return first match
                return rows[0]['id']
        
        return None
    
    def create_entry(self, entry: Entry, check_duplicate: bool = True) -> Tuple[int, bool]:
        """Create a new entry, checking for duplicates first.
        
        Args:
            entry: Entry object to create
            check_duplicate: Whether to check for duplicates (default: True)
            
        Returns:
            Tuple of (entry_id, is_new) where is_new is True if entry was created, False if duplicate found
        """
        if not self.conn:
            self.connect()
        
        # Check for duplicates first
        if check_duplicate:
            existing_id = self.check_duplicate(entry)
            if existing_id:
                return (existing_id, False)
        
        now = datetime.now()
        entry.created_at = now
        entry.updated_at = now
        
        cursor = self.conn.execute("""
            INSERT INTO entries (type, title, year, venue, volume, issue, pages, 
                               doi, abstract_number, date, location, status,
                               abstract, url, keywords, subject_area, citation_count,
                               anum_position, project_area, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.type, entry.title, entry.year, entry.venue, entry.volume,
            entry.issue, entry.pages, entry.doi, entry.abstract_number,
            entry.date, entry.location, entry.status,
            entry.abstract, entry.url, entry.keywords, entry.subject_area, entry.citation_count,
            entry.anum_position, entry.project_area, entry.created_at, entry.updated_at
        ))
        
        self.conn.commit()
        return (cursor.lastrowid, True)
    
    def get_entry(self, entry_id: int) -> Optional[Entry]:
        """Get entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Entry object or None if not found
        """
        if not self.conn:
            self.connect()
        
        row = self.conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        
        if row:
            return Entry.from_dict(dict(row))
        return None
    
    def get_all_entries(self, entry_type: Optional[str] = None, 
                       year: Optional[int] = None,
                       project_area: Optional[str] = None) -> List[Entry]:
        """Get all entries, optionally filtered by type, year, and/or project_area.
        
        Args:
            entry_type: Optional filter by entry type
            year: Optional filter by year
            project_area: Optional filter by project area
            
        Returns:
            List of Entry objects
        """
        if not self.conn:
            self.connect()
        
        query = "SELECT * FROM entries WHERE 1=1"
        params = []
        
        if entry_type:
            query += " AND type = ?"
            params.append(entry_type)
        
        if year:
            query += " AND year = ?"
            params.append(year)
        
        if project_area:
            query += " AND project_area = ?"
            params.append(project_area)
        
        query += " ORDER BY year DESC, id DESC"
        
        rows = self.conn.execute(query, params).fetchall()
        return [Entry.from_dict(dict(row)) for row in rows]
    
    def get_entries_by_project_area(self, project_area: str) -> List[Entry]:
        """Get all entries for a specific project area.
        
        Args:
            project_area: Project area identifier (snake_case)
            
        Returns:
            List of Entry objects
        """
        return self.get_all_entries(project_area=project_area)
    
    def update_entry(self, entry: Entry) -> bool:
        """Update an existing entry.
        
        Args:
            entry: Entry object with updated data (must have id)
            
        Returns:
            True if updated, False if entry not found
        """
        if not self.conn:
            self.connect()
        
        if entry.id is None:
            return False
        
        entry.updated_at = datetime.now()
        
        cursor = self.conn.execute("""
            UPDATE entries 
            SET type = ?, title = ?, year = ?, venue = ?, volume = ?, 
                issue = ?, pages = ?, doi = ?, abstract_number = ?, 
                date = ?, location = ?, status = ?,
                abstract = ?, url = ?, keywords = ?, subject_area = ?, citation_count = ?,
                anum_position = ?, project_area = ?, updated_at = ?
            WHERE id = ?
        """, (
            entry.type, entry.title, entry.year, entry.venue, entry.volume,
            entry.issue, entry.pages, entry.doi, entry.abstract_number,
            entry.date, entry.location, entry.status,
            entry.abstract, entry.url, entry.keywords, entry.subject_area, entry.citation_count,
            entry.anum_position, entry.project_area, entry.updated_at, entry.id
        ))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry (cascades to entry_authors).
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if not self.conn:
            self.connect()
        
        cursor = self.conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # Author operations
    
    def create_author(self, author: Author) -> int:
        """Create a new author or get existing one.
        
        Args:
            author: Author object to create
            
        Returns:
            ID of author (existing or newly created)
        """
        if not self.conn:
            self.connect()
        
        # Check if author already exists
        row = self.conn.execute(
            "SELECT id FROM authors WHERE name = ?", (author.name,)
        ).fetchone()
        
        if row:
            return row['id']
        
        # Create new author
        cursor = self.conn.execute(
            "INSERT INTO authors (name, is_anum) VALUES (?, ?)",
            (author.name, 1 if author.is_anum else 0)
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_author(self, author_id: int) -> Optional[Author]:
        """Get author by ID.
        
        Args:
            author_id: Author ID
            
        Returns:
            Author object or None if not found
        """
        if not self.conn:
            self.connect()
        
        row = self.conn.execute(
            "SELECT * FROM authors WHERE id = ?", (author_id,)
        ).fetchone()
        
        if row:
            return Author.from_dict(dict(row))
        return None
    
    def get_author_by_name(self, name: str) -> Optional[Author]:
        """Get author by name.
        
        Args:
            name: Author name
            
        Returns:
            Author object or None if not found
        """
        if not self.conn:
            self.connect()
        
        row = self.conn.execute(
            "SELECT * FROM authors WHERE name = ?", (name,)
        ).fetchone()
        
        if row:
            return Author.from_dict(dict(row))
        return None
    
    def get_all_authors(self) -> List[Author]:
        """Get all authors.
        
        Returns:
            List of Author objects
        """
        if not self.conn:
            self.connect()
        
        rows = self.conn.execute("SELECT * FROM authors ORDER BY name").fetchall()
        return [Author.from_dict(dict(row)) for row in rows]
    
    # Entry-Author relationship operations
    
    def add_entry_author(self, entry_author: EntryAuthor):
        """Add author to entry.
        
        Args:
            entry_author: EntryAuthor relationship object
        """
        if not self.conn:
            self.connect()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO entry_authors 
            (entry_id, author_id, position, is_first_author, is_corresponding)
            VALUES (?, ?, ?, ?, ?)
        """, (
            entry_author.entry_id, entry_author.author_id, entry_author.position,
            1 if entry_author.is_first_author else 0,
            1 if entry_author.is_corresponding else 0
        ))
        
        self.conn.commit()
    
    def get_entry_authors(self, entry_id: int) -> List[Dict[str, Any]]:
        """Get all authors for an entry with their details.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            List of dictionaries with author info and relationship details
        """
        if not self.conn:
            self.connect()
        
        rows = self.conn.execute("""
            SELECT a.id, a.name, a.is_anum, 
                   ea.position, ea.is_first_author, ea.is_corresponding
            FROM authors a
            JOIN entry_authors ea ON a.id = ea.author_id
            WHERE ea.entry_id = ?
            ORDER BY ea.position
        """, (entry_id,)).fetchall()
        
        return [dict(row) for row in rows]
    
    def remove_entry_author(self, entry_id: int, author_id: int):
        """Remove author from entry.
        
        Args:
            entry_id: Entry ID
            author_id: Author ID
        """
        if not self.conn:
            self.connect()
        
        self.conn.execute(
            "DELETE FROM entry_authors WHERE entry_id = ? AND author_id = ?",
            (entry_id, author_id)
        )
        self.conn.commit()
    
    def get_entries_by_author(self, author_id: int) -> List[Entry]:
        """Get all entries by a specific author.
        
        Args:
            author_id: Author ID
            
        Returns:
            List of Entry objects
        """
        if not self.conn:
            self.connect()
        
        rows = self.conn.execute("""
            SELECT e.* FROM entries e
            JOIN entry_authors ea ON e.id = ea.entry_id
            WHERE ea.author_id = ?
            ORDER BY e.year DESC, e.id DESC
        """, (author_id,)).fetchall()
        
        return [Entry.from_dict(dict(row)) for row in rows]

