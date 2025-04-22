from flask import Flask, render_template, jsonify, request, send_file
import os
import google.generativeai as genai
from dotenv import load_dotenv
from pymongo import MongoClient
import random
from fpdf import FPDF
import matplotlib.pyplot as plt
import json
import matplotlib
from io import BytesIO
matplotlib.use("Agg")
from fpdf import FPDF

load_dotenv()
app = Flask(__name__)

# Load JSON data from files
load_dotenv()
client = MongoClient("mongodb+srv://diya:diya@cluster0.mgkw8.mongodb.net/")
db = client["Dyslexia"]

# MongoDB collections
def get_or_create_collection(db, collection_name):
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
    return db[collection_name]

questions_collection = get_or_create_collection(db, "Assessment")
patterns_collection = get_or_create_collection(db, "Pattern")


# AI SUGGESTIONS
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


def generate_graph(scores):
    plt.figure(figsize=(6, 4))
    numeric_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
    categories = list(numeric_scores.keys())
    values = list(numeric_scores.values())
    plt.bar(categories, values, color=['blue', 'green', 'red'])
    plt.xlabel("Assessment Types")
    plt.ylabel("Scores")
    plt.title("Assessment Scores")
    
    graph_path = "temp_graph.png"  # Save as file
    plt.savefig(graph_path, format="png")
    plt.close()  
    return graph_path  # Return file path

def generate_ai_suggestion(scores):
    prompt = f"""
    Generate a detailed Early Childhood Development Assessment report for a child aged 4-8 years based on the following scores:

    Assessment (Memory & Recognition): {scores['assessment']}
    Pattern (Logical Thinking & Spatial Reasoning): {scores['pattern']}
    Reading (Reading & Comprehension): {scores['reading']}

    Report Requirements:
    Overview: Provide a summary of the child's performance across all areas.
    Detailed Analysis:
    Assessment (Memory & Recognition): Evaluate the child's ability to recall and recognize images, patterns, or information.
    Pattern (Logical Thinking & Spatial Reasoning): Analyze the child's ability to identify patterns, solve logical problems, and understand spatial relationships.
    Reading (Reading & Comprehension): Assess the child's reading fluency, comprehension, and ability to understand text.
    Strengths & Areas for Improvement: Highlight the child's strengths and identify areas where they may need additional support.
    Personalized Recommendations: Provide engaging and practical activities to help improve areas where the child may be struggling. Keep the recommendations fun and age-appropriate.
    Motivational Encouragement: End the report with a positive and motivating message to encourage continued learning and growth.
    Tone:
    Use an encouraging and supportive tone.
    Keep the feedback constructive and uplifting to boost confidence.
    Offer actionable and enjoyable strategies for improvement.

    Do not include the child's name in the report. Instead, refer to the child as 'the child' or 'they'. Also don't generate any special characters in the report.
    """
    model = genai.GenerativeModel("models/gemini-1.5-pro")
    response = model.generate_content(prompt)
    return response.text.strip()


    print(repr(scores_data))  
    print(repr(ai_suggestion))


def generate_pdf(scores, ai_suggestion):
    pdf = FPDF()
    pdf.add_page()

    # Use a Unicode-compatible font  
    pdf.set_font("Arial", "", 12)  

    pdf.set_auto_page_break(auto=True, margin=15)

    # Use UTF-8 text
    safe_text = ai_suggestion.encode("utf-8", "ignore").decode("utf-8")

    # Logo
    logo_path = "static/images/logo.jpeg"
    pdf.image(logo_path, x=80, y=10, w=30)
    pdf.ln(30)

    # Title
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, "Early Childhood Development Assessment Report", ln=True, align='C')
    pdf.ln(10)

    # Assessment Scores Section
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, "Assessment Scores", ln=True, align='L')
    pdf.cell(190, 0, "", ln=True, border="T")  
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    for key, value in scores.items():
        if value != "abc123":  
            pdf.cell(0, 8, f"{key}: {str(value)}", ln=True)
    pdf.ln(10)

    # AI Suggestions (Markdown Support)
    markdown_lines = ai_suggestion.split("\n")
    for line in markdown_lines:
        if line.startswith("# "):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, line[2:], ln=True)
        elif line.startswith("## "):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, line[3:], ln=True)
        else:
            font_style = ""
            if "***" in line:  
                font_style = "BI"
                line = line.replace("***", "")
            elif "**" in line:  
                font_style = "B"
                line = line.replace("**", "")
            elif "*" in line:  
                font_style = "I"
                line = line.replace("*", "")

            pdf.set_font("Arial", font_style, 10)
            pdf.multi_cell(0, 7, line)
        pdf.ln(2)

    # Graph Image
    pdf.ln(10)
    pdf.cell(0, 10, "Performance Graph:", ln=True)
    graph_path = generate_graph(scores)  
    pdf.image(graph_path, x=30, y=None, w=150)

    # Save PDF
    pdf_path = "Early_Childhood_Assessment_Report.pdf"
    pdf.output(pdf_path, "F")

    return pdf_path



@app.route("/generate-report", methods=["POST","GET"])
def generate_report():
    print("Received request")  # Check if this function runs

    data = request.get_json()  # Get JSON data from request
    print("Raw data received:", data)  # Debugging output

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    scores_data = data.get("scores")  # Extract scores
    print("Extracted scores:", scores_data)  # Debugging output

    if not scores_data:
        return jsonify({"error": "No scores found"}), 400

    # Generate AI suggestion and PDF (if scores are valid)
    ai_suggestion = generate_ai_suggestion(scores_data)
    pdf_path = generate_pdf(scores_data, ai_suggestion)

    return send_file(pdf_path, as_attachment=True)


@app.route('/activity')
def activity():
    return render_template('activity.html')

@app.route('/assessment')
def assessment():
    return render_template('assessment.html')

@app.route('/pattern')
def pattern():
    return render_template("pattern.html")

@app.route('/reading')
def reading():
    return render_template('reading.html')

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/onboarding')
def onboarding():
    return render_template('onboarding.html')

@app.route('/get_questions')
def get_questions():
    questions_collection = list(db.Assessment.find({}, {"_id": 0})) 
    shuffled_questions = random.sample(questions_collection, min(10, len(questions_collection)))  
    return jsonify(shuffled_questions)


@app.route('/get_patterns')
def get_patterns():
    patterns_collection = list(db.Pattern.find({}, {"_id": 0})) 
    shuffled_patterns = random.sample(patterns_collection, min(10, len(patterns_collection)))
    return jsonify(shuffled_patterns)

if __name__ == '__main__':
    app.run(debug=True)
