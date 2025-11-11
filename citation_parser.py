"""Citation parser for academic citations using proper libraries.

Parser stack (in order of preference):
1. GROBID - Best parser for free-form citations (requires GROBID server)
2. Crossref (habanero) - DOI lookup and metadata enrichment
3. OpenAlex (pyalex) - Alternative metadata source
4. Fallback regex parser - When libraries/services unavailable
5. CSL JSON parser - For Zotero exports
"""

import re
import json
import requests
from typing import Optional, Dict, List, Tuple, Union
from models import Entry, Author, EntryAuthor

# GROBID configuration (optional - requires GROBID server running)
GROBID_URL = "http://192.168.20.139:8070"  # GROBID server URL
GROBID_AVAILABLE = False

# Check if GROBID server is available
try:
    response = requests.get(f"{GROBID_URL}/api/isalive", timeout=2)
    if response.status_code == 200:
        GROBID_AVAILABLE = True
except:
    GROBID_AVAILABLE = False

try:
    from habanero import Crossref
    HABANERO_AVAILABLE = True
except ImportError:
    HABANERO_AVAILABLE = False

try:
    import pyalex
    OPENALEX_AVAILABLE = True
except ImportError:
    OPENALEX_AVAILABLE = False

try:
    from onecite import CitationParser
    ONECITE_AVAILABLE = True
except ImportError:
    ONECITE_AVAILABLE = False

# Anum's name variations
ANUM_NAMES = [
    "Kazerouni, A. S.",
    "Kazerouni, A.S.",
    "Syed, A. K.",
    "Syed, A.K.",
    "Syed A. K.",
    "Syed A.K.",
]

def normalize_author_name(name: str) -> str:
    """Normalize author name."""
    name = re.sub(r'\*+', '', name).strip()
    name = re.sub(r'\s+', ' ', name)
    return name

def is_anum_author(name: str) -> bool:
    """Check if author is Anum."""
    normalized = normalize_author_name(name)
    for anum_name in ANUM_NAMES:
        if normalize_author_name(anum_name).lower() == normalized.lower():
            return True
    return False

def parse_with_grobid(citation_text: str) -> Optional[Dict]:
    """Parse citation using GROBID server.
    
    GROBID is the most accurate parser for free-form citations.
    Requires GROBID server running at GROBID_URL.
    
    Args:
        citation_text: Citation string to parse
        
    Returns:
        Dictionary with parsed data or None if parsing fails
    """
    if not GROBID_AVAILABLE:
        return None
    
    try:
        # GROBID citation parsing endpoint
        # consolidateCitations=1 as query parameter, citations in form-urlencoded body
        response = requests.post(
            f"{GROBID_URL}/api/processCitation?consolidateCitations=1",
            data={
                'citations': citation_text
            },
            headers={'Accept': 'application/xml'},
            timeout=30  # Increased timeout for GROBID processing
        )
        
        if response.status_code == 200:
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            # GROBID returns XML - may or may not have TEI namespace
            # Try both namespaced and non-namespaced versions
            ns = '{http://www.tei-c.org/ns/1.0}'
            
            # Helper function to find elements with or without namespace
            def find_elem(path_ns, path_no_ns):
                elem = root.find(path_ns)
                if elem is None:
                    elem = root.find(path_no_ns)
                return elem
            
            def findall_elem(path_ns, path_no_ns):
                elems = root.findall(path_ns)
                if not elems:
                    elems = root.findall(path_no_ns)
                return elems
            
            # Extract fields from the XML
            authors = []
            for author in findall_elem('.//{ns}author'.format(ns=ns), './/author'):
                persname = author.find('.//{ns}persName'.format(ns=ns)) or author.find('.//persName')
                if persname is not None:
                    # Get all forenames and surname
                    forenames = persname.findall('.//{ns}forename'.format(ns=ns)) or persname.findall('.//forename')
                    surname_elem = persname.find('.//{ns}surname'.format(ns=ns)) or persname.find('.//surname')
                    
                    if surname_elem is not None:
                        surname_text = surname_elem.text or ''
                        given_texts = [f.text for f in forenames if f.text]
                        given_text = ' '.join(given_texts).strip()
                        if surname_text:
                            authors.append(f"{surname_text}, {given_text}".strip(', '))
            
            # Extract title - for book chapters, level="a" is chapter title, level="m" is book title
            # For articles, level="a" is article title, level="j" is journal title
            title_elem = find_elem('.//{ns}title[@level="a"]'.format(ns=ns), './/title[@level="a"]')
            title = title_elem.text if title_elem is not None and title_elem.text else None
            
            # Extract journal/venue - check for journal (level="j") or book (level="m")
            journal_elem = find_elem('.//{ns}title[@level="j"]'.format(ns=ns), './/title[@level="j"]')
            book_elem = find_elem('.//{ns}title[@level="m"]'.format(ns=ns), './/title[@level="m"]')
            venue = None
            if journal_elem is not None and journal_elem.text:
                venue = journal_elem.text
            elif book_elem is not None and book_elem.text:
                venue = book_elem.text
            
            # If we have a book title but no chapter title, the "title" might actually be the book
            # In that case, try to extract publisher info to identify it as a book
            publisher_elem = find_elem('.//{ns}publisher'.format(ns=ns), './/publisher')
            publisher = publisher_elem.text if publisher_elem is not None and publisher_elem.text else None
            
            # Extract year
            year_elem = find_elem('.//{ns}date'.format(ns=ns), './/date')
            year = None
            if year_elem is not None:
                year_attr = year_elem.get('when')
                if year_attr:
                    year = int(year_attr[:4]) if len(year_attr) >= 4 else None
                elif year_elem.text:
                    year_match = re.search(r'(\d{4})', year_elem.text)
                    if year_match:
                        year = int(year_match.group(1))
            
            # Extract volume, issue, pages
            biblscope = findall_elem('.//{ns}biblScope'.format(ns=ns), './/biblScope')
            volume = None
            issue = None
            pages = None
            for scope in biblscope:
                unit = scope.get('unit', '')
                text = scope.text
                if unit == 'volume':
                    volume = text
                elif unit == 'issue':
                    issue = text
                elif unit == 'page':
                    pages = text
            
            # Extract DOI
            idno = find_elem('.//{ns}idno[@type="DOI"]'.format(ns=ns), './/idno[@type="DOI"]')
            doi = idno.text if idno is not None and idno.text else None
            
            # Handle book chapters: if title starts with "in ", GROBID likely got it wrong
            # Extract the actual chapter title from before "in" in the citation
            if title and title.lower().startswith('in '):
                # Pattern: "Authors. Chapter Title. in Book Title (Publisher, Year)"
                # Try to extract chapter title from before "in"
                in_pos = citation_text.lower().find(' in ')
                if in_pos > 0:
                    before_in = citation_text[:in_pos]
                    # Find the chapter title (last sentence before "in", after authors)
                    parts = [p.strip() for p in before_in.split('.') if p.strip() and len(p.strip()) > 5]
                    if len(parts) >= 2:
                        # Last part before "in" is likely the chapter title
                        chapter_title = parts[-1].strip()
                        if len(chapter_title.split()) >= 3:  # Must be substantial
                            title = chapter_title
                            # Extract book title from the "in ..." part
                            after_in = citation_text[in_pos + 4:].strip()
                            # Remove publisher/year part: "Book Title (Publisher, Year)"
                            book_match = re.match(r'^([^(]+)', after_in)
                            if book_match:
                                venue = book_match.group(1).strip()
                            elif not venue and book_elem is not None:
                                venue = book_elem.text
            
            if title:
                return {
                    'title': title,
                    'authors': authors,
                    'venue': venue,
                    'year': year,
                    'volume': volume,
                    'issue': issue,
                    'pages': pages,
                    'doi': doi
                }
    except Exception as e:
        print(f"GROBID parsing error: {e}")
        return None
    
    return None

