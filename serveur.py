import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

# 📌 Chemin absolu vers le dossier du projet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 📌 Route principale : sert index.html
@app.route("/")
def home():
    return send_file(os.path.join(BASE_DIR, "index.html"))

# 📌 Route pour envoyer une facture par mail
@app.route("/sendmail", methods=["POST"])
def sendmail():
    try:
        # Champs envoyés par ton frontend
        to_email = request.form.get("to") or request.form.get("to_email")
        subject = request.form.get("subject", "Facture")
        message = request.form.get("message", "")
        file = request.files.get("file")  # fichier optionnel

        if not to_email:
            return jsonify({"error": "Destinataire manquant"}), 400

        # Config SMTP depuis variables Render
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        # Création du mail
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        # Pièce jointe si présente
        if file:
            part = MIMEApplication(file.read(), Name=file.filename)
            part["Content-Disposition"] = f'attachment; filename="{file.filename}"'
            msg.attach(part)

        # Envoi via SMTP
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return jsonify({"status": "success", "message": "Mail envoyé avec succès"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
