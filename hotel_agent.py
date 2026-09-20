
import os
import time

from tavily import TavilyClient
from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)


# ============================================================
# CLIENTS
# ============================================================

tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ============================================================
# CUSTOM ERROR
# ============================================================

class HotelAgentError(Exception):
    pass


def validate_clients():
    if not TAVILY_API_KEY:
        raise HotelAgentError(
            "TAVILY_API_KEY is missing. Add it to your environment variables."
        )

    if not GROQ_API_KEY:
        raise HotelAgentError(
            "GROQ_API_KEY is missing. Add it to your environment variables."
        )


# ============================================================
# TAVILY SEARCH
# ============================================================

def search_hotel(hotel_name):
    validate_clients()

    query = f"""
    {hotel_name} hotel reviews
    guest experiences
    cleanliness
    room quality
    staff and service
    food and dining
    location
    facilities
    complaints
    value for money
    """

    print(f"Searching information for: {hotel_name}")

    try:
        response = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=8,
            include_answer=True
        )

        if not response:
            raise HotelAgentError(
                "Tavily returned an empty response."
            )

        results = response.get("results", [])

        if not results and not response.get("answer"):
            raise HotelAgentError(
                "No hotel information was found by Tavily."
            )

        return response

    except HotelAgentError:
        raise

    except Exception as error:
        print("TAVILY ERROR:", repr(error))

        raise HotelAgentError(
            f"Tavily search failed: {str(error)}"
        ) from error


# ============================================================
# EXTRACT RESEARCH
# ============================================================

def extract_information(search_results):
    if not search_results:
        return ""

    information_parts = []

    answer = search_results.get("answer", "")

    if answer:
        information_parts.append(
            f"TAVILY SUMMARY:\n{answer}"
        )

    results = search_results.get("results", [])

    for index, result in enumerate(results, start=1):
        title = result.get("title", "Unknown source")
        content = result.get("content", "")
        url = result.get("url", "")

        information_parts.append(
            f"""
SOURCE {index}

TITLE:
{title}

CONTENT:
{content}

URL:
{url}
"""
        )

    return "\n\n".join(information_parts).strip()


# ============================================================
# AI REPORT
# ============================================================

def analyze_hotel(hotel_name, hotel_information):
    validate_clients()

    if not hotel_information.strip():
        raise HotelAgentError(
            "There is no research data available for analysis."
        )

    prompt = f"""
You are a professional hotel review analyst.

Analyze the hotel using ONLY the supplied research.
Do not invent facts, ratings, facilities, or guest opinions.

HOTEL NAME:
{hotel_name}

RESEARCH:
{hotel_information}

Create a clear report using exactly these numbered sections:

1. ⭐ OVERALL IMPRESSION
2. 😊 OVERALL SENTIMENT
3. 👍 WHAT GUESTS LIKE
4. 👎 COMMON COMPLAINTS
5. 🧹 CLEANLINESS
6. 🛏️ ROOM QUALITY
7. 👨‍💼 STAFF & SERVICE
8. 🍽️ FOOD
9. 📍 LOCATION
10. 💰 VALUE FOR MONEY
11. ⚠️ RECURRING PROBLEMS
12. 💡 FINAL AI SUMMARY

Rules:

- Use only the supplied research.
- If information is unavailable, write "Not enough information."
- Do not treat one review as a universal fact.
- Mention recurring patterns where possible.
- Use bullet points where useful.
- Keep the report professional and readable.
- Do not add a separate report title.
- Do not use markdown tables.
"""

    for attempt in range(3):
        try:
            print(
                f"Generating AI report... attempt {attempt + 1}/3"
            )

            response = groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful hotel review analyst. "
                            "Use only the supplied research and never "
                            "invent information."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=6000
            )

            if not response.choices:
                raise HotelAgentError(
                    "Groq returned no choices."
                )

            content = response.choices[0].message.content

            if not content or not content.strip():
                raise HotelAgentError(
                    "Groq returned an empty AI report."
                )

            return content.strip()

        except HotelAgentError:
            raise

        except Exception as error:
            error_text = str(error)

            print("GROQ ERROR:", repr(error))

            temporary_error = (
                "429" in error_text
                or "rate_limit" in error_text.lower()
                or "503" in error_text
                or "timeout" in error_text.lower()
                or "temporarily" in error_text.lower()
            )

            if temporary_error and attempt < 2:
                time.sleep(3)
                continue

            raise HotelAgentError(
                f"Groq analysis failed: {error_text}"
            ) from error

    raise HotelAgentError(
        "Groq was unavailable after multiple attempts."
    )


# ============================================================
# CHAT ASSISTANT
# ============================================================

def chat_about_hotel(
    hotel_name,
    question,
    analysis="",
    sources=None
):
    validate_clients()

    sources = sources or []

    source_text = "\n".join(
        f"{source.get('title', '')}: {source.get('url', '')}"
        for source in sources
    )

    prompt = f"""
You are StayWise AI, a hotel review assistant.

Hotel:
{hotel_name}

Existing AI report:
{analysis}

Research sources:
{source_text}

User question:
{question}

Answer using only the available report and research.
If the information is unavailable, clearly say:
"Not enough information."

Keep the answer concise and useful.
"""

    try:
        response = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful and evidence-based "
                        "hotel review assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1200
        )

        if not response.choices:
            raise HotelAgentError(
                "Groq returned no chat response."
            )

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            raise HotelAgentError(
                "Groq returned an empty chat response."
            )

        return answer.strip()

    except HotelAgentError:
        raise

    except Exception as error:
        print("CHAT ERROR:", repr(error))

        raise HotelAgentError(
            f"Chat response failed: {str(error)}"
        ) from error
