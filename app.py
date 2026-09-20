
from flask import Flask, render_template, request, jsonify

from hotel_agent import (
    search_hotel,
    extract_information,
    analyze_hotel,
    chat_about_hotel,
    HotelAgentError
)


app = Flask(__name__)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "message": "StayWise AI server is running."
    })


# ============================================================
# ANALYZE HOTEL
# ============================================================

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(silent=True) or {}

        hotel_name = str(
            data.get("hotel_name", "")
        ).strip()

        if not hotel_name:
            return jsonify({
                "success": False,
                "error": "Please enter a hotel name."
            }), 400

        print(f"\nStarting analysis for: {hotel_name}")

        # STEP 1: WEB SEARCH
        search_results = search_hotel(hotel_name)

        # STEP 2: EXTRACT INFORMATION
        hotel_information = extract_information(
            search_results
        )

        if not hotel_information:
            return jsonify({
                "success": False,
                "error": (
                    "No research information was found "
                    "for this hotel."
                )
            }), 502

        # STEP 3: GENERATE AI REPORT
        analysis = analyze_hotel(
            hotel_name,
            hotel_information
        )

        if not analysis:
            return jsonify({
                "success": False,
                "error": "AI report was empty."
            }), 502

        # STEP 4: PREPARE SOURCES
        sources = []

        for result in search_results.get("results", []):
            sources.append({
                "title": result.get(
                    "title",
                    "Unknown source"
                ),
                "url": result.get("url", ""),
                "content": result.get("content", "")
            })

        print(f"Analysis completed for: {hotel_name}")

        return jsonify({
            "success": True,
            "hotel": hotel_name,
            "analysis": analysis,
            "sources": sources
        }), 200

    except HotelAgentError as error:
        print("AGENT ERROR:", str(error))

        return jsonify({
            "success": False,
            "error": str(error)
        }), 502

    except Exception as error:
        print("UNEXPECTED ERROR:", repr(error))

        return jsonify({
            "success": False,
            "error": (
                "Unexpected server error. "
                "Check the Flask terminal."
            )
        }), 500


# ============================================================
# CHAT
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        hotel_name = str(
            data.get("hotel_name", "")
        ).strip()

        question = str(
            data.get("question", "")
        ).strip()

        analysis = str(
            data.get("analysis", "")
        )

        sources = data.get("sources", [])

        if not hotel_name:
            return jsonify({
                "success": False,
                "error": "Hotel name is missing."
            }), 400

        if not question:
            return jsonify({
                "success": False,
                "error": "Please enter a question."
            }), 400

        answer = chat_about_hotel(
            hotel_name=hotel_name,
            question=question,
            analysis=analysis,
            sources=sources
        )

        return jsonify({
            "success": True,
            "answer": answer
        }), 200

    except HotelAgentError as error:
        print("CHAT AGENT ERROR:", str(error))

        return jsonify({
            "success": False,
            "error": str(error)
        }), 502

    except Exception as error:
        print("CHAT UNEXPECTED ERROR:", repr(error))

        return jsonify({
            "success": False,
            "error": "Unable to generate chat response."
        }), 500


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