def lookup_openalex(citation_text: str, title: Optional[str] = None, 
                    authors: Optional[List[str]] = None, year: Optional[int] = None) -> Optional[Dict]:
    """Look up metadata from OpenAlex.
    
    OpenAlex is a free, open catalog of scholarly works.
    Great for metadata when DOI is not available.
    
    Args:
        citation_text: Original citation text
        title: Title if already known
        authors: List of authors if already known
        year: Year if already known
        
    Returns:
        Dictionary with enriched metadata or None
    """
    if not OPENALEX_AVAILABLE:
        return None
    
    try:
        import pyalex
        Works = pyalex.Works()
        
        # Try to search by title if available
        # Use search() instead of search_filter() for more robust searching
        if title and len(title.strip()) > 10:  # Only search if title is substantial
            try:
                # Use search() with title in quotes for phrase matching
                # Escape special characters and limit to reasonable length
                search_title = title[:200]  # Limit length
                results = Works.search(search_title).get()
                
                if results and len(results) > 0:
                    work = results[0]
                    
                    # Extract authors
                    work_authors = []
                    if 'authorships' in work:
                        for authorship in work.get('authorships', []):
                            author = authorship.get('author', {})
                            display_name = author.get('display_name', '')
                            if display_name:
                                work_authors.append(display_name)
                    
                    # Extract metadata
                    return {
                        'title': work.get('title', title),
                        'authors': work_authors if work_authors else authors,
                        'venue': work.get('primary_location', {}).get('source', {}).get('display_name'),
                        'year': work.get('publication_year'),
                        'doi': work.get('doi', '').replace('https://doi.org/', '') if work.get('doi') else None,
                        'url': work.get('open_access', {}).get('oa_url'),
                        'citation_count': work.get('cited_by_count'),
                        'abstract': work.get('abstract'),
                        'keywords': ', '.join([concept.get('display_name', '') for concept in work.get('concepts', [])[:5]])
                    }
            except Exception as search_error:
                # Silently fail - OpenAlex search can be finicky
                # Don't print errors for every failed search as it's expected
                pass
    except Exception as e:
        # Only print unexpected errors (not search failures)
        if "Invalid query parameter" not in str(e):
            print(f"OpenAlex lookup error: {e}")
        return None
    
    return None

def extract_doi(citation_text: str) -> Optional[str]:
    """Extract DOI from citation text or URL."""
    # Look for doi: prefix
    doi_match = re.search(r'doi:([^\s\)]+)', citation_text, re.IGNORECASE)
    if doi_match:
        return doi_match.group(1).strip()
    
    # Look for DOI URL
    doi_url_match = re.search(r'https?://(?:dx\.)?doi\.org/([^\s\)]+)', citation_text, re.IGNORECASE)
    if doi_url_match:
        return doi_url_match.group(1).strip()
    
    return None

def extract_doi_from_url(url: str) -> Optional[str]:
    """Extract DOI from a URL (e.g., https://doi.org/10.1093/jbi/wbae089)."""
    if not url:
        return None
    doi_match = re.search(r'https?://(?:dx\.)?doi\.org/([^\s\)]+)', url, re.IGNORECASE)
    if doi_match:
        return doi_match.group(1).strip()
    return None

