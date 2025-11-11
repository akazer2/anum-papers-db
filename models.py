"""Data models for Anum Papers Database."""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class Entry:
    """Represents an academic entry (publication, presentation, etc.)."""
    id: Optional[int] = None
    type: str = ""  # 'publication', 'book_chapter', 'patent', 'oral_presentation', 'poster_abstract'
    title: str = ""
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    abstract_number: Optional[str] = None
    date: Optional[str] = None  # e.g., "October 2025"
    location: Optional[str] = None  # e.g., "Seattle, WA"
    status: Optional[str] = None  # for patents
    abstract: Optional[str] = None  # paper abstract
    url: Optional[str] = None  # URL to paper
    keywords: Optional[str] = None  # comma-separated keywords
    subject_area: Optional[str] = None  # subject area/category
    citation_count: Optional[int] = None  # number of citations
    anum_position: Optional[int] = None  # Anum's author position (1-based, NULL if not an author)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert entry to dictionary for database operations."""
        result = {
            'type': self.type,
            'title': self.title,
            'year': self.year,
            'venue': self.venue,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'doi': self.doi,
            'abstract_number': self.abstract_number,
            'date': self.date,
            'location': self.location,
            'status': self.status,
            'abstract': self.abstract,
            'url': self.url,
            'keywords': self.keywords,
            'subject_area': self.subject_area,
            'citation_count': self.citation_count,
            'anum_position': self.anum_position,
        }
        if self.id is not None:
            result['id'] = self.id
        if self.created_at:
            result['created_at'] = self.created_at
        if self.updated_at:
            result['updated_at'] = self.updated_at
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Entry':
        """Create entry from dictionary (e.g., from database row)."""
        return cls(
            id=data.get('id'),
            type=data.get('type', ''),
            title=data.get('title', ''),
            year=data.get('year'),
            venue=data.get('venue'),
            volume=data.get('volume'),
            issue=data.get('issue'),
            pages=data.get('pages'),
            doi=data.get('doi'),
            abstract_number=data.get('abstract_number'),
            date=data.get('date'),
            location=data.get('location'),
            status=data.get('status'),
            abstract=data.get('abstract'),
            url=data.get('url'),
            keywords=data.get('keywords'),
            subject_area=data.get('subject_area'),
            citation_count=data.get('citation_count'),
            anum_position=data.get('anum_position'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class Author:
    """Represents an author."""
    id: Optional[int] = None
    name: str = ""
    is_anum: bool = False
    
    def to_dict(self) -> dict:
        """Convert author to dictionary for database operations."""
        result = {
            'name': self.name,
            'is_anum': 1 if self.is_anum else 0,
        }
        if self.id is not None:
            result['id'] = self.id
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Author':
        """Create author from dictionary (e.g., from database row)."""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            is_anum=bool(data.get('is_anum', 0)),
        )


@dataclass
class EntryAuthor:
    """Represents the relationship between an entry and an author."""
    entry_id: int
    author_id: int
    position: int  # 1-based author order
    is_first_author: bool = False
    is_corresponding: bool = False
    
    def to_dict(self) -> dict:
        """Convert entry-author relationship to dictionary for database operations."""
        return {
            'entry_id': self.entry_id,
            'author_id': self.author_id,
            'position': self.position,
            'is_first_author': 1 if self.is_first_author else 0,
            'is_corresponding': 1 if self.is_corresponding else 0,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EntryAuthor':
        """Create entry-author relationship from dictionary."""
        return cls(
            entry_id=data['entry_id'],
            author_id=data['author_id'],
            position=data['position'],
            is_first_author=bool(data.get('is_first_author', 0)),
            is_corresponding=bool(data.get('is_corresponding', 0)),
        )

