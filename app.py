"""Streamlit app for searching Anum's papers database."""

import os
import sqlite3
from typing import Tuple
import streamlit as st
from db import Database
from models import Entry, Author
from citation_parser import create_entry_from_citation, parse_citation

# Get database path from environment variable or use default
DATABASE_PATH = os.getenv("DATABASE_PATH", "anum_papers.db")

# Page configuration
st.set_page_config(
    page_title="Anum Papers Database",
    page_icon="📚",
    layout="wide"
)

# Initialize database connection
def get_database():
    """Get database connection (per session)."""
    if 'db' not in st.session_state:
        # Ensure data directory exists if using custom path
        db_dir = os.path.dirname(DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        st.session_state.db = Database(DATABASE_PATH)
        st.session_state.db.connect()
        
        # Check if database needs initialization
        try:
            st.session_state.db.conn.execute("SELECT COUNT(*) FROM entries LIMIT 1").fetchone()
        except sqlite3.OperationalError:
            # Database not initialized, initialize it
            st.session_state.db.initialize()
    else:
        # Ensure connection is still active
        try:
            st.session_state.db._ensure_connected()
        except:
            st.session_state.db.connect()
    return st.session_state.db

def format_entry(entry: Entry, authors: list) -> str:
    """Format an entry for display."""
    author_names = [a['name'] for a in authors]
    author_str = ", ".join(author_names)
    
    parts = []
    if author_str:
        parts.append(f"**{author_str}**")
    
    parts.append(f"*{entry.title}*")
    
    if entry.venue:
        parts.append(entry.venue)
    
    if entry.year:
        parts.append(f"({entry.year})")
    
    if entry.volume or entry.issue or entry.pages:
        vol_info = []
        if entry.volume:
            vol_info.append(f"vol. {entry.volume}")
        if entry.issue:
            vol_info.append(f"no. {entry.issue}")
        if entry.pages:
            vol_info.append(f"pp. {entry.pages}")
        if vol_info:
            parts.append(", ".join(vol_info))
    
    if entry.doi:
        parts.append(f"DOI: {entry.doi}")
    
    if entry.date and entry.location:
        parts.append(f"{entry.date}, {entry.location}")
    elif entry.date:
        parts.append(entry.date)
    elif entry.location:
        parts.append(entry.location)
    
    if entry.status:
        parts.append(f"Status: {entry.status}")
    
    return " | ".join(parts)

def enrich_entry_from_crossref(db, entry: Entry) -> Tuple[bool, str]:
    """Enrich an entry with Crossref metadata using its DOI.
    
    Args:
        db: Database instance
        entry: Entry object with a DOI
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not entry.doi:
        return False, "Entry does not have a DOI"
    
    try:
        from citation_parser import lookup_doi_metadata, HABANERO_AVAILABLE
        
        if not HABANERO_AVAILABLE:
            return False, "Crossref API (habanero) is not available"
        
        # Fetch metadata from Crossref
        metadata = lookup_doi_metadata(entry.doi)
        
        if not metadata:
            return False, f"Could not find metadata for DOI: {entry.doi}"
        
        # Update entry with Crossref data
        # For most fields, only update if current value is None/empty
        # For citation_count, always update (refresh)
        updated_entry = Entry(
            id=entry.id,
            type=entry.type,  # Don't change type
            title=entry.title or metadata.get('title') or entry.title,
            year=entry.year or metadata.get('year'),
            venue=entry.venue or metadata.get('venue'),
            volume=entry.volume or metadata.get('volume'),
            issue=entry.issue or metadata.get('issue'),
            pages=entry.pages or metadata.get('pages'),
            doi=entry.doi,  # Keep existing DOI
            abstract_number=entry.abstract_number,  # Don't change
            date=entry.date,  # Don't change
            location=entry.location,  # Don't change
            status=entry.status,  # Don't change
            abstract=entry.abstract or metadata.get('abstract'),
            url=entry.url or metadata.get('url'),
            keywords=entry.keywords or metadata.get('keywords'),
            subject_area=entry.subject_area or metadata.get('subject_area'),
            citation_count=metadata.get('citation_count'),  # Always refresh citation count
            anum_position=entry.anum_position  # Don't change
        )
        
        if db.update_entry(updated_entry):
            updated_fields = []
            if metadata.get('citation_count') is not None:
                updated_fields.append(f"citation count: {metadata.get('citation_count')}")
            if metadata.get('abstract') and not entry.abstract:
                updated_fields.append("abstract")
            if metadata.get('url') and not entry.url:
                updated_fields.append("URL")
            if metadata.get('keywords') and not entry.keywords:
                updated_fields.append("keywords")
            if metadata.get('subject_area') and not entry.subject_area:
                updated_fields.append("subject area")
            
            msg = f"✅ Enriched entry with Crossref data"
            if updated_fields:
                msg += f" (updated: {', '.join(updated_fields)})"
            return True, msg
        else:
            return False, "Failed to update entry in database"
            
    except Exception as e:
        return False, f"Error enriching entry: {str(e)}"

def show_add_citations_page(db):
    """Show the add citations page."""
    # Ensure imports are available
    from citation_parser import create_entry_from_citation, parse_citation
    
    st.header("➕ Add Citations")
    st.markdown("Paste citations to add them to the database. You can add one at a time or paste multiple citations.")
    
    # Entry type selector
    entry_type = st.selectbox(
        "Default Entry Type",
        ["publication", "book_chapter", "patent", "oral_presentation", "poster_abstract"],
        help="The parser will try to detect the type automatically, but you can set a default."
    )
    
    # Tabs for single vs bulk vs live query vs CSL JSON
    tab1, tab2, tab3, tab4 = st.tabs(["Single Citation", "Bulk Upload", "🔍 Live Query", "📄 CSL JSON Upload"])
    
    with tab1:
        st.subheader("Add Single Citation")
        citation_text = st.text_area(
            "Citation",
            height=150,
            placeholder="Paste citation here, e.g.:\nKazerouni, A. S.*, Chen, Y. A.*, Phelps, M. D., ... Time to Enhancement Measured From Ultrafast Dynamic Contrast-Enhanced MRI for Improved Breast Lesion Diagnosis. Journal of Breast Imaging wbae089 (2025). doi:10.1093/jbi/wbae089"
        )
        
        # Initialize session state if not exists
        if 'parsed_citation' not in st.session_state:
            st.session_state.parsed_citation = None
        if 'citation_text_stored' not in st.session_state:
            st.session_state.citation_text_stored = None
        
        # Handle "Parse & Preview" button click
        if st.button("Parse & Preview", type="primary"):
            if citation_text.strip():
                parsed = parse_citation(citation_text, entry_type)
                if parsed:
                    # Store parsed data in session state
                    st.session_state.parsed_citation = parsed
                    st.session_state.citation_text_stored = citation_text
                    st.success("✅ Citation parsed successfully! Review and edit below before adding to database.")
                    st.rerun()
                else:
                    st.error("❌ Could not parse citation. Please check the format.")
            else:
                st.warning("Please enter a citation.")
        
        # Show form if parsed data exists in session state
        if st.session_state.parsed_citation is not None:
            parsed = st.session_state.parsed_citation
            
            # Editable form
            with st.form("edit_parsed_citation"):
                st.markdown("### Edit Parsed Data")
                
                col1, col2 = st.columns(2)
                with col1:
                    type_options = ["publication", "book_chapter", "patent", "oral_presentation", "poster_abstract"]
                    parsed_type = parsed.get('type', 'publication')
                    try:
                        type_index = type_options.index(parsed_type)
                    except ValueError:
                        type_index = 0
                    edited_type = st.selectbox(
                        "Entry Type",
                        type_options,
                        index=type_index
                    )
                    parsed_year = parsed.get('year')
                    edited_year = st.number_input("Year", value=int(parsed_year) if parsed_year else None, min_value=1900, max_value=2100, step=1, format="%d")
                    edited_venue = st.text_input("Venue/Journal", value=parsed.get('venue', '') or '')
                
                with col2:
                    edited_volume = st.text_input("Volume", value=parsed.get('volume', '') or '')
                    edited_issue = st.text_input("Issue", value=parsed.get('issue', '') or '')
                    edited_pages = st.text_input("Pages", value=parsed.get('pages', '') or '')
                
                edited_title = st.text_area("Title", value=parsed.get('title', '') or '', height=100)
                edited_doi = st.text_input("DOI", value=parsed.get('doi', '') or '')
                
                # Authors editing - use text area for easy editing
                st.markdown("### Authors (one per line)")
                authors_list = parsed.get('authors', [])
                authors_text = '\n'.join(authors_list)
                edited_authors_text = st.text_area(
                    "Authors", 
                    value=authors_text, 
                    height=100,
                    help="Enter authors, one per line. Format: LastName, FirstName"
                )
                edited_authors = [a.strip() for a in edited_authors_text.split('\n') if a.strip()]
                
                # Additional fields
                with st.expander("Additional Fields"):
                    edited_abstract = st.text_area("Abstract", value=parsed.get('abstract', '') or '')
                    edited_url = st.text_input("URL", value=parsed.get('url', '') or '')
                    edited_keywords = st.text_input("Keywords", value=parsed.get('keywords', '') or '')
                    edited_subject_area = st.text_input("Subject Area", value=parsed.get('subject_area', '') or '')
                    edited_citation_count = st.number_input("Citation Count", value=parsed.get('citation_count') or 0, min_value=0, step=1)
                    edited_date = st.text_input("Date (for presentations)", value=parsed.get('date', '') or '')
                    edited_location = st.text_input("Location (for presentations)", value=parsed.get('location', '') or '')
                    edited_abstract_number = st.text_input("Abstract Number", value=parsed.get('abstract_number', '') or '')
                    edited_status = st.text_input("Status (for patents)", value=parsed.get('status', '') or '')
                
                submitted = st.form_submit_button("💾 Save to Database", type="primary", use_container_width=True)
                
                if submitted:
                    # Validate required fields
                    if not edited_title or not edited_title.strip():
                        st.error("Title is required!")
                    elif not edited_authors:
                        st.error("At least one author is required!")
                    else:
                        # Create entry from edited data
                        from models import Entry
                        entry = Entry(
                            type=edited_type,
                            title=edited_title,
                            year=int(edited_year) if edited_year else None,
                            venue=edited_venue if edited_venue else None,
                            volume=edited_volume if edited_volume else None,
                            issue=edited_issue if edited_issue else None,
                            pages=edited_pages if edited_pages else None,
                            doi=edited_doi if edited_doi else None,
                            abstract_number=edited_abstract_number if edited_abstract_number else None,
                            date=edited_date if edited_date else None,
                            location=edited_location if edited_location else None,
                            status=edited_status if edited_status else None,
                            abstract=edited_abstract if edited_abstract else None,
                            url=edited_url if edited_url else None,
                            keywords=edited_keywords if edited_keywords else None,
                            subject_area=edited_subject_area if edited_subject_area else None,
                            citation_count=int(edited_citation_count) if edited_citation_count else None
                        )
                        
                        try:
                            entry_id, is_new = db.create_entry(entry)
                            
                            if not is_new:
                                st.warning(f"⚠️ Duplicate entry detected! Entry already exists with ID: {entry_id}")
                            else:
                                # Add authors
                                from models import Author, EntryAuthor
                                from citation_parser import is_anum_author, normalize_author_name
                                
                                anum_position = None
                                for pos, author_name in enumerate(edited_authors, 1):
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
                                        is_first_author=False  # Could be enhanced to detect from *
                                    ))
                                
                                # Update entry with Anum's position
                                if anum_position:
                                    entry.id = entry_id
                                    entry.anum_position = anum_position
                                    db.update_entry(entry)
                                
                                st.success(f"✅ Entry added successfully! (ID: {entry_id})")
                                st.balloons()
                            
                            # Clear session state after successful save
                            st.session_state.parsed_citation = None
                            st.session_state.citation_text_stored = None
                            
                            # Rerun to refresh the page
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error adding entry: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
            
            # Show raw JSON for reference
            with st.expander("📋 View Raw Parsed JSON"):
                st.json(parsed)
            
            # Add a button to clear/start over
            if st.button("🔄 Parse New Citation", key="clear_parsed"):
                st.session_state.parsed_citation = None
                st.session_state.citation_text_stored = None
                st.rerun()
    
    with tab2:
        st.subheader("Bulk Upload Citations")
        st.markdown("Paste multiple citations, one per line. Empty lines will be ignored.")
        
        bulk_citations = st.text_area(
            "Citations (one per line)",
            height=400,
            placeholder="Paste multiple citations here, one per line:\n\nKazerouni, A. S.*, Chen, Y. A.*, ... Title 1. Journal 1 (2025).\nKazerouni, A. S., ... Title 2. Journal 2 (2024).\n..."
        )
        
        # Initialize session state for bulk upload
        if 'bulk_parsed_results' not in st.session_state:
            st.session_state.bulk_parsed_results = None
        if 'bulk_entry_type' not in st.session_state:
            st.session_state.bulk_entry_type = None
        
        if st.button("Parse All & Preview", type="primary"):
            if bulk_citations.strip():
                citations = [c.strip() for c in bulk_citations.split('\n') if c.strip()]
                st.info(f"Found {len(citations)} citation(s) to process.")
                
                parsed_results = []
                for i, citation in enumerate(citations, 1):
                    parsed = parse_citation(citation, entry_type)
                    if parsed:
                        parsed_results.append((i, citation, parsed, True))
                    else:
                        parsed_results.append((i, citation, None, False))
                
                # Store in session state
                st.session_state.bulk_parsed_results = parsed_results
                st.session_state.bulk_entry_type = entry_type
            else:
                st.warning("Please paste citations to process.")
                st.session_state.bulk_parsed_results = None
        
        # Show results if we have parsed data
        if st.session_state.bulk_parsed_results:
            parsed_results = st.session_state.bulk_parsed_results
            success_count = sum(1 for _, _, _, success in parsed_results if success)
            st.metric("Successfully Parsed", f"{success_count}/{len(parsed_results)}")
            
            # Show preview
            with st.expander("Preview Parsed Citations", expanded=True):
                for i, citation, parsed, success in parsed_results:
                    if success:
                        st.markdown(f"**Citation {i}:** ✅")
                        st.json(parsed)
                    else:
                        st.markdown(f"**Citation {i}:** ❌ Failed to parse")
                        st.code(citation[:200] + "..." if len(citation) > 200 else citation)
                    st.divider()
            
            if success_count > 0:
                if st.button("Add All to Database", type="primary", key="add_all_bulk"):
                    added_count = 0
                    error_count = 0
                    error_messages = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    duplicate_count = 0
                    for i, (idx, citation, parsed, success) in enumerate(parsed_results):
                        if success:
                            try:
                                entry_id, is_new = create_entry_from_citation(db, citation, st.session_state.bulk_entry_type)
                                if entry_id:
                                    if is_new:
                                        added_count += 1
                                    else:
                                        duplicate_count += 1
                                else:
                                    error_count += 1
                                    error_messages.append(f"Citation {idx}: Failed to create entry")
                            except Exception as e:
                                error_count += 1
                                error_messages.append(f"Citation {idx}: {str(e)}")
                        
                        progress_bar.progress((i + 1) / len(parsed_results))
                        status_text.text(f"Processing {i + 1}/{len(parsed_results)}...")
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    if added_count > 0:
                        st.success(f"✅ Successfully added {added_count} entries to the database!")
                        st.balloons()
                        # Clear parsed results after successful addition
                        st.session_state.bulk_parsed_results = None
                    if duplicate_count > 0:
                        st.info(f"ℹ️ {duplicate_count} duplicate entries were skipped.")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} entries could not be added.")
                        for msg in error_messages:
                            st.error(msg)
    
    with tab3:
        st.subheader("🔍 Live Citation Query")
        st.markdown("Search for papers by title, author, or DOI using Crossref API")
        
        query_type = st.radio(
            "Search by:",
            ["Title", "Author", "DOI"],
            horizontal=True
        )
        
        if query_type == "Title":
            search_query = st.text_input("Enter paper title", placeholder="e.g., Time to Enhancement Measured From Ultrafast Dynamic Contrast-Enhanced MRI")
            if st.button("🔍 Search", type="primary") and search_query:
                try:
                    from habanero import Crossref
                    cr = Crossref()
                    results = cr.works(query=search_query, limit=10)
                    
                    if results and 'message' in results and 'items' in results['message']:
                        items = results['message']['items']
                        st.success(f"Found {len(items)} results")
                        
                        for i, item in enumerate(items, 1):
                            with st.expander(f"{i}. {item.get('title', ['Unknown'])[0] if item.get('title') else 'Unknown'}"):
                                # Extract basic info
                                title = item.get('title', [''])[0] if item.get('title') else ''
                                authors = []
                                if 'author' in item:
                                    for author in item['author']:
                                        given = author.get('given', '')
                                        family = author.get('family', '')
                                        if family:
                                            authors.append(f"{family}, {given}".strip(', '))
                                
                                doi = item.get('DOI', '')
                                year = None
                                if 'published-print' in item and item['published-print'].get('date-parts'):
                                    year = item['published-print']['date-parts'][0][0]
                                elif 'published-online' in item and item['published-online'].get('date-parts'):
                                    year = item['published-online']['date-parts'][0][0]
                                
                                venue = item.get('container-title', [''])[0] if item.get('container-title') else ''
                                
                                st.write(f"**Title:** {title}")
                                st.write(f"**Authors:** {', '.join(authors) if authors else 'Unknown'}")
                                st.write(f"**Venue:** {venue}")
                                st.write(f"**Year:** {year if year else 'Unknown'}")
                                if doi:
                                    st.write(f"**DOI:** {doi}")
                                
                                # Create citation string
                                author_str = ', '.join(authors) if authors else ''
                                citation_str = f"{author_str}. {title}. {venue} ({year}). doi:{doi}" if doi else f"{author_str}. {title}. {venue} ({year})."
                                
                                st.text_area("Citation", citation_str, key=f"citation_{i}", height=100)
                                
                                if st.button("Add to Database", key=f"add_{i}"):
                                    try:
                                        from citation_parser import create_entry_from_citation
                                        entry_id, is_new = create_entry_from_citation(db, citation_str, entry_type)
                                        if entry_id:
                                            if is_new:
                                                st.success(f"✅ Added! Entry ID: {entry_id}")
                                            else:
                                                st.warning(f"⚠️ Duplicate entry detected! Entry already exists with ID: {entry_id}")
                                        else:
                                            st.error("Failed to add entry")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                    else:
                        st.info("No results found")
                except Exception as e:
                    st.error(f"Search error: {str(e)}")
        
        elif query_type == "Author":
            author_query = st.text_input("Enter author name", placeholder="e.g., Kazerouni")
            if st.button("🔍 Search", type="primary") and author_query:
                try:
                    from habanero import Crossref
                    cr = Crossref()
                    results = cr.works(query_author=author_query, limit=10)
                    
                    if results and 'message' in results and 'items' in results['message']:
                        items = results['message']['items']
                        st.success(f"Found {len(items)} results")
                        
                        for i, item in enumerate(items, 1):
                            with st.expander(f"{i}. {item.get('title', ['Unknown'])[0] if item.get('title') else 'Unknown'}"):
                                title = item.get('title', [''])[0] if item.get('title') else ''
                                authors = []
                                if 'author' in item:
                                    for author in item['author']:
                                        given = author.get('given', '')
                                        family = author.get('family', '')
                                        if family:
                                            authors.append(f"{family}, {given}".strip(', '))
                                
                                doi = item.get('DOI', '')
                                year = None
                                if 'published-print' in item and item['published-print'].get('date-parts'):
                                    year = item['published-print']['date-parts'][0][0]
                                
                                venue = item.get('container-title', [''])[0] if item.get('container-title') else ''
                                
                                st.write(f"**Title:** {title}")
                                st.write(f"**Authors:** {', '.join(authors) if authors else 'Unknown'}")
                                st.write(f"**Venue:** {venue}")
                                st.write(f"**Year:** {year if year else 'Unknown'}")
                                if doi:
                                    st.write(f"**DOI:** {doi}")
                                
                                author_str = ', '.join(authors) if authors else ''
                                citation_str = f"{author_str}. {title}. {venue} ({year}). doi:{doi}" if doi else f"{author_str}. {title}. {venue} ({year})."
                                
                                st.text_area("Citation", citation_str, key=f"citation_author_{i}", height=100)
                                
                                if st.button("Add to Database", key=f"add_author_{i}"):
                                    try:
                                        from citation_parser import create_entry_from_citation
                                        entry_id, is_new = create_entry_from_citation(db, citation_str, entry_type)
                                        if entry_id:
                                            if is_new:
                                                st.success(f"✅ Added! Entry ID: {entry_id}")
                                            else:
                                                st.warning(f"⚠️ Duplicate entry detected! Entry already exists with ID: {entry_id}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                    else:
                        st.info("No results found")
                except Exception as e:
                    st.error(f"Search error: {str(e)}")
        
        elif query_type == "DOI":
            doi_query = st.text_input("Enter DOI", placeholder="e.g., 10.1093/jbi/wbae089")
            if st.button("🔍 Lookup", type="primary") and doi_query:
                try:
                    from habanero import Crossref
                    from citation_parser import lookup_doi_metadata
                    
                    # Clean DOI
                    doi_clean = doi_query.replace('doi:', '').replace('https://doi.org/', '').strip()
                    metadata = lookup_doi_metadata(doi_clean)
                    
                    if metadata:
                        st.success("✅ Found metadata!")
                        st.json(metadata)
                        
                        # Create citation string
                        authors_str = ', '.join(metadata.get('authors', []))
                        citation_str = f"{authors_str}. {metadata.get('title', '')}. {metadata.get('venue', '')} ({metadata.get('year', '')}). doi:{doi_clean}"
                        
                        st.text_area("Citation", citation_str, height=100)
                        
                        if st.button("Add to Database", type="primary"):
                            try:
                                from citation_parser import create_entry_from_citation
                                entry_id, is_new = create_entry_from_citation(db, citation_str, entry_type)
                                if entry_id:
                                    if is_new:
                                        st.success(f"✅ Added! Entry ID: {entry_id}")
                                        st.balloons()
                                    else:
                                        st.warning(f"⚠️ Duplicate entry detected! Entry already exists with ID: {entry_id}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        st.error("Could not find metadata for this DOI")
                except Exception as e:
                    st.error(f"Lookup error: {str(e)}")
    
    with tab4:
        st.subheader("📄 CSL JSON Upload (Zotero Export)")
        st.markdown("Upload a CSL JSON file exported from Zotero to import entries into the database.")
        
        uploaded_file = st.file_uploader(
            "Choose CSL JSON file",
            type=['json'],
            help="Export from Zotero: File → Export Library → Format: CSL JSON"
        )
        
        if uploaded_file is not None:
            try:
                # Read and parse the file
                file_contents = uploaded_file.read().decode('utf-8')
                import json
                from citation_parser import parse_csl_json
                
                csl_data = json.loads(file_contents)
                
                # Parse all items
                parsed_items = parse_csl_json(csl_data)
                
                if not parsed_items:
                    st.warning("No valid entries found in the CSL JSON file.")
                else:
                    st.success(f"Found {len(parsed_items)} entries in the file.")
                    
                    # Show preview
                    with st.expander("Preview Entries", expanded=False):
                        for i, item in enumerate(parsed_items[:10], 1):  # Show first 10
                            st.markdown(f"**{i}. {item.get('title', 'Unknown')[:80]}...**")
                            st.caption(f"Type: {item.get('type')} | Year: {item.get('year', 'N/A')} | Authors: {len(item.get('authors', []))}")
                    
                    if len(parsed_items) > 10:
                        st.caption(f"... and {len(parsed_items) - 10} more entries")
                    
                    # Import button
                    if st.button("Import All Entries", type="primary"):
                        added_count = 0
                        duplicate_count = 0
                        error_count = 0
                        error_messages = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, item in enumerate(parsed_items, 1):
                            try:
                                # Create entry from parsed data
                                from models import Entry, Author, EntryAuthor
                                from citation_parser import is_anum_author, normalize_author_name
                                
                                entry = Entry(
                                    type=item['type'],
                                    title=item['title'],
                                    year=item.get('year'),
                                    venue=item.get('venue'),
                                    volume=item.get('volume'),
                                    issue=item.get('issue'),
                                    pages=item.get('pages'),
                                    doi=item.get('doi'),
                                    abstract_number=item.get('abstract_number'),
                                    date=item.get('date'),
                                    location=item.get('location'),
                                    status=item.get('status'),
                                    abstract=item.get('abstract'),
                                    url=item.get('url'),
                                    keywords=item.get('keywords'),
                                    subject_area=item.get('subject_area'),
                                    citation_count=item.get('citation_count')
                                )
                                
                                entry_id, is_new = db.create_entry(entry)
                                
                                if is_new:
                                    # Add authors
                                    authors = item.get('authors', [])
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
                                            is_first_author=False
                                        ))
                                    
                                    # Update entry with Anum's position
                                    if anum_position:
                                        entry.id = entry_id
                                        entry.anum_position = anum_position
                                        db.update_entry(entry)
                                    
                                    added_count += 1
                                else:
                                    duplicate_count += 1
                                
                            except Exception as e:
                                error_count += 1
                                error_messages.append(f"Entry {i} ({item.get('title', 'Unknown')[:50]}): {str(e)}")
                            
                            progress_bar.progress(i / len(parsed_items))
                            status_text.text(f"Processing {i}/{len(parsed_items)}...")
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if added_count > 0:
                            st.success(f"✅ Successfully imported {added_count} entries!")
                            st.balloons()
                        if duplicate_count > 0:
                            st.info(f"ℹ️ {duplicate_count} duplicate entries were skipped.")
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count} entries could not be imported.")
                            with st.expander("Error Details"):
                                for msg in error_messages:
                                    st.error(msg)
                        
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file. Please ensure the file is a valid CSL JSON export from Zotero.")
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

def show_search_page(db):
    """Show the search page."""
    st.header("🔍 Search Database")
    
    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        
        # Entry type filter
        entry_types = ["All", "publication", "book_chapter", "patent", 
                      "oral_presentation", "poster_abstract"]
        selected_type = st.selectbox("Entry Type", entry_types)
        entry_type_filter = None if selected_type == "All" else selected_type
        
        # Year filter
        try:
            if db.conn:
                years = db.conn.execute(
                    "SELECT DISTINCT year FROM entries WHERE year IS NOT NULL ORDER BY year DESC"
                ).fetchall()
                year_options = ["All"] + [str(row[0]) for row in years]
            else:
                year_options = ["All"]
        except sqlite3.OperationalError:
            year_options = ["All"]
        
        selected_year = st.selectbox("Year", year_options)
        year_filter = None if selected_year == "All" else int(selected_year)
        
        # Author filter
        authors = db.get_all_authors()
        author_options = ["All"] + [a.name for a in authors]
        selected_author = st.selectbox("Author", author_options)
        author_filter = None if selected_author == "All" else selected_author
    
    # Search bar
    search_query = st.text_input("🔍 Search", placeholder="Search by title, venue, or keywords...")
    
    # Get entries based on filters
    if author_filter:
        # Filter by specific author
        author = db.get_author_by_name(author_filter)
        if author:
            entries = db.get_entries_by_author(author.id)
            # Apply type and year filters
            if entry_type_filter:
                entries = [e for e in entries if e.type == entry_type_filter]
            if year_filter:
                entries = [e for e in entries if e.year == year_filter]
        else:
            entries = []
    else:
        entries = db.get_all_entries(entry_type=entry_type_filter, year=year_filter)
    
    # Apply search query filter
    if search_query:
        query_lower = search_query.lower()
        filtered_entries = []
        for entry in entries:
            # Search in title, venue, abstract_number, abstract, keywords, and subject_area
            if (query_lower in entry.title.lower() or
                (entry.venue and query_lower in entry.venue.lower()) or
                (entry.abstract_number and query_lower in entry.abstract_number.lower()) or
                (entry.abstract and query_lower in entry.abstract.lower()) or
                (entry.keywords and query_lower in entry.keywords.lower()) or
                (entry.subject_area and query_lower in entry.subject_area.lower())):
                filtered_entries.append(entry)
        entries = filtered_entries
    
    # Display results
    st.markdown(f"**Found {len(entries)} entries**")
    
    if entries:
        for entry in entries:
            authors = db.get_entry_authors(entry.id)
            
            # Create a cleaner header with title and type badge
            type_badge = entry.type.replace("_", " ").title()
            header_text = f"{entry.title[:80]}{'...' if len(entry.title) > 80 else ''} • {type_badge}"
            
            with st.expander(header_text, expanded=False):
                # Title - most prominent
                st.markdown(f"### {entry.title}")
                
                # Authors section
                if authors:
                    author_names = [a['name'] for a in authors]
                    author_str = ", ".join(author_names)
                    st.markdown(f"**Authors:** {author_str}")
                
                st.markdown("---")
                
                # Details in columns
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Publication Details**")
                    if entry.venue:
                        st.write(f"**Venue:** {entry.venue}")
                    if entry.year:
                        st.write(f"**Year:** {entry.year}")
                    if entry.anum_position:
                        position_suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(entry.anum_position, 'th')
                        st.write(f"**Anum's Position:** {entry.anum_position}{position_suffix} author")
                    if entry.volume or entry.issue:
                        vol_info = []
                        if entry.volume:
                            vol_info.append(f"Vol. {entry.volume}")
                        if entry.issue:
                            vol_info.append(f"Issue {entry.issue}")
                        if entry.pages:
                            vol_info.append(f"pp. {entry.pages}")
                        if vol_info:
                            st.write(f"**Publication Info:** {', '.join(vol_info)}")
                    if entry.doi:
                        st.write(f"**DOI:** [{entry.doi}](https://doi.org/{entry.doi})")
                    if entry.abstract_number:
                        st.write(f"**Abstract #:** {entry.abstract_number}")
                    if entry.date:
                        st.write(f"**Date:** {entry.date}")
                    if entry.location:
                        st.write(f"**Location:** {entry.location}")
                    if entry.status:
                        st.write(f"**Status:** {entry.status}")
                    if entry.citation_count is not None:
                        st.write(f"**Citations:** {entry.citation_count}")
                    if entry.subject_area:
                        st.write(f"**Subject Area:** {entry.subject_area}")
                
                with col2:
                    st.markdown("**Author List**")
                    for author in authors:
                        author_marker = " 👤" if author['is_anum'] else ""
                        first_marker = " ⭐" if author['is_first_author'] else ""
                        st.write(f"{author['position']}. {author['name']}{author_marker}{first_marker}")
                
                # Enriched metadata section
                has_enriched = entry.abstract or entry.url or entry.keywords
                if has_enriched:
                    st.markdown("---")
                    st.markdown("**Additional Information**")
                    if entry.url:
                        st.write(f"**URL:** [{entry.url}]({entry.url})")
                    if entry.abstract:
                        with st.expander("📄 Abstract", expanded=False):
                            st.write(entry.abstract)
                    if entry.keywords:
                        st.write(f"**Keywords:** {entry.keywords}")
                
                # Edit and Delete buttons
                st.markdown("---")
                edit_key = f"edit_mode_{entry.id}"
                delete_key = f"delete_confirm_{entry.id}"
                
                # Initialize session state
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False
                
                # Show edit form if in edit mode
                if st.session_state[edit_key]:
                    with st.form(f"edit_entry_{entry.id}"):
                        st.markdown("### ✏️ Edit Entry")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            type_options = ["publication", "book_chapter", "patent", "oral_presentation", "poster_abstract"]
                            try:
                                type_index = type_options.index(entry.type)
                            except ValueError:
                                type_index = 0
                            edited_type = st.selectbox("Entry Type", type_options, index=type_index, key=f"edit_type_{entry.id}")
                            edited_year = st.number_input("Year", value=entry.year or None, min_value=1900, max_value=2100, step=1, format="%d", key=f"edit_year_{entry.id}")
                            edited_venue = st.text_input("Venue/Journal", value=entry.venue or '', key=f"edit_venue_{entry.id}")
                        
                        with col2:
                            edited_volume = st.text_input("Volume", value=entry.volume or '', key=f"edit_volume_{entry.id}")
                            edited_issue = st.text_input("Issue", value=entry.issue or '', key=f"edit_issue_{entry.id}")
                            edited_pages = st.text_input("Pages", value=entry.pages or '', key=f"edit_pages_{entry.id}")
                        
                        edited_title = st.text_area("Title", value=entry.title or '', height=100, key=f"edit_title_{entry.id}")
                        edited_doi = st.text_input("DOI", value=entry.doi or '', key=f"edit_doi_{entry.id}")
                        
                        # Authors editing
                        st.markdown("### Authors (one per line)")
                        authors_text = '\n'.join([a['name'] for a in authors])
                        edited_authors_text = st.text_area(
                            "Authors", 
                            value=authors_text, 
                            height=100,
                            help="Enter authors, one per line. Format: LastName, FirstName",
                            key=f"edit_authors_{entry.id}"
                        )
                        edited_authors = [a.strip() for a in edited_authors_text.split('\n') if a.strip()]
                        
                        # Additional fields
                        with st.expander("Additional Fields"):
                            edited_abstract = st.text_area("Abstract", value=entry.abstract or '', key=f"edit_abstract_{entry.id}")
                            edited_url = st.text_input("URL", value=entry.url or '', key=f"edit_url_{entry.id}")
                            edited_keywords = st.text_input("Keywords", value=entry.keywords or '', key=f"edit_keywords_{entry.id}")
                            edited_subject_area = st.text_input("Subject Area", value=entry.subject_area or '', key=f"edit_subject_{entry.id}")
                            edited_citation_count = st.number_input("Citation Count", value=entry.citation_count or 0, min_value=0, step=1, key=f"edit_citations_{entry.id}")
                            edited_date = st.text_input("Date (for presentations)", value=entry.date or '', key=f"edit_date_{entry.id}")
                            edited_location = st.text_input("Location (for presentations)", value=entry.location or '', key=f"edit_location_{entry.id}")
                            edited_abstract_number = st.text_input("Abstract Number", value=entry.abstract_number or '', key=f"edit_abstract_num_{entry.id}")
                            edited_status = st.text_input("Status (for patents)", value=entry.status or '', key=f"edit_status_{entry.id}")
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_clicked = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                        with col_cancel:
                            cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                        
                        # Handle form submission
                        if save_clicked:
                            # Validate required fields
                            if not edited_title or not edited_title.strip():
                                st.error("❌ Title is required!")
                            elif not edited_authors:
                                st.error("❌ At least one author is required!")
                            else:
                                try:
                                    # Update entry
                                    from models import Entry
                                    updated_entry = Entry(
                                        id=entry.id,
                                        type=edited_type,
                                        title=edited_title.strip(),
                                        year=int(edited_year) if edited_year else None,
                                        venue=edited_venue.strip() if edited_venue else None,
                                        volume=edited_volume.strip() if edited_volume else None,
                                        issue=edited_issue.strip() if edited_issue else None,
                                        pages=edited_pages.strip() if edited_pages else None,
                                        doi=edited_doi.strip() if edited_doi else None,
                                        abstract_number=edited_abstract_number.strip() if edited_abstract_number else None,
                                        date=edited_date.strip() if edited_date else None,
                                        location=edited_location.strip() if edited_location else None,
                                        status=edited_status.strip() if edited_status else None,
                                        abstract=edited_abstract.strip() if edited_abstract else None,
                                        url=edited_url.strip() if edited_url else None,
                                        keywords=edited_keywords.strip() if edited_keywords else None,
                                        subject_area=edited_subject_area.strip() if edited_subject_area else None,
                                        citation_count=int(edited_citation_count) if edited_citation_count else None,
                                        anum_position=entry.anum_position
                                    )
                                    
                                    # Update the entry first
                                    if not db.update_entry(updated_entry):
                                        st.error("❌ Failed to update entry in database.")
                                    else:
                                        # Update authors - delete old relationships and add new ones
                                        current_authors = db.get_entry_authors(entry.id)
                                        for curr_author in current_authors:
                                            # Delete the relationship (authors themselves are kept for other entries)
                                            db.conn.execute(
                                                "DELETE FROM entry_authors WHERE entry_id = ? AND author_id = ?",
                                                (entry.id, curr_author['id'])
                                            )
                                        
                                        # Add updated authors
                                        from models import Author, EntryAuthor
                                        from citation_parser import is_anum_author, normalize_author_name
                                        
                                        anum_position = None
                                        for pos, author_name in enumerate(edited_authors, 1):
                                            if not author_name or len(author_name.strip()) < 3:
                                                continue
                                            
                                            is_anum = is_anum_author(author_name)
                                            if is_anum and anum_position is None:
                                                anum_position = pos
                                            
                                            author = Author(name=normalize_author_name(author_name), is_anum=is_anum)
                                            author_id = db.create_author(author)
                                            
                                            db.add_entry_author(EntryAuthor(
                                                entry_id=entry.id,
                                                author_id=author_id,
                                                position=pos,
                                                is_first_author=False
                                            ))
                                        
                                        # Update Anum's position if changed
                                        if anum_position != entry.anum_position:
                                            updated_entry.anum_position = anum_position
                                            db.update_entry(updated_entry)
                                        
                                        # Commit all changes
                                        db.conn.commit()
                                        
                                        st.success("✅ Entry updated successfully!")
                                        st.session_state[edit_key] = False
                                        st.rerun()
                                        
                                except Exception as e:
                                    st.error(f"❌ Error updating entry: {str(e)}")
                                    import traceback
                                    with st.expander("Error Details"):
                                        st.code(traceback.format_exc())
                        
                        if cancel_clicked:
                            st.session_state[edit_key] = False
                            st.rerun()
                
                # Show action buttons when not in edit mode
                elif not st.session_state[delete_key]:
                    # Determine number of columns based on whether entry has DOI
                    if entry.doi:
                        col_actions1, col_actions2, col_actions3, col_actions4 = st.columns([2, 1, 1, 1])
                    else:
                        col_actions1, col_actions2, col_actions3 = st.columns([2, 1, 1])
                    
                    with col_actions1:
                        st.caption(f"Entry ID: {entry.id}")
                    with col_actions2:
                        if st.button("✏️ Edit", key=f"edit_btn_{entry.id}", type="primary"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    with col_actions3:
                        if st.button("🗑️ Delete", key=f"delete_btn_{entry.id}", type="secondary"):
                            st.session_state[delete_key] = True
                            st.rerun()
                    # Only show enrich button if entry has a DOI
                    if entry.doi:
                        with col_actions4:
                            if st.button("🔄 Enrich", key=f"enrich_btn_{entry.id}", 
                                       help="Fetch latest metadata from Crossref (refreshes citation count, abstract, etc.)"):
                                with st.spinner("Fetching data from Crossref..."):
                                    success, message = enrich_entry_from_crossref(db, entry)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                else:
                    # Show delete confirmation
                    st.warning("⚠️ Are you sure you want to delete this entry? This action cannot be undone.")
                    st.caption(f"Entry ID: {entry.id} - {entry.title[:80]}...")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("✅ Confirm Delete", key=f"confirm_{entry.id}", type="primary"):
                            try:
                                if db.delete_entry(entry.id):
                                    st.success("✅ Entry deleted successfully!")
                                    st.session_state[delete_key] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to delete entry.")
                                    st.session_state[delete_key] = False
                            except Exception as e:
                                st.error(f"Error deleting entry: {str(e)}")
                                st.session_state[delete_key] = False
                    with confirm_col2:
                        if st.button("❌ Cancel", key=f"cancel_{entry.id}"):
                            st.session_state[delete_key] = False
                            st.rerun()
    else:
        st.info("No entries found. Try adjusting your filters or search query.")
    
    # Statistics
    with st.sidebar:
        st.markdown("---")
        st.header("Statistics")
        
        total_entries = len(db.get_all_entries())
        st.metric("Total Entries", total_entries)
        
        for entry_type in ["publication", "oral_presentation", "poster_abstract"]:
            count = len(db.get_all_entries(entry_type=entry_type))
            if count > 0:
                st.metric(entry_type.replace("_", " ").title(), count)
        
        # Database management
        st.markdown("---")
        st.header("Database Management")
        
        # Bulk enrich from Crossref
        if st.button("🔄 Enrich All Entries with DOI", 
                    help="Refresh citation counts and metadata for all entries that have a DOI"):
            from citation_parser import lookup_doi_metadata, HABANERO_AVAILABLE
            
            if not HABANERO_AVAILABLE:
                st.error("Crossref API (habanero) is not available")
            else:
                # Get all entries with DOI
                all_entries = db.get_all_entries()
                entries_with_doi = [e for e in all_entries if e.doi]
                
                if not entries_with_doi:
                    st.info("No entries with DOI found.")
                else:
                    st.info(f"Found {len(entries_with_doi)} entries with DOI. This may take a while...")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    enriched_count = 0
                    error_count = 0
                    
                    for i, entry in enumerate(entries_with_doi):
                        success, _ = enrich_entry_from_crossref(db, entry)
                        if success:
                            enriched_count += 1
                        else:
                            error_count += 1
                        
                        progress_bar.progress((i + 1) / len(entries_with_doi))
                        status_text.text(f"Processing {i + 1}/{len(entries_with_doi)}...")
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    if enriched_count > 0:
                        st.success(f"✅ Successfully enriched {enriched_count} entries!")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} entries could not be enriched.")
                    st.rerun()
        
        st.markdown("---")
        
        # Nuke DB button with confirmation
        nuke_confirm_key = "nuke_db_confirm"
        if nuke_confirm_key not in st.session_state:
            st.session_state[nuke_confirm_key] = False
        
        if not st.session_state[nuke_confirm_key]:
            if st.button("🗑️ Nuke Database", type="secondary", help="Delete all data and reinitialize database"):
                st.session_state[nuke_confirm_key] = True
                st.rerun()
        else:
            st.warning("⚠️ Are you sure you want to delete ALL data? This cannot be undone!")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Nuke", type="primary"):
                    try:
                        # Close database connection
                        db.close()
                        
                        # Delete database file
                        db_path = db.db_path
                        if os.path.exists(db_path):
                            os.remove(db_path)
                        
                        # Reinitialize database
                        db.initialize()
                        db.connect()
                        
                        # Clear session state
                        st.session_state[nuke_confirm_key] = False
                        if 'db' in st.session_state:
                            st.session_state.db = db
                        
                        st.success("✅ Database nuked and reinitialized!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error nuking database: {str(e)}")
                        st.session_state[nuke_confirm_key] = False
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state[nuke_confirm_key] = False
                    st.rerun()

def main():
    """Main Streamlit app."""
    st.title("📚 Anum Papers Database")
    st.markdown("Search through academic publications, presentations, and related work")
    
    db = get_database()
    
    # Check if database is initialized
    try:
        # Try to query entries table to see if it exists
        if db.conn:
            db.conn.execute("SELECT COUNT(*) FROM entries LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        st.error("Database not initialized. Please run the database initialization first.")
        st.code("""
from db import Database

with Database("anum_papers.db") as db:
    db.initialize()
        """)
        st.stop()
    
    # Main tabs
    tab1, tab2 = st.tabs(["🔍 Search", "➕ Add Citations"])
    
    with tab1:
        show_search_page(db)
    
    with tab2:
        show_add_citations_page(db)

if __name__ == "__main__":
    main()