def lookup_doi_metadata(doi: str) -> Optional[Dict]:
    """Look up metadata from DOI using habanero/Crossref.
    
    Returns comprehensive metadata including:
    - All authors (properly formatted)
    - Title, venue, year, volume, issue, pages
    - Abstract, URL, keywords, subject areas
    - Citation count
    """
    if not HABANERO_AVAILABLE:
        return None
    
    # Clean DOI - remove any URL prefixes
    doi_clean = doi.strip()
    if doi_clean.startswith('doi:'):
        doi_clean = doi_clean[4:].strip()
    if doi_clean.startswith('https://doi.org/'):
        doi_clean = doi_clean[16:].strip()
    if doi_clean.startswith('http://dx.doi.org/'):
        doi_clean = doi_clean[18:].strip()
    
    max_retries = 2
    timeout_seconds = 30
    msg = None
    
    for attempt in range(max_retries):
        try:
            # Configure Crossref with timeout and follow redirects
            cr = Crossref(timeout=timeout_seconds)
            
            # Try to lookup the DOI
            result = cr.works(ids=[doi_clean])
            
            if not result or len(result) == 0:
                return None
            
            # Crossref returns a list, get first result
            if isinstance(result, list):
                if len(result) == 0:
                    return None
                msg = result[0].get('message', {}) if isinstance(result[0], dict) else {}
            else:
                msg = result.get('message', {}) if isinstance(result, dict) else {}
            
            if not msg:
                return None
            break  # Success, exit retry loop
            
        except Exception as e:
            error_str = str(e)
            
            # Handle redirect errors - extract new DOI from redirect location
            if '301' in error_str or 'Redirect' in error_str or 'Moved Permanently' in error_str:
                # Try to extract the new DOI from the redirect location
                # Pattern: "Redirect location: '/works/10.1158/1538-7445.am2019-296'"
                import re
                redirect_match = re.search(r"/works/([^\s']+)", error_str)
                if redirect_match:
                    new_doi = redirect_match.group(1)
                    if new_doi != doi_clean:
                        # Retry with the new DOI
                        doi_clean = new_doi
                        continue
            
            # Handle timeout errors - retry with longer timeout
            if 'timeout' in error_str.lower() or 'ReadTimeout' in error_str:
                if attempt < max_retries - 1:
                    timeout_seconds = timeout_seconds * 2  # Double timeout for retry
                    continue
                else:
                    # Last attempt failed, return None silently
                    return None
            
            # For other errors, print and return None
            if attempt == max_retries - 1:  # Only print on last attempt
                print(f"Error looking up DOI {doi_clean}: {e}")
            return None
    
    # If we get here, we successfully retrieved metadata
    if not msg:
        return None
    
    # Extract authors - FIX: properly handle all authors
    authors = []
    if 'author' in msg and msg['author']:
        for author in msg['author']:
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                # Format as "Last, First" or just "Last" if no first name
                if given:
                    author_name = f"{family}, {given}"
                else:
                    author_name = family
                authors.append(author_name)
    
    # Extract title
    title = None
    if 'title' in msg and msg['title']:
        title = msg['title'][0] if isinstance(msg['title'], list) else msg['title']
    
    # Extract journal/venue
    venue = None
    if 'container-title' in msg and msg['container-title']:
        venue = msg['container-title'][0] if isinstance(msg['container-title'], list) else msg['container-title']
    
    # Extract year
    year = None
    if 'published-print' in msg and msg['published-print'].get('date-parts'):
        year = msg['published-print']['date-parts'][0][0]
    elif 'published-online' in msg and msg['published-online'].get('date-parts'):
        year = msg['published-online']['date-parts'][0][0]
    elif 'issued' in msg and msg['issued'].get('date-parts'):
        year = msg['issued']['date-parts'][0][0]
    
    # Extract volume and issue
    volume = msg.get('volume')
    issue = msg.get('issue')
    
    # Extract pages
    pages = None
    if 'page' in msg:
        pages = msg['page']
    
    # Extract abstract
    abstract = None
    if 'abstract' in msg:
        # Abstract might be HTML, try to get plain text
        abstract_text = msg['abstract']
        if isinstance(abstract_text, str):
            # Remove HTML tags if present
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract_text)
        elif isinstance(abstract_text, dict):
            abstract = abstract_text.get('text', '')
    
    # Extract URL
    url = None
    if 'URL' in msg:
        url = msg['URL']
    elif 'link' in msg and msg['link']:
        # Get first URL from links
        if isinstance(msg['link'], list) and len(msg['link']) > 0:
            url = msg['link'][0].get('URL', '')
    
    # Extract keywords
    keywords = None
    if 'subject' in msg and msg['subject']:
        keywords_list = msg['subject'] if isinstance(msg['subject'], list) else [msg['subject']]
        keywords = ', '.join(kw for kw in keywords_list if kw)
    
    # Extract subject area
    subject_area = None
    if 'subject' in msg and msg['subject']:
        # Use first subject as primary area
        if isinstance(msg['subject'], list) and len(msg['subject']) > 0:
            subject_area = msg['subject'][0]
        elif isinstance(msg['subject'], str):
            subject_area = msg['subject']
    
    # Extract citation count (if available)
    citation_count = None
    if 'is-referenced-by-count' in msg:
        citation_count = msg['is-referenced-by-count']
    
    return {
        'title': title,
        'authors': authors,
        'venue': venue,
        'year': year,
        'volume': str(volume) if volume else None,
        'issue': str(issue) if issue else None,
        'pages': pages,
        'doi': doi_clean,  # Use cleaned DOI
        'abstract': abstract,
        'url': url,
        'keywords': keywords,
        'subject_area': subject_area,
        'citation_count': citation_count
    }

def parse_with_onecite(citation_text: str) -> Optional[Dict]:
    """Parse citation using onecite library."""
    if not ONECITE_AVAILABLE:
        return None
    
    try:
        parser = CitationParser()
        result = parser.parse(citation_text)
        
        if result:
            # Convert onecite format to our format
            authors = []
            if 'authors' in result:
                for author in result['authors']:
                    if isinstance(author, dict):
                        # Format: {first: "John", last: "Doe"}
                        first = author.get('first', '')
                        last = author.get('last', '')
                        if last:
                            authors.append(f"{last}, {first}".strip(', '))
                    elif isinstance(author, str):
                        authors.append(author)
            
            return {
                'title': result.get('title'),
                'authors': authors,
                'venue': result.get('journal') or result.get('venue'),
                'year': result.get('year'),
                'volume': str(result.get('volume')) if result.get('volume') else None,
                'issue': str(result.get('issue')) if result.get('issue') else None,
                'pages': result.get('pages'),
                'doi': result.get('doi')
            }
    except Exception as e:
        print(f"Error parsing with onecite: {e}")
        return None
    
    return None

