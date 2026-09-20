from flask import Flask, render_template, request, jsonify

from hotel_agent import search_hotel, extract_information, analyze_hotel

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    try:
        data = request.get_json()

        hotel_name = data.get("hotel_name", "").strip()

        if not hotel_name:
            return jsonify({
                "success": False,
                "error": "Please enter a hotel name."
            })

        # -----------------------------------------
        # STEP 1: SEARCH WEB
        # -----------------------------------------

        search_results = search_hotel(hotel_name)

        if search_results is None:
            return jsonify({
                "success": False,
                "error": "Unable to search for hotel information."
            })

        # -----------------------------------------
        # STEP 2: EXTRACT INFORMATION
        # -----------------------------------------

        hotel_information = extract_information(search_results)

        if not hotel_information.strip():
            return jsonify({
                "success": False,
                "error": "No hotel information was found."
            })

        # -----------------------------------------
        # STEP 3: GEMINI ANALYSIS
        # -----------------------------------------

        analysis = analyze_hotel(
            hotel_name,
            hotel_information
        )

        if analysis is None:
            return jsonify({
                "success": False,
                "error": "AI analysis is temporarily unavailable. Please try again."
            })

        # -----------------------------------------
        # STEP 4: SOURCES
        # -----------------------------------------

        sources = []

        for result in search_results.get("results", []):

            sources.append({
                "title": result.get("title", "Unknown"),
                "url": result.get("url", "")
            })

        return jsonify({
            "success": True,
            "hotel": hotel_name,
            "analysis": analysis,
            "sources": sources
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "success": False,
            "error": "Something went wrong. Please try again."
        })


if __name__ == "__main__":
    app.run(debug=True)
