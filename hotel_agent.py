import os
import time

from flask import Flask, render_template, request, jsonify

from tavily import TavilyClient
from groq import Groq

# ============================================================
# API KEYS  (now read from environment variables so this works
# after deploying — set TAVILY_API_KEY and GROQ_API_KEY on your
# host, e.g. Render / Railway / Heroku env vars, or a .env file
# loaded before this module runs)
# ============================================================

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


# ============================================================
# INITIALIZE APIs
# ============================================================

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)

groq = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# SEARCH HOTEL
# ============================================================

def search_hotel(hotel_name):

    print("\n🔎 Searching the web for hotel reviews...")
    print("Please wait...\n")

    query = f"""
    {hotel_name} hotel reviews
    customer reviews
    guest experience
    hotel rating
    cleanliness
    rooms
    staff service
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

        print("\n❌ Tavily Error:")
        print(e)

        return None


# ============================================================
# EXTRACT INFORMATION
# ============================================================

def extract_information(search_results):

    information = ""

    answer = search_results.get(
        "answer",
        ""
    )

    if answer:

        information += f"""

TAVILY SUMMARY:

{answer}

==================================================
"""


    results = search_results.get(
        "results",
        []
    )


    for i, result in enumerate(results):

        title = result.get(
            "title",
            "Unknown"
        )

        content = result.get(
            "content",
            ""
        )

        url = result.get(
            "url",
            ""
        )


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

    print("🤖 Groq is analyzing the hotel...")
    print("Please wait...\n")

    prompt = f"""
You are an AI Hotel Review Analyst.

Analyze the following hotel using ONLY the supplied
web research.

HOTEL NAME:
{hotel_name}

WEB RESEARCH:
{hotel_information}


Create a professional hotel review report.

IMPORTANT:

Do NOT create a report title.

Do NOT write:

AI HOTEL REVIEW REPORT

Do NOT use lines such as:

==================================================

Do NOT write:

HOTEL: {hotel_name}


Use exactly these sections:

1. ⭐ OVERALL IMPRESSION

2. 😊 OVERALL SENTIMENT

Choose one:
Positive
Neutral
Negative

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

• Do NOT invent information.
• Only use supplied research.
• If information is unavailable, say "Not enough information."
• Do not treat one review as a universal fact.
• Mention recurring patterns where possible.
• Keep the language professional and concise.
• Use bullet points where useful.
"""

    for attempt in range(3):

        try:

            response = groq.chat.completions.create(

                model="openai/gpt-oss-120b",

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional hotel review "
                            "analyst. Follow the instructions "
                            "strictly and do not invent information."
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

            return response.choices[0].message.content

        except Exception as e:

            error = str(e)

            if (
                "429" in error
                or "rate_limit" in error.lower()
                or "503" in error
                or "timeout" in error.lower()
            ):

                print(
                    f"⚠️ Groq temporarily unavailable. "
                    f"Retrying... ({attempt + 1}/3)"
                )

                time.sleep(4)

            else:

                print("\n❌ Groq Error:")
                print(e)

                return None


    print("\n❌ Groq is currently unavailable.")

    return None


# ============================================================
# CHATBOT — answer follow-up questions about the hotel
# ============================================================

def chat_with_hotel_ai(hotel_name, question, analysis, sources):

    print(f"💬 Chatbot answering question about {hotel_name}...")

    # Build a compact context out of the sources so the chatbot
    # can reference real review content, not just the report.

    sources_context = ""

    for i, source in enumerate(sources or []):

        title = source.get("title", "Unknown")
        content = source.get("content", "")
        url = source.get("url", "")

        sources_context += f"""

SOURCE {i + 1}: {title}
{content}
URL: {url}
==================================================
"""

    prompt = f"""
You are the StayWise AI Assistant, a friendly hotel review chatbot.

HOTEL NAME:
{hotel_name}

EXISTING AI REPORT ABOUT THIS HOTEL:
{analysis}

RAW REVIEW SOURCES:
{sources_context}

GUEST QUESTION:
{question}

INSTRUCTIONS:

• Answer ONLY using the report and sources above.
• If the answer isn't covered by them, say you don't have
  enough information from the reviews to answer that.
• Keep the answer conversational, concise (2-5 sentences
  unless the question needs a list), and helpful.