def parse_citation_fallback(citation_text: str) -> Optional[Dict]:
    """Fallback parser using regex when libraries aren't available."""
    citation_text = citation_text.strip()
    if not citation_text or len(citation_text) < 20:
        return None
    
    # Extract year
    year_match = re.search(r'\((\d{4})\)', citation_text)
    year = int(year_match.group(1)) if year_match else None
    
    # Extract DOI
    doi = extract_doi(citation_text)
    
    # Extract volume/issue/article number
    volume = None
    issue = None
    pages = None
    detected_venue_from_vol = None  # Store venue if found in volume pattern
    
    # Pattern 1: "Radiology 316, e241629" or "Journal Name 316, e241629" - volume and article ID
    # Look for pattern: [Journal Name] [number], [e?number]
    vol_article_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*,\s*([a-z]?\d+)', citation_text)
    if vol_article_match:
        potential_venue = vol_article_match.group(1)
        vol_num = vol_article_match.group(2)
        article_id = vol_article_match.group(3)
        
        # Check if it looks like a journal name (short, capitalized, before year)
        vol_pos = vol_article_match.start()
        year_pos = citation_text.find(f"({year})") if year else len(citation_text)
        
        if vol_pos < year_pos and len(potential_venue.split()) <= 3:
            detected_venue_from_vol = potential_venue
            volume = vol_num
            # Article IDs like "e241629" go in pages field
            if article_id.startswith('e') or article_id.startswith('E') or article_id.startswith('a') or article_id.startswith('A'):
                pages = article_id
            else:
                # Could be issue number
                issue = article_id
    
    # Pattern 2: Traditional "vol. X, no. Y" or "X, Y"
    if not volume:
        vol_issue_match = re.search(r'(?:vol\.?\s*)?(\d+)\s*,\s*(?:no\.?\s*)?(\d+)', citation_text, re.IGNORECASE)
        if vol_issue_match:
            volume = vol_issue_match.group(1)
            issue = vol_issue_match.group(2)
    
    # Pattern 3: Just volume number
    if not volume:
        vol_match = re.search(r'\b(\d{3,4})\s*,', citation_text)
        if vol_match:
            # Check if it's likely a volume (appears after venue, before year)
            vol_pos = vol_match.start()
            year_pos = citation_text.find(f"({year})") if year else -1
            if year_pos > vol_pos:
                volume = vol_match.group(1)
    
    # Extract pages (traditional format)
    if not pages:
        pages_match = re.search(r'pp\.\s*([^,\s]+)', citation_text, re.IGNORECASE)
        if pages_match:
            pages = pages_match.group(1)
    
    # Find where title likely starts (after authors section)
    # Authors section typically ends with a period followed by capitalized title
    # Look for pattern: ... Initials. Title (title starts with capital, is long)
    
    # First, try to find title by looking for long capitalized phrases after periods
    title_start_pos = None
    for match in re.finditer(r'\.\s+([A-Z][^.]{20,})', citation_text):
        # Found a period followed by a long capitalized phrase - likely the title
        title_start_pos = match.start()
        break
    
    # If we found title start, extract authors from before it
    if title_start_pos:
        author_text = citation_text[:title_start_pos].strip()
    else:
        # Fallback: split by period and use first part
        parts = [p.strip() for p in citation_text.split('.') if p.strip() and len(p.strip()) > 1]
        if len(parts) < 2:
            return None
        author_text = parts[0]
    
    # Parse authors - handle "&" before last author
    authors = []
    
    # Replace " & " with ", " for consistent parsing
    author_text = author_text.replace(' & ', ', ')
    
    # Pattern: LastName, First Initial., LastName, First Initial.
    # Strategy: Split by comma, then pair up LastName with following Initials
    
    author_parts = [p.strip() for p in author_text.split(',') if p.strip()]
    
    # Reconstruct authors by pairing LastName with Initials
    # Each author follows pattern: "LastName, Initials."
    i = 0
    while i < len(author_parts):
        current = author_parts[i]
        
        # Look ahead to find the initials (next part that ends with period)
        if i + 1 < len(author_parts):
            next_part = author_parts[i + 1]
            
            # Check if next part ends with period (it's initials)
            if next_part.endswith('.'):
                # Standard case: "LastName, Initials."
                author_name = f"{current}, {next_part}".rstrip('*')
                normalized = normalize_author_name(author_name)
                if normalized:
                    authors.append(normalized)
                i += 2
            elif '.' in next_part and len(next_part) <= 6:
                # Next part has dots and is short - likely initials like "S. C" (missing final period)
                # Check if there's a third part or if this is the end
                if i + 2 >= len(author_parts) or not author_parts[i + 2].strip():
                    # This is likely the last author's initials (period was lost in splitting)
                    author_name = f"{current}, {next_part}.".rstrip('*')
                    normalized = normalize_author_name(author_name)
                    if normalized:
                        authors.append(normalized)
                    i += 2
                else:
                    # There's more, so next_part might be part of a multi-word last name
                    # Continue to check for multi-word case
                    if i + 2 < len(author_parts):
                        third = author_parts[i + 2]
                        if third.endswith('.'):
                            # Multi-word last name
                            author_name = f"{current}, {next_part}, {third}".rstrip('*')
                            normalized = normalize_author_name(author_name)
                            if normalized:
                                authors.append(normalized)
                            i += 3
                        else:
                            # Not sure, try current as standalone
                            if current and len(current) >= 2:
                                normalized = normalize_author_name(current.rstrip('*'))
                                if normalized:
                                    authors.append(normalized)
                            i += 1
                    else:
                        i += 1
            elif i + 2 < len(author_parts):
                # Check if we have a multi-word last name like "Lavista Ferres"
                # Pattern: "Lavista", "Ferres", "J. M."
                third = author_parts[i + 2]
                if third.endswith('.'):
                    # Multi-word last name: "Lavista Ferres, J. M."
                    author_name = f"{current}, {next_part}, {third}".rstrip('*')
                    normalized = normalize_author_name(author_name)
                    if normalized:
                        authors.append(normalized)
                    i += 3
                else:
                    # Not sure what this is, try current as standalone
                    if current and len(current) >= 2:
                        normalized = normalize_author_name(current.rstrip('*'))
                        if normalized:
                            authors.append(normalized)
                    i += 1
            else:
                # No more parts, current might be incomplete but add if valid
                if current and len(current) >= 2:
                    normalized = normalize_author_name(current.rstrip('*'))
                    if normalized:
                        authors.append(normalized)
                i += 1
        else:
            # Last part only
            if current and len(current) >= 2:
                normalized = normalize_author_name(current.rstrip('*'))
                if normalized:
                    authors.append(normalized)
            i += 1
    
    # Check for book chapter pattern: "Authors. Chapter Title. in Book Title (Publisher, Year)."
    book_chapter_match = re.search(r'\.\s+([^.]{10,}?)\s*\.\s+in\s+([^(]+?)\s*\(([^)]+),\s*(\d{4})\)', citation_text, re.IGNORECASE)
    if book_chapter_match:
        chapter_title = book_chapter_match.group(1).strip()
        book_title = book_chapter_match.group(2).strip()
        publisher = book_chapter_match.group(3).strip()
        year = int(book_chapter_match.group(4))
        
        return {
            'title': chapter_title,
            'year': year,
            'venue': book_title,  # For book chapters, venue is the book title
            'volume': None,
            'issue': None,
            'pages': None,
            'doi': doi,
            'date': None,
            'location': None,
            'authors': authors,
            'first_author_positions': [1] if authors else []
        }
    
    # Now find title - split citation into parts for title extraction
    # But first, find where authors end more accurately
    # Authors typically end with a period after initials, followed by title
    # Look for pattern: "LastName, Initials. Title" where title starts with capital and is long
    
    # Find the end of authors section - look for pattern like "N. Title" where Title is capitalized
    author_end_pos = None
    # Try to find where authors end by looking for "Initial. Title" pattern
    # This handles cases like "M. N. In vitro..." where "In" starts the title
    for match in re.finditer(r'([A-Z]\.\s+[A-Z]\.\s+)([A-Z][a-z]+)', citation_text):
        # Found pattern like "M. N. In" - the word after is likely the start of the title
        potential_title_start = match.end() - len(match.group(2))
        # Check if this looks like a title start (capitalized word, not too short)
        if len(match.group(2)) >= 2:
            author_end_pos = match.start()
            break
    
    # If we didn't find it that way, try simpler pattern: look for period followed by capitalized word
    if not author_end_pos:
        for match in re.finditer(r'\.\s+([A-Z][a-z]{2,})\s', citation_text):
            # Check if the word before the period looks like author initials
            before_period = citation_text[max(0, match.start()-10):match.start()]
            if re.search(r'[A-Z]\.\s*$', before_period):
                author_end_pos = match.start()
                break
    
    # Split citation into parts
    parts = [p.strip() for p in citation_text.split('.') if p.strip() and len(p.strip()) > 1]
    
    if len(parts) < 2:
        return None
    
    # Find title - it's usually the longest sentence-like part after authors
    # Exclude parts that look like author names, years, DOIs, or very short parts
    title = None
    title_index = None
    title_candidates = []
    
    # Start from part 1 (skip part 0 which is authors)
    for i, part in enumerate(parts[1:], 1):
        part_lower = part.lower()
        # Skip if it looks like:
        # - A year in parentheses: "(2020)"
        # - A DOI: "doi:10..."
        # - Very short: less than 10 chars
        # - Starts with number (likely volume/issue)
        # - Contains only initials pattern
        if (len(part) < 10 or 
            part.startswith('(') or 
            'doi:' in part_lower or 
            part[0].isdigit() or
            re.match(r'^[A-Z]\.\s*[A-Z]\.?$', part.strip())):
            continue
        
        # Good candidate if it has multiple words and doesn't look like author initials
        word_count = len(part.split())
        if word_count > 3:
            title_candidates.append((len(part), word_count, i, part))
    
    if title_candidates:
        # Prefer longer titles with more words
        title = max(title_candidates, key=lambda x: (x[1], x[0]))[3]
        title_index = max(title_candidates, key=lambda x: (x[1], x[0]))[2]
    elif len(parts) > 1:
        # Fallback: use second part if it's substantial
        if len(parts[1].split()) > 3:
            title = parts[1]
            title_index = 1
        else:
            return None
    
    if not title:
        return None
    
    # Find venue - comes after title, before year/DOI
    venue = detected_venue_from_vol
    
    if not venue:
        # Find the part that comes after the title using the title_index we already found
        venue_candidate = None
        if title_index is not None and title_index + 1 < len(parts):
            venue_candidate = parts[title_index + 1]
        else:
            # Fallback: search for title in parts
            found_title_index = None
            for i, part in enumerate(parts):
                if title and title in part:
                    found_title_index = i
                    break
            
            if found_title_index is not None and found_title_index + 1 < len(parts):
                venue_candidate = parts[found_title_index + 1]
        
        if venue_candidate:
            # Clean up venue - remove article IDs, volume numbers, etc.
            # Pattern: "Biotechnology and Bioengineering bit.27487" -> "Biotechnology and Bioengineering"
            # Remove patterns like "bit.27487", "vol.123", etc.
            venue_clean = re.sub(r'\s+[a-z]+\.\d+', '', venue_candidate, flags=re.IGNORECASE)
            venue_clean = re.sub(r'\s+vol\.?\s*\d+', '', venue_clean, flags=re.IGNORECASE)
            venue_clean = re.sub(r'\s+\d+', '', venue_clean)  # Remove standalone numbers
            venue_clean = venue_clean.strip()
            
            # Check if it looks like a journal/venue name
            if venue_clean:
                # Check if it's a known journal name pattern
                if any(kw in venue_clean for kw in ['Journal', 'Radiology', 'Cancer', 'Meeting', 'Symposium', 'Conference', 'Society', 'Press', 'Engineering', 'Science']):
                    venue = venue_clean
                # Or if it's 2-4 words and starts with capital
                elif 2 <= len(venue_clean.split()) <= 4 and venue_clean[0].isupper():
                    venue = venue_clean
                # Or if it's a single capitalized word (like "Nature", "Science")
                elif len(venue_clean.split()) == 1 and venue_clean[0].isupper() and len(venue_clean) > 3:
                    venue = venue_clean
    
    # Extract date and location for presentations
    date = None
    location = None
    date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', citation_text)
    if date_match:
        date = date_match.group(0)
    
    location_match = re.search(r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)$', citation_text)
    if location_match:
        location = f"{location_match.group(1)}, {location_match.group(2)}"
    
    if not title:
        return None
    
    # Check first authors
    first_author_indices = []
    author_section = citation_text[:citation_text.find(title)] if title in citation_text else parts[0]
    for i, author in enumerate(authors):
        if '*' in author_section and author in author_section:
            first_author_indices.append(i + 1)
    
    return {
        'title': title,
        'year': year,
        'venue': venue,
        'volume': volume,
        'issue': issue,
        'pages': pages,
        'doi': doi,
        'date': date,
        'location': location,
        'authors': authors,
        'first_author_positions': first_author_indices if first_author_indices else [1] if authors else []
    }

