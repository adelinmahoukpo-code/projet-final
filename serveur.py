from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import csv
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env (local)
load_dotenv()

EMAIL = os.getenv("GMAIL_USERNAME")
PASSWORD = os.getenv("GMAIL_PASSWORD")

app = Flask(__name__)
CORS(app)  # Autoriser toutes les origines (évite Failed to fetch)

# 📌 Route principale : sert index.html
@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

# 📌 Route pour envoyer un mail
@app.route("/sendmail", methods=["POST"])
def sendmail():
    # Support JSON ou form-data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    destinataire = data.get("to_email")
    messagePerso = data.get("message", "")
    refFacture   = data.get("invoice_ref", "")
    fromName     = data.get("from_name", "Mon Service Facture")
    fromContact  = data.get("agent_contact", "")
    sujet        = data.get("subject", "Nouvelle Facture")

    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = destinataire
    msg["Subject"] = sujet

    corps = f"""
    Bonjour,<br><br>
    Référence facture : <b>{refFacture}</b><br>
    Message : {messagePerso}<br><br>
    Contact : {fromName} ({fromContact})
    """
    msg.attach(MIMEText(corps, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, destinataire, msg.as_string())
        server.quit()
        return jsonify({"status": "success", "message": "Email envoyé avec succès"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# 📌 Route pour renvoyer la liste des entreprises
@app.route("/entreprises")
def get_entreprises():
    entreprises = []
    csv_path = os.path.join(os.path.dirname(__file__), "entreprises_geocodes.csv")
    
    # Vérifie si le fichier existe
    if not os.path.exists(csv_path):
        return jsonify({"error": "Fichier CSV non trouvé"}), 404

    try:
        # Lire le CSV avec encodage latin-1 pour éviter UnicodeDecodeError
        with open(csv_path, newline="", encoding="latin-1") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                entreprises.append(row)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(entreprises)

if __name__ == "__main__":
    # Récupérer le port fourni par Render ou utiliser 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
