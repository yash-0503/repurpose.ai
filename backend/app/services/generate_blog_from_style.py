import os
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized")
    return _client


def get_blog_prompt(style_guide: str = None) -> str:
    base_prompt = """You are an expert technical writer. Convert the following video transcript into a well-structured blog post in Markdown format.

Requirements:
- Use proper Markdown headers (##, ###)
- Include a compelling introduction
- Break content into clear sections
- Add a "Key Takeaways" section at the end
- Write in a professional but easy-to-read tone
- Make it engaging and informative
"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def get_linkedin_prompt(style_guide: str = None, length: str = None) -> str:
    if length == "short":
        base_prompt = """Convert this video transcript into a SHORT LinkedIn post (300-500 words).

Requirements:
- Start with a strong hook
- Maximum 500 words
- 3-5 key points only
- Include relevant emojis
- End with a question or call-to-action
- Professional yet conversational tone
"""
    else:
        base_prompt = """Convert this video transcript into a LONG-FORM LinkedIn post (800-1200 words).

Requirements:
- Start with a compelling hook
- Tell a story or share insights
- Break into digestible paragraphs
- Use line breaks for readability
- Include relevant emojis (but not too many)
- End with a thought-provoking question
- Professional yet personal tone
"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def get_twitter_prompt(style_guide: str = None, thread_type: str = None) -> str:
    if thread_type == "thread":
        base_prompt = """Convert this video transcript into a Twitter THREAD.

Requirements:
- First tweet: Strong hook (under 280 chars)
- Break into 5-10 tweets
- Each tweet under 280 characters
- Number tweets (1/, 2/, etc.)
- Use simple language
- Include relevant emojis
- Last tweet: Call-to-action or summary
"""
    else:
        base_prompt = """Convert this video transcript into a SINGLE Twitter post.

Requirements:
- Maximum 280 characters
- Capture the main insight
- Use punchy, engaging language
- Include 1-2 relevant emojis
- Make every word count
"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def generate_blog_from_transcript(
    transcription: str,
    style_guide: str = None,
    output_format: str = "blog",
    output_option: str = None
) -> str:
    logger.info(f"Generating {output_format} content")
    client = get_client()

    if output_format == "blog":
        prompt = get_blog_prompt(style_guide)
    elif output_format == "linkedin":
        prompt = get_linkedin_prompt(style_guide, output_option)
    elif output_format == "twitter":
        prompt = get_twitter_prompt(style_guide, output_option)
    else:
        prompt = get_blog_prompt(style_guide)

    full_prompt = f"{prompt}\n\n--- TRANSCRIPT ---\n{transcription}\n--- END TRANSCRIPT ---"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
    )
    logger.info("Content generation complete")
    return response.text