def parse_citation(citation_text: str, default_type: str = "publication") -> Optional[Dict]:
    """Parse a citation string into structured data.
    
    Uses multiple strategies (in order of preference):
    1. GROBID - Best parser for free-form citations (requires GROBID server)
    2. Crossref DOI lookup - If DOI found, get full metadata
    3. OpenAlex - Search by title/author for metadata enrichment
    4. Fallback regex parser - When services unavailable
    
    Args:
        citation_text: The citation string to parse
        default_type: Default entry type if not determinable
        
    Returns:
        Dictionary with parsed data or None if parsing fails
    """
    citation_text = citation_text.strip()
    if not citation_text or len(citation_text) < 20:
        return None
    
    def determine_entry_type(citation_lower: str) -> str:
        """Determine entry type from citation text.
        
        Respects the user-selected default_type, especially for oral_presentation vs poster_abstract.
        Only overrides when the citation clearly indicates a different type (patent, book_chapter).
        """
        # If user explicitly selected oral_presentation or poster_abstract, respect that choice
        if default_type in ['oral_presentation', 'poster_abstract']:
            # Only override if citation clearly indicates the opposite
            if default_type == 'oral_presentation' and ('poster' in citation_lower or 'abstract' in citation_lower):
                return 'poster_abstract'
            elif default_type == 'poster_abstract' and ('oral' in citation_lower or 'presentation' in citation_lower):
                return 'oral_presentation'
            # Otherwise, use the user's selection
            return default_type
        
        # For other types or generic "publication" default, try to auto-detect
        if any(kw in citation_lower for kw in ['meeting', 'symposium', 'conference', 'workshop', 'retreat', 'annual']):
            # Check for explicit oral presentation indicators
            if 'oral' in citation_lower or 'presentation' in citation_lower:
                return 'oral_presentation'
            # Check for explicit poster/abstract indicators
            elif 'poster' in citation_lower or 'abstract' in citation_lower:
                return 'poster_abstract'
            # Default to oral_presentation for meetings/symposia if no explicit indicator
            # (most presentations at these venues are oral unless explicitly marked as posters)
            else:
                return 'oral_presentation'
        elif 'patent' in citation_lower:
            return 'patent'
        elif 'chapter' in citation_lower:
            return 'book_chapter'
        return default_type
    
    def extract_first_author_positions(authors: List[str], citation_text: str, title: str) -> List[int]:
        """Extract first author positions marked with *."""
        first_author_indices = []
        if authors:
            author_section = citation_text[:citation_text.find(title)] if title in citation_text else ''
            for i, author in enumerate(authors, 1):
                if '*' in author_section and author.split(',')[0] in author_section:
                    first_author_indices.append(i)
        return first_author_indices if first_author_indices else [1] if authors else []
    
    # Strategy 1: Try GROBID (best parser for free-form citations)
    if GROBID_AVAILABLE:
        metadata = parse_with_grobid(citation_text)
        if metadata and metadata.get('title'):
            entry_type = determine_entry_type(citation_text.lower())
            first_author_indices = extract_first_author_positions(
                metadata.get('authors', []), citation_text, metadata['title']
            )
            
            # Enrich with Crossref if DOI found (from GROBID, extracted from text, or from URLs)
            doi = metadata.get('doi') or extract_doi(citation_text)
            # Also check if we can extract DOI from any URLs we might have
            if not doi and metadata.get('url'):
                doi = extract_doi_from_url(metadata.get('url'))
            
            if doi and HABANERO_AVAILABLE:
                if not metadata.get('doi'):
                    metadata['doi'] = doi  # Store extracted DOI
                crossref_metadata = lookup_doi_metadata(doi)
                if crossref_metadata:
                    # Merge GROBID + Crossref data (prefer GROBID for parsing, Crossref for enrichment)
                    metadata.update({
                        'abstract': crossref_metadata.get('abstract') or metadata.get('abstract'),
                        'url': crossref_metadata.get('url') or metadata.get('url'),
                        'keywords': crossref_metadata.get('keywords') or metadata.get('keywords'),
                        'subject_area': crossref_metadata.get('subject_area') or metadata.get('subject_area'),
                        'citation_count': crossref_metadata.get('citation_count') or metadata.get('citation_count'),
                    })
                    # If Crossref URL contains a DOI, extract it (in case we didn't have it before)
                    if crossref_metadata.get('url') and not metadata.get('doi'):
                        url_doi = extract_doi_from_url(crossref_metadata.get('url'))
                        if url_doi:
                            metadata['doi'] = url_doi
            
            # Also try OpenAlex enrichment if no DOI or if we want additional metadata
            if OPENALEX_AVAILABLE and metadata.get('title'):
                openalex_metadata = lookup_openalex(
                    citation_text,
                    title=metadata.get('title'),
                    authors=metadata.get('authors'),
                    year=metadata.get('year')
                )
                if openalex_metadata:
                    # Extract DOI from OpenAlex (from doi field or URL)
                    openalex_doi = openalex_metadata.get('doi')
                    if not openalex_doi and openalex_metadata.get('url'):
                        openalex_doi = extract_doi_from_url(openalex_metadata.get('url'))
                    
                    # If OpenAlex found a DOI we didn't have, use it for Crossref enrichment
                    if not doi and openalex_doi and HABANERO_AVAILABLE:
                        metadata['doi'] = openalex_doi
                        crossref_metadata = lookup_doi_metadata(openalex_doi)
                        if crossref_metadata:
                            # Merge Crossref data from OpenAlex-found DOI
                            metadata.update({
                                'abstract': crossref_metadata.get('abstract') or metadata.get('abstract'),
                                'url': crossref_metadata.get('url') or metadata.get('url'),
                                'keywords': crossref_metadata.get('keywords') or metadata.get('keywords'),
                                'subject_area': crossref_metadata.get('subject_area') or metadata.get('subject_area'),
                                'citation_count': crossref_metadata.get('citation_count') or metadata.get('citation_count'),
                            })
                    
                    # Merge OpenAlex data (only fill in missing fields)
                    if not metadata.get('abstract') and openalex_metadata.get('abstract'):
                        metadata['abstract'] = openalex_metadata.get('abstract')
                    if not metadata.get('url') and openalex_metadata.get('url'):
                        metadata['url'] = openalex_metadata.get('url')
                    if not metadata.get('keywords') and openalex_metadata.get('keywords'):
                        metadata['keywords'] = openalex_metadata.get('keywords')
                    if not metadata.get('citation_count') and openalex_metadata.get('citation_count'):
                        metadata['citation_count'] = openalex_metadata.get('citation_count')
            
            return {
                'type': entry_type,
                'title': metadata['title'],
                'year': metadata.get('year'),
                'venue': metadata.get('venue'),
                'volume': metadata.get('volume'),
                'issue': metadata.get('issue'),
                'pages': metadata.get('pages'),
                'doi': metadata.get('doi'),
                'abstract': metadata.get('abstract'),
                'url': metadata.get('url'),
                'keywords': metadata.get('keywords'),
                'subject_area': metadata.get('subject_area'),
                'citation_count': metadata.get('citation_count'),
                'authors': metadata.get('authors', []),
                'first_author_positions': first_author_indices
            }
    
    # Strategy 2: Try DOI lookup via Crossref (if DOI found)
    doi = extract_doi(citation_text)
    if doi and HABANERO_AVAILABLE:
        metadata = lookup_doi_metadata(doi)
        if metadata and metadata.get('title'):
            entry_type = determine_entry_type(citation_text.lower())
            first_author_indices = extract_first_author_positions(
                metadata.get('authors', []), citation_text, metadata['title']
            )
            
            return {
                'type': entry_type,
                'title': metadata['title'],
                'year': metadata.get('year'),
                'venue': metadata.get('venue'),
                'volume': metadata.get('volume'),
                'issue': metadata.get('issue'),
                'pages': metadata.get('pages'),
                'doi': doi,
                'abstract': metadata.get('abstract'),
                'url': metadata.get('url'),
                'keywords': metadata.get('keywords'),
                'subject_area': metadata.get('subject_area'),
                'citation_count': metadata.get('citation_count'),
                'authors': metadata.get('authors', []),
                'first_author_positions': first_author_indices
            }
    
    # Strategy 3: Try OpenAlex search (if no DOI)
    if OPENALEX_AVAILABLE:
        # First try fallback parser to get basic info
        fallback_parsed = parse_citation_fallback(citation_text)
        if fallback_parsed and fallback_parsed.get('title'):
            # Enrich with OpenAlex
            openalex_metadata = lookup_openalex(
                citation_text,
                title=fallback_parsed.get('title'),
                authors=fallback_parsed.get('authors'),
                year=fallback_parsed.get('year')
            )
            
            if openalex_metadata:
                # Merge fallback + OpenAlex (prefer OpenAlex for metadata)
                entry_type = determine_entry_type(citation_text.lower())
                authors = openalex_metadata.get('authors') or fallback_parsed.get('authors', [])
                first_author_indices = extract_first_author_positions(
                    authors, citation_text, openalex_metadata.get('title', fallback_parsed['title'])
                )
                
                # Get DOI from OpenAlex (doi field or URL), fallback parser, or extract from text
                doi = openalex_metadata.get('doi') or fallback_parsed.get('doi') or extract_doi(citation_text)
                # Also check URLs for DOIs
                if not doi and openalex_metadata.get('url'):
                    doi = extract_doi_from_url(openalex_metadata.get('url'))
                if not doi and fallback_parsed.get('url'):
                    doi = extract_doi_from_url(fallback_parsed.get('url'))
                
                # If we found a DOI, enrich with Crossref
                crossref_metadata = None
                if doi and HABANERO_AVAILABLE:
                    crossref_metadata = lookup_doi_metadata(doi)
                    # If Crossref URL contains a DOI, use it
                    if crossref_metadata and crossref_metadata.get('url'):
                        url_doi = extract_doi_from_url(crossref_metadata.get('url'))
                        if url_doi and url_doi != doi:
                            doi = url_doi  # Use the DOI from URL if different
                
                # Merge data: prefer Crossref if available, otherwise OpenAlex
                return {
                    'type': entry_type,
                    'title': openalex_metadata.get('title', fallback_parsed['title']),
                    'year': openalex_metadata.get('year') or fallback_parsed.get('year'),
                    'venue': openalex_metadata.get('venue') or fallback_parsed.get('venue'),
                    'volume': fallback_parsed.get('volume'),
                    'issue': fallback_parsed.get('issue'),
                    'pages': openalex_metadata.get('pages') or fallback_parsed.get('pages'),
                    'doi': doi,
                    'abstract': (crossref_metadata.get('abstract') if crossref_metadata else None) or openalex_metadata.get('abstract'),
                    'url': (crossref_metadata.get('url') if crossref_metadata else None) or openalex_metadata.get('url'),
                    'keywords': (crossref_metadata.get('keywords') if crossref_metadata else None) or openalex_metadata.get('keywords'),
                    'subject_area': crossref_metadata.get('subject_area') if crossref_metadata else None,
                    'citation_count': (crossref_metadata.get('citation_count') if crossref_metadata else None) or openalex_metadata.get('citation_count'),
                    'authors': authors,
                    'first_author_positions': first_author_indices
                }
    
    # Strategy 4: Fallback to regex parsing
    parsed = parse_citation_fallback(citation_text)
    if parsed:
        # Determine entry type - respect user's selection
        entry_type = default_type
        citation_lower = citation_text.lower()
        
        # If user explicitly selected oral_presentation or poster_abstract, respect that choice
        if default_type in ['oral_presentation', 'poster_abstract']:
            # Only override if citation clearly indicates the opposite
            if default_type == 'oral_presentation' and ('poster' in citation_lower or 'abstract' in citation_lower):
                entry_type = 'poster_abstract'
            elif default_type == 'poster_abstract' and ('oral' in citation_lower or 'presentation' in citation_lower):
                entry_type = 'oral_presentation'
            # Otherwise, use the user's selection (entry_type already set to default_type)
        elif any(kw in citation_lower for kw in ['meeting', 'symposium', 'conference', 'workshop', 'retreat', 'annual']):
            # Check for explicit oral presentation indicators
            if 'oral' in citation_lower or 'presentation' in citation_lower:
                entry_type = 'oral_presentation'
            # Check for explicit poster/abstract indicators
            elif 'poster' in citation_lower or 'abstract' in citation_lower:
                entry_type = 'poster_abstract'
            # Default to oral_presentation for meetings/symposia if no explicit indicator
            else:
                entry_type = 'oral_presentation'
        elif 'patent' in citation_lower:
            entry_type = 'patent'
            status_match = re.search(r'(pending|granted|issued)', citation_lower)
            if status_match:
                parsed['status'] = status_match.group(1)
        elif 'chapter' in citation_lower or 'book' in citation_lower:
            entry_type = 'book_chapter'
        
        parsed['type'] = entry_type
        if 'status' not in parsed:
            parsed['status'] = None
        
        # If fallback parser found a DOI (from doi field or URL), enrich with Crossref
        doi = parsed.get('doi') or extract_doi(citation_text)
        # Also check URLs for DOIs
        if not doi and parsed.get('url'):
            doi = extract_doi_from_url(parsed.get('url'))
        
        if doi and HABANERO_AVAILABLE:
            crossref_metadata = lookup_doi_metadata(doi)
            if crossref_metadata:
                # Merge fallback + Crossref (prefer Crossref for enrichment)
                parsed.update({
                    'doi': doi,
                    'abstract': crossref_metadata.get('abstract') or parsed.get('abstract'),
                    'url': crossref_metadata.get('url') or parsed.get('url'),
                    'keywords': crossref_metadata.get('keywords') or parsed.get('keywords'),
                    'subject_area': crossref_metadata.get('subject_area') or parsed.get('subject_area'),
                    'citation_count': crossref_metadata.get('citation_count') or parsed.get('citation_count'),
                })
                # If Crossref URL contains a DOI, extract it
                if crossref_metadata.get('url'):
                    url_doi = extract_doi_from_url(crossref_metadata.get('url'))
                    if url_doi:
                        parsed['doi'] = url_doi
        
        return parsed
    
    return None

