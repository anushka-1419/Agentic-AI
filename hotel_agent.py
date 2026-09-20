
import os
import time

from tavily import TavilyClient
from groq import Groq


# ============================================================
# API KEYS
# ============================================================

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is not set")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set")


# ============================================================
# INITIALIZE APIs
# ============================================================

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)

groq = Groq(
    api_key=GROQ_API_KEY
)


MODEL_NAME = "openai/gpt-oss-120b"


# ============================================================
# SEARCH HOTEL
# ============================================================

def search_hotel(hotel_name):

    print("Searching hotel reviews...")

    query = f"""
    {hotel_name} hotel reviews
    customer experiences
    hotel rating
    cleanliness
    rooms
    staff and service
    food
    location
    complaints
    value for money
    """

    try:

        response = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=8,
            include_answer=True
        )

        return response

    except Exception as e:

        print("Tavily Error:", repr(e))

        return None


# ============================================================
# EXTRACT INFORMATION
# ============================================================

def extract_information(search_results):

    if not search_results:
        return ""

    information = ""

    answer = search_results.get("answer", "")

    if answer:

        information += f"""
TAVILY SUMMARY:

{answer}

==================================================
"""

    results = search_results.get("results", [])

    for i, result in enumerate(results):

        title = result.get("title", "Unknown")
        content = result.get("content", "")
        url = result.get("url", "")

        information += f"""
SOURCE {i + 1}

TITLE:
{title}

CONTENT:
{content}

URL:
{url}

==================================================
"""

    return information


# ============================================================
# GROQ ANALYSIS
# ============================================================

def analyze_hotel(hotel_name, hotel_information):

    print("Groq is analyzing the hotel...")

    prompt = f"""
You are an AI Hotel Review Analyst.

Analyze the hotel using ONLY the supplied web research.

HOTEL NAME:
{hotel_name}

WEB RESEARCH:
{hotel_information}

Create a professional hotel review report.

Use exactly these sections:

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

RULES:

- Do not invent information.
- Use only the supplied research.
- If information is unavailable, say "Not enough information."
- Do not treat one review as a universal fact.
- Mention recurring patterns where possible.
- Keep the language professional and concise.
- Use bullet points where useful.
- Do not add a report title.
"""

    for attempt in range(3):

        try:

            response = groq.chat.completions.create(

                model=MODEL_NAME,

                messages=[

                    {
                        "role": "system",
                        "content": (
                            "You are a professional hotel review "
                            "analyst. Use only the supplied research."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ],

                temperature=0.3,
                max_tokens=4000

            )

            result = response.choices[0].message.content

            if result and result.strip():
                return result.strip()

            print("Groq returned an empty response.")

            return None

        except Exception as e:

            error = str(e)

            print(f"Groq Error (Attempt {attempt + 1}):", error)

            if (
                "429" in error
                or "rate_limit" in error.lower()
                or "503" in error
                or "timeout" in error.lower()
            ):

                if attempt < 2:
                    time.sleep(4)
                    continue

            return None

    return None


# ============================================================
# CHAT ABOUT HOTEL
# ============================================================

def chat_about_hotel(
    hotel_name,
    question,
    analysis,
    sources
):

    print("Generating chatbot response...")

    source_text = ""

    for i, source in enumerate(sources):

        title = source.get("title", "")
        content = source.get("content", "")
        url = source.get("url", "")

        source_text += f"""
SOURCE {i + 1}

TITLE:
{title}

CONTENT:
{content}

URL:
{url}

==================================================
"""

    prompt = f"""
You are StayWise AI, a hotel review assistant.

HOTEL NAME:
{hotel_name}

PREVIOUS AI ANALYSIS:
{analysis}

RESEARCH SOURCES:
{source_text}

USER QUESTION:
{question}

INSTRUCTIONS:

- Answer using only the supplied analysis and research.
- Do not invent hotel information.
- If the information is unavailable, say:
  "Not enough information from the available research."
- Be helpful, professional, and concise.
- Use bullet points where useful.
"""

    for attempt in range(3):

        try:

            response = groq.chat.completions.create(

                model=MODEL_NAME,

                messages=[

                    {
                        "role": "system",
                        "content": (
                            "You are a helpful hotel review assistant. "
                            "Never invent information."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ],

                temperature=0.3,
                max_tokens=1500

            )

            result = response.choices[0].message.content

            if result and result.strip():
                return result.strip()

            return None

        except Exception as e:

            error = str(e)

            print(f"Chat Error (Attempt {attempt + 1}):", error)

            if (
                "429" in error
                or "rate_limit" in error.lower()
                or "503" in error
                or "timeout" in error.lower()
            ):

                if attempt < 2:
                    time.sleep(4)
                    continue

            return None

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("AI HOTEL REVIEW AGENT")
    print("=" * 60)

    hotel_name = input("Enter hotel name: ").strip()

    if not hotel_name:
        print("Please enter a hotel name.")
        return

    search_results = search_hotel(hotel_name)

    if not search_results:
        print("Hotel search failed.")
        return

    hotel_information = extract_information(search_results)

    if not hotel_information.strip():
        print("No information found.")
        return

    analysis = analyze_hotel(
        hotel_name,
        hotel_information
    )

    if not analysis:
        print("AI analysis failed.")
        return

    print("\nAI HOTEL REVIEW REPORT")
    print("=" * 60)
    print(analysis)

    print("\nSOURCES")
    print("=" * 60)

    for i, result in enumerate(
        search_results.get("results", [])
    ):

        print(f"{i + 1}. {result.get('title', 'Unknown')}")
        print(result.get("url", ""))


if __name__ == "__main__":
    main()
