from flask import Flask, request, send_from_directory, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import os
import csv
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

EMAIL = os.getenv("GMAIL_USERNAME")
PASSWORD = os.getenv("GMAIL_PASSWORD")

app = Flask(__name__)

# 📌 Route principale : sert index.html
@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

# 📌 Route pour envoyer un mail
@app.route("/sendmail", methods=["POST"])
def sendmail():
    destinataire = request.form.get("to_email")
    messagePerso = request.form.get("message", "")
    refFacture   = request.form.get("invoice_ref", "")
    fromName     = request.form.get("from_name", "Mon Service Facture")
    fromContact  = request.form.get("agent_contact", "")
    sujet        = request.form.get("subject", "Nouvelle Facture")

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

# 📌 Nouvelle route : renvoyer la liste des entreprises
@app.route("/entreprises")
def get_entreprises():
    entreprises = []
    csv_path = os.path.join(os.path.dirname(__file__), "entreprises_geocodes.csv")
    
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            entreprises.append(row)
    
    return jsonify(entreprises)

if __name__ == "__main__":
    app.run(debug=True)