def create_entry_from_citation(db, citation_text: str, entry_type: str = "publication") -> Tuple[Optional[int], bool]:
    """Parse citation and create entry in database.
    
    Args:
        db: Database instance
        citation_text: Citation string to parse
        entry_type: Default entry type
        
    Returns:
        Tuple of (entry_id, is_new) where entry_id is the entry ID if successful (None if parsing failed),
        and is_new is True if entry was created, False if duplicate found
    """
    parsed = parse_citation(citation_text, entry_type)
    if not parsed:
        return (None, False)
    
    # Create entry
    entry = Entry(
        type=parsed['type'],
        title=parsed['title'],
        year=parsed.get('year'),
        venue=parsed.get('venue'),
        volume=parsed.get('volume'),
        issue=parsed.get('issue'),
        pages=parsed.get('pages'),
        doi=parsed.get('doi'),
        abstract_number=parsed.get('abstract_number'),
        date=parsed.get('date'),
        location=parsed.get('location'),
        status=parsed.get('status'),
        abstract=parsed.get('abstract'),
        url=parsed.get('url'),
        keywords=parsed.get('keywords'),
        subject_area=parsed.get('subject_area'),
        citation_count=parsed.get('citation_count')
    )
    
    entry_id, is_new = db.create_entry(entry)
    
    # Only add authors if this is a new entry (skip if duplicate)
    if not is_new:
        return (entry_id, False)
    
    # Add authors and track Anum's position
    authors = parsed.get('authors', [])
    first_positions = set(parsed.get('first_author_positions', []))
    anum_position = None
    
    for pos, author_name in enumerate(authors, 1):
        if not author_name or len(author_name) < 3:
            continue
        
        is_anum = is_anum_author(author_name)
        if is_anum and anum_position is None:
            anum_position = pos
        
        author = Author(name=author_name, is_anum=is_anum)
        author_id = db.create_author(author)
        
        db.add_entry_author(EntryAuthor(
            entry_id=entry_id,
            author_id=author_id,
            position=pos,
            is_first_author=pos in first_positions
        ))
    
    # Update entry with Anum's position for easier querying
    if anum_position:
        entry.anum_position = anum_position
        db.update_entry(entry)
    
    return (entry_id, True)

