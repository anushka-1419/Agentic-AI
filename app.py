import os
from flask import Flask, render_template, request, jsonify

from hotel_agent import (
    search_hotel,
    extract_information,
    analyze_hotel,
    chat_about_hotel
)

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "success": True,
        "message": "StayWise AI is running"
    })


@app.route("/analyze", methods=["POST"])
def analyze():

    try:
        data = request.get_json(silent=True) or {}

        hotel_name = data.get("hotel_name", "").strip()

        if not hotel_name:
            return jsonify({
                "success": False,
                "error": "Please enter a hotel name."
            }), 400

        # STEP 1: Search hotel
        search_results = search_hotel(hotel_name)

        if not search_results:
            return jsonify({
                "success": False,
                "error": "Unable to find hotel information."
            }), 502

        # STEP 2: Extract information
        hotel_information = extract_information(search_results)

        if not hotel_information.strip():
            return jsonify({
                "success": False,
                "error": "No hotel information was found."
            }), 404

        # STEP 3: AI analysis
        analysis = analyze_hotel(
            hotel_name,
            hotel_information
        )

        if not analysis:
            return jsonify({
                "success": False,
                "error": "AI analysis failed. Check your Groq API key and logs."
            }), 502

        # STEP 4: Sources
        sources = []

        for result in search_results.get("results", []):

            sources.append({
                "title": result.get("title", "Unknown"),
                "url": result.get("url", ""),
                "content": result.get("content", "")
            })

        return jsonify({
            "success": True,
            "hotel": hotel_name,
            "analysis": analysis,
            "sources": sources
        })

    except Exception as e:

        print("ANALYZE ERROR:", repr(e))

        return jsonify({
            "success": False,
            "error": "Something went wrong while analyzing the hotel."
        }), 500


@app.route("/chat", methods=["POST"])
def chat():

    try:
        data = request.get_json(silent=True) or {}

        hotel_name = data.get("hotel_name", "").strip()
        question = data.get("question", "").strip()
        analysis = data.get("analysis", "")
        sources = data.get("sources", [])

        if not hotel_name or not question:
            return jsonify({
                "success": False,
                "error": "Hotel name and question are required."
            }), 400

        answer = chat_about_hotel(
            hotel_name=hotel_name,
            question=question,
            analysis=analysis,
            sources=sources
        )

        if not answer:
            return jsonify({
                "success": False,
                "error": "Unable to generate an answer."
            }), 502

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as e:

        print("CHAT ERROR:", repr(e))

        return jsonify({
            "success": False,
            "error": "Chat service is temporarily unavailable."
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
