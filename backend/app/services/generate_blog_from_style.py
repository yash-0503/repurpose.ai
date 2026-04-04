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


ADAPTIVE_PREAMBLE = """STEP 1 — Detect content type:
Read the transcript and determine what kind of video this is (e.g. educational tutorial, podcast conversation, product announcement, motivational talk, interview, news commentary, coding walkthrough, review, vlog, etc.).

STEP 2 — Adapt your structure to match:
- Educational/tutorial → focus on the lesson, key concepts, and practical takeaways
- Podcast/interview → pull out the best insights, stories, and memorable quotes
- Announcement/launch → build hype, highlight what's new, and why it matters
- Motivational/storytelling → capture the emotional arc and the core message
- Technical/coding → distill the approach, tradeoffs, and what the viewer will learn
- Any other type → use your judgment to pick the most engaging angle

STEP 3 — Write in a storytelling voice:
- Short, punchy sentences. Line break after every sentence.
- Simple, conversational language. No corporate jargon.
- Personal and real — write like a human, not a press release.
- Strong emotional hook as the opening line.
"""


def get_blog_prompt(style_guide: str = None, youtube_url: str = None) -> str:
    cta = ""
    if youtube_url:
        cta = f"\n- End with: 🎬 Watch the full video here: {youtube_url}\n"

    base_prompt = f"""{ADAPTIVE_PREAMBLE}
Now convert the transcript into a well-structured BLOG POST in Markdown.

Requirements:
- Use Markdown headers (##, ###) to break into clear sections
- Compelling introduction that hooks the reader
- Adapt section structure to the content type you detected
- Add a "Key Takeaways" bullet list near the end
- Professional but easy-to-read tone
- Make it engaging and informative
{cta}"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def get_linkedin_prompt(style_guide: str = None, length: str = None, youtube_url: str = None) -> str:
    cta = ""
    if youtube_url:
        cta = f"\n- End with a call-to-action:\n  🎬 Want to learn more? Watch the full video: {youtube_url}\n"

    if length == "short":
        base_prompt = f"""{ADAPTIVE_PREAMBLE}
Now convert the transcript into a SHORT LinkedIn post.

Requirements:
- 120-180 words ONLY, do NOT exceed 180 words
- Adapt the narrative structure to the content type you detected
- Use bullet points where they help readability
- Keep it personal and real
{cta}"""
    else:
        base_prompt = f"""{ADAPTIVE_PREAMBLE}
Now convert the transcript into a LONG-FORM LinkedIn post.

Requirements:
- 400-600 words
- Adapt the narrative structure to the content type you detected
- Use bullet points where they help readability
- Go deeper on the ideas — add personal perspective and reflection
- Keep it personal and real
{cta}"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def get_twitter_prompt(style_guide: str = None, thread_type: str = None, youtube_url: str = None) -> str:
    cta = ""
    if youtube_url:
        cta = f"\n- Include the video link in the last tweet: {youtube_url}\n"

    if thread_type == "thread":
        base_prompt = f"""{ADAPTIVE_PREAMBLE}
Now convert the transcript into a Twitter/X THREAD.

Requirements:
- First tweet: Strong hook (under 280 chars)
- 5-10 tweets, each under 280 characters
- Number tweets (1/, 2/, etc.)
- Adapt the thread flow to the content type you detected
- Simple language, relevant emojis
- Last tweet: summary or call-to-action
{cta}"""
    else:
        base_prompt = f"""{ADAPTIVE_PREAMBLE}
Now convert the transcript into a SINGLE tweet.

Requirements:
- Maximum 280 characters
- Capture the single most powerful insight
- Punchy, engaging language
- 1-2 relevant emojis
- Make every word count
"""

    if style_guide:
        base_prompt += f"\n**IMPORTANT**: Write in this specific style:\n{style_guide}\n"

    return base_prompt


def generate_blog_from_transcript(
    transcription: str,
    style_guide: str = None,
    output_format: str = "blog",
    output_option: str = None,
    youtube_url: str = None,
) -> str:
    logger.info(f"Generating {output_format} content")
    client = get_client()

    if output_format == "blog":
        prompt = get_blog_prompt(style_guide, youtube_url)
    elif output_format == "linkedin":
        prompt = get_linkedin_prompt(style_guide, output_option, youtube_url)
    elif output_format == "twitter":
        prompt = get_twitter_prompt(style_guide, output_option, youtube_url)
    else:
        prompt = get_blog_prompt(style_guide, youtube_url)

    full_prompt = f"{prompt}\n\n--- TRANSCRIPT ---\n{transcription}\n--- END TRANSCRIPT ---"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
    )
    logger.info("Content generation complete")
    return response.text