def parse_csl_json_item(item: Dict) -> Optional[Dict]:
    """Parse a single CSL JSON item into our internal format.
    
    CSL JSON is the format used by Zotero and other reference managers.
    
    Args:
        item: A single CSL JSON item (dictionary)
        
    Returns:
        Dictionary with parsed data in our format, or None if parsing fails
    """
    if not item or not isinstance(item, dict):
        return None
    
    # Extract title
    title = item.get('title', '')
    if not title:
        return None
    
    # Extract authors
    authors = []
    if 'author' in item:
        for author in item['author']:
            if isinstance(author, dict):
                family = author.get('family', '')
                given = author.get('given', '')
                if family:
                    if given:
                        authors.append(f"{family}, {given}")
                    else:
                        authors.append(family)
    
    # Determine entry type
    csl_type = item.get('type', 'article').lower()
    entry_type_map = {
        'article': 'publication',
        'article-journal': 'publication',
        'paper-conference': 'oral_presentation',
        'poster': 'poster_abstract',
        'presentation': 'oral_presentation',
        'chapter': 'book_chapter',
        'patent': 'patent',
        'book': 'publication',
    }
    entry_type = entry_type_map.get(csl_type, 'publication')
    
    # Extract year
    year = None
    if 'issued' in item and item['issued']:
        date_parts = item['issued'].get('date-parts', [])
        if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
            year = int(date_parts[0][0])
    elif 'year' in item:
        try:
            year = int(item['year'])
        except (ValueError, TypeError):
            pass
    
    # Extract venue/journal
    venue = None
    if 'container-title' in item:
        container = item['container-title']
        if isinstance(container, list) and len(container) > 0:
            venue = container[0]
        elif isinstance(container, str):
            venue = container
    elif 'journal' in item:
        venue = item['journal']
    elif 'event' in item:
        venue = item['event']
    
    # Extract volume, issue, pages
    volume = str(item.get('volume', '')) if item.get('volume') else None
    issue = str(item.get('issue', '')) if item.get('issue') else None
    pages = item.get('page', '') or item.get('pages', '') or None
    
    # Extract DOI
    doi = None
    if 'DOI' in item:
        doi = item['DOI']
    elif 'doi' in item:
        doi = item['doi']
    
    # Clean DOI (remove URL prefixes)
    if doi:
        doi = doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '').replace('doi:', '').strip()
        if not doi:
            doi = None
    
    # Extract abstract
    abstract = item.get('abstract', '') or None
    
    # Extract URL
    url = item.get('URL', '') or item.get('url', '') or None
    
    # Extract keywords
    keywords = None
    if 'keyword' in item:
        kw_list = item['keyword']
        if isinstance(kw_list, list):
            keywords = ', '.join(kw for kw in kw_list if kw)
        elif isinstance(kw_list, str):
            keywords = kw_list
    
    # Extract subject area
    subject_area = None
    if 'subject' in item:
        subject_list = item['subject']
        if isinstance(subject_list, list) and len(subject_list) > 0:
            subject_area = subject_list[0]
        elif isinstance(subject_list, str):
            subject_area = subject_list
    
    # Extract citation count
    citation_count = None
    if 'citation-count' in item:
        try:
            citation_count = int(item['citation-count'])
        except (ValueError, TypeError):
            pass
    
    # Extract date and location for presentations
    date = None
    location = None
    if 'event-date' in item and item['event-date']:
        date_parts = item['event-date'].get('date-parts', [])
        if date_parts and len(date_parts) > 0:
            # Format as "Month Year" if possible
            if len(date_parts[0]) >= 2:
                month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                month = date_parts[0][1] if len(date_parts[0]) > 1 else None
                year_part = date_parts[0][0]
                if month and 1 <= month <= 12:
                    date = f"{month_names[month-1]} {year_part}"
                else:
                    date = str(year_part)
    
    if 'event-place' in item:
        location = item['event-place']
    elif 'publisher-place' in item:
        location = item['publisher-place']
    
    # Extract status for patents
    status = None
    if entry_type == 'patent' and 'status' in item:
        status = item['status']
    
    # Extract abstract number for posters/abstracts
    abstract_number = None
    if entry_type in ['poster_abstract', 'oral_presentation']:
        if 'number' in item:
            abstract_number = str(item['number'])
        elif 'note' in item:
            # Sometimes abstract number is in note field
            note = item['note']
            if isinstance(note, str):
                # Look for patterns like "Abstract #123" or "Poster #456"
                match = re.search(r'(?:abstract|poster)[\s#:]*(\d+)', note, re.IGNORECASE)
                if match:
                    abstract_number = match.group(1)
    
    return {
        'type': entry_type,
        'title': title,
        'year': year,
        'venue': venue,
        'volume': volume,
        'issue': issue,
        'pages': pages,
        'doi': doi,
        'abstract': abstract,
        'url': url,
        'keywords': keywords,
        'subject_area': subject_area,
        'citation_count': citation_count,
        'authors': authors,
        'date': date,
        'location': location,
        'status': status,
        'abstract_number': abstract_number,
    }