• Do not invent facts, ratings, or amenities.
• You may use short bullet points for lists like
  complaints or amenities.
"""

    for attempt in range(3):

        try:

            response = groq.chat.completions.create(

                model="openai/gpt-oss-120b",

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful, concise hotel review "
                            "assistant. Only use the supplied report "
                            "and sources. Never invent information."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.4,

                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:

            error = str(e)

            if (
                "429" in error
                or "rate_limit" in error.lower()
                or "503" in error
                or "timeout" in error.lower()
            ):

                print(
                    f"⚠️ Groq temporarily unavailable. "
                    f"Retrying... ({attempt + 1}/3)"
                )

                time.sleep(3)

            else:

                print("\n❌ Groq Chat Error:")
                print(e)

                return None

    print("\n❌ Groq is currently unavailable for chat.")

    return None


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze_route():

    data = request.get_json(silent=True) or {}

    hotel_name = (data.get("hotel_name") or "").strip()

    if not hotel_name:

        return jsonify(
            success=False,
            error="Please enter a hotel name."
        ), 400


    search_results = search_hotel(hotel_name)

    if search_results is None:

        return jsonify(
            success=False,
            error="Unable to search for hotel information."
        ), 502


    hotel_information = extract_information(search_results)

    if not hotel_information.strip():

        return jsonify(
            success=False,
            error="No information found for this hotel."
        ), 404


    analysis = analyze_hotel(hotel_name, hotel_information)

    if analysis is None:

        return jsonify(
            success=False,
            error="AI analysis is currently unavailable."
        ), 502


    raw_results = search_results.get("results", [])

    sources = []

    for result in raw_results:

        sources.append({
            "title": result.get("title", "Unknown"),
            "url": result.get("url", ""),
            "content": result.get("content", "")
        })


    return jsonify(
        success=True,
        hotel=hotel_name,
        analysis=analysis,
        sources=sources
    )


@app.route("/chat", methods=["POST"])
def chat_route():

    data = request.get_json(silent=True) or {}

    hotel_name = (data.get("hotel_name") or "").strip()
    question = (data.get("question") or "").strip()
    analysis = data.get("analysis") or ""
    sources = data.get("sources") or []

    if not hotel_name or not question:

        return jsonify(
            success=False,
            error="Missing hotel name or question."
        ), 400


    answer = chat_with_hotel_ai(
        hotel_name,
        question,
        analysis,
        sources
    )

    if answer is None:

        return jsonify(
            success=False,
            error="Unable to get AI response right now."
        ), 502


    return jsonify(
        success=True,
        answer=answer
    )


# ============================================================
# OPTIONAL: CLI MODE (same behaviour as before)
# Run with:  python hotel_agent.py cli
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("          🏨 AI HOTEL REVIEW AGENT")
    print("=" * 60)

    print(
        "\nThis AI Agent uses:"
        "\n🔎 Tavily → Web Research"
        "\n🤖 Groq → Review Analysis"
    )

    print("\n" + "=" * 60)


    hotel_name = input(
        "\n🏨 Enter hotel name: "
    ).strip()


    if not hotel_name:

        print(
            "\n❌ Please enter a hotel name."
        )

        return


    search_results = search_hotel(
        hotel_name
    )


    if search_results is None:
        return


    hotel_information = extract_information(
        search_results
    )


    if not hotel_information.strip():

        print(
            "\n❌ No information found."
        )

        return


    print(
        "✅ Hotel information collected!"
    )


    results = search_results.get(
        "results",
        []
    )


    print("\n" + "=" * 60)
    print("🌐 SOURCES USED")
    print("=" * 60)


    for i, result in enumerate(results):

        title = result.get(
            "title",
            "Unknown"
        )

        url = result.get(
            "url",
            ""
        )

        print(
            f"\n{i + 1}. {title}"
        )

        print(
            f"   {url}"
        )


    analysis = analyze_hotel(
        hotel_name,
        hotel_information
    )


    if analysis is None:
        return


    print("\n")
    print("=" * 60)
    print("              🤖 AI ANALYSIS")
    print("=" * 60)

    print(analysis)

    print("\n" + "=" * 60)
    print("✅ Hotel analysis completed!")
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "cli":

        main()

    else:

        port = int(os.environ.get("PORT", 5000))

        app.run(
            host="0.0.0.0",
            port=port,
            debug=False
        )
