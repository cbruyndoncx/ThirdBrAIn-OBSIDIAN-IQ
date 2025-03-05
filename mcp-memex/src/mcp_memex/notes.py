from pathlib import Path
import datetime
import yaml

def add_journal_entry(entry: str, vault_path: Path) -> None:
    title = datetime.datetime.now().strftime('%Y-%m-%d')
    daily_note_path = vault_path / "Journal" / f"{title}.md"
    daily_note_path.parent.mkdir(parents=True, exist_ok=True)

    content = ""
    if daily_note_path.exists():
        content = daily_note_path.read_text().rstrip() + "\n"
    content += entry.rstrip() + "\n"

    with open(daily_note_path, "w") as f:
        f.write(content)

def add_note(title: str, note: str, vault_path: Path) -> None:
    note_path = vault_path / "Notes" / f"{title}.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    with open(note_path, "w") as f:
        f.write(note)

def add_artifact(title: str, artifact: str, vault_path: Path) -> None:
    artifact_path = vault_path / "Artifacts" / f"{title}.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifact_path, "w") as f:
        f.write(artifact)

def get_topics(vault_path: Path) -> dict[str, str]:
    topics_path = vault_path / "Topics"
    taxonomy = {}
    for topic_path in topics_path.glob("*.md"):
        title = topic_path.stem
        content = topic_path.read_text()
        taxonomy[title] = content
    return taxonomy

def get_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file.
    
    Args:
        content: The full content of the markdown file as a string
        
    Returns:
        tuple: (frontmatter_dict, remaining_content)
            - frontmatter_dict: Dictionary containing the parsed YAML frontmatter
            - remaining_content: The rest of the markdown content without frontmatter
    """
    
    # Check if content starts with frontmatter delimiter
    if not content.startswith('---\n'):
        return {}, content
        
    # Find the closing frontmatter delimiter
    try:
        end_idx = content.index('\n---\n', 4)  # Start search after first delimiter
    except ValueError:
        return {}, content
        
    # Extract and parse frontmatter
    frontmatter_str = content[4:end_idx]  # Skip first '---\n'
    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError:
        return {}, content
        
    # Get remaining content (skip closing delimiter)
    remaining_content = content[end_idx + 5:]
    
    return frontmatter, remaining_content