def parse_csl_json(csl_json_data: Union[str, List[Dict], Dict]) -> List[Dict]:
    """Parse CSL JSON data (from Zotero export) into list of parsed entries.
    
    Args:
        csl_json_data: CSL JSON data as string, list of items, or single item dict
        
    Returns:
        List of dictionaries with parsed data
    """
    parsed_items = []
    
    # Parse JSON string if needed
    if isinstance(csl_json_data, str):
        try:
            data = json.loads(csl_json_data)
        except json.JSONDecodeError:
            return []
    else:
        data = csl_json_data
    
    # Handle single item or list of items
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        return []
    
    # Parse each item
    for item in items:
        parsed = parse_csl_json_item(item)
        if parsed:
            parsed_items.append(parsed)
    
    return parsed_items

def create_entry_from_csl_json(db, csl_item: Dict) -> Tuple[Optional[int], bool]:
    """Create entry from CSL JSON item.
    
    Args:
        db: Database instance
        csl_item: CSL JSON item dictionary
        
    Returns:
        Tuple of (entry_id, is_new) where entry_id is the entry ID if successful (None if parsing failed),
        and is_new is True if entry was created, False if duplicate found
    """
    parsed = parse_csl_json_item(csl_item)
    if not parsed:
        return (None, False)
    
    # Create entry
    entry = Entry(
        type=parsed['type'],
        title=parsed['title'],
        year=parsed.get('year'),
        venue=parsed.get('venue'),
        volume=parsed.get('volume'),
        issue=parsed.get('issue'),
        pages=parsed.get('pages'),
        doi=parsed.get('doi'),
        abstract_number=parsed.get('abstract_number'),
        date=parsed.get('date'),
        location=parsed.get('location'),
        status=parsed.get('status'),
        abstract=parsed.get('abstract'),
        url=parsed.get('url'),
        keywords=parsed.get('keywords'),
        subject_area=parsed.get('subject_area'),
        citation_count=parsed.get('citation_count')
    )
    
    entry_id, is_new = db.create_entry(entry)
    
    # Only add authors if this is a new entry (skip if duplicate)
    if not is_new:
        return (entry_id, False)
    
    # Add authors and track Anum's position
    authors = parsed.get('authors', [])
    anum_position = None
    
    for pos, author_name in enumerate(authors, 1):
        if not author_name or len(author_name) < 3:
            continue
        
        is_anum = is_anum_author(author_name)
        if is_anum and anum_position is None:
            anum_position = pos
        
        author = Author(name=normalize_author_name(author_name), is_anum=is_anum)
        author_id = db.create_author(author)
        
        db.add_entry_author(EntryAuthor(
            entry_id=entry_id,
            author_id=author_id,
            position=pos,
            is_first_author=False  # CSL JSON doesn't typically mark first authors
        ))
    
    # Update entry with Anum's position for easier querying
    if anum_position:
        entry.id = entry_id
        entry.anum_position = anum_position
        db.update_entry(entry)
    
    return (entry_id, True)
