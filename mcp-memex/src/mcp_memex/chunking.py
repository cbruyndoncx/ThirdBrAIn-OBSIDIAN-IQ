import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MarkdownSection:
    path: str
    index: int
    level: int  # Header level (1-6)
    header: str  # The header text
    content: str  # Full content including header
    parent_index: Optional[int]  # Index of parent section
    child_indices: List[int]  # Indices of child sections

def split_markdown_sections(markdown_text: str, path: str) -> List[MarkdownSection]:
    """
    Split markdown text into sections based on headers while maintaining hierarchy.
    Returns a list of MarkdownSection objects.
    
    Example:
    # Header 1
    Content 1
    ## Subheader 1
    Content 2
    # Header 2
    Content 3
    
    Will create 3 sections with appropriate parent-child relationships.
    """
    # Regex to match markdown headers (# Header)
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # Find all headers with their positions
    headers = [(match.group(1), match.group(2), match.start()) 
              for match in header_pattern.finditer(markdown_text)]
    
    if not headers:
        # If no headers found, treat entire text as one section
        return [MarkdownSection(
            path=path,
            index=0,
            level=0,
            header="",
            content=markdown_text,
            parent_index=None,
            child_indices=[],
        )]
    
    # Create sections
    sections = []
    section_stack = []
    
    for i, (hashes, header_text, start_pos) in enumerate(headers):
        level = len(hashes)
        # Get section content (from this header to next header or end)
        end_pos = headers[i + 1][2] if i < len(headers) - 1 else len(markdown_text)
        content = markdown_text[start_pos:end_pos].strip()
        
        # Create new section
        section = MarkdownSection(
            path=path,
            index=i,
            level=level,
            header=header_text.strip(),
            content=content,
            parent_index=None,
            child_indices=[],
        )
        
        # Update parent-child relationships
        while section_stack and section_stack[-1].level >= level:
            section_stack.pop()
            
        if section_stack:
            parent = section_stack[-1]
            section.parent_index = parent.index
            parent.child_indices.append(section.index)
            
        section_stack.append(section)
        sections.append(section)
    
    return sections