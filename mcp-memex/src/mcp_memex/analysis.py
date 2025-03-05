from typing import Tuple
import anthropic
import os

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 4096
SYSTEM_PROMPT = """You are an expert research assistant.
Your task is to read through the given content and and extract all the information relevant to the question.
Do not answer the question, just extract the information.
You will be given a taxonomy of topics. 
Make sure to include [[wikilinks]] to any relevant topics which appear in your answer.
You should try to include as many relevant topics as possible.
The format of your output should be a detailed Markdown document with bullet points and blockquotes.
The first line of the document should be a short title for the document.
Every blockquote must be followed by a citation pointing back to the URL of the original content.
DO NOT include any other text or commentary in your output.
"""

def build_prompt(query: str, content: str, url: str, topics: dict) -> str:
    taxonomy = ""
    for topic in topics:
        taxonomy += f'## {topic}\n\n{topics[topic]}\n\n'
    return f"""Given the following taxonomy and content, extract all the information relevant to the question:

Topics:

{taxonomy}

Question: {query}

URL: {url}

Content: {content}
"""


async def analyze_content(query: str, content: str, url: str, topics: dict) -> Tuple[str, str]:
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    prompt = build_prompt(query, content, url, topics)
    response = client.messages.create(
        max_tokens=MAX_TOKENS,
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
    )

    if len(response.content) == 0:
        raise ValueError("No response from LLM")
    
    if response.content[0].type != "text":
        raise ValueError("LLM did not return text")
    content = response.content[0].text
    content_lines = content.splitlines()
    title = content_lines[0].replace("# ", "").strip()
    content = "\n".join(content_lines[1:])

    return title, content