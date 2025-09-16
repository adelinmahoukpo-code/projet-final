from flask import Flask, request, send_from_directory, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import os
import csv

app = Flask(__name__)

# 📌 Route principale : sert index.html (ou renomme ton HTML corrigé en index.html)
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
    sujet        = request.form.get("subject", "Votre facture")
    companyName  = request.form.get("company_name", "")

    # Vérification email
    if not destinataire or "@" not in destinataire:
        return "ERROR: Adresse e-mail invalide."

    try:
        # Corps du message
        body = ""
        if messagePerso:
            body += f"<p><em>Message de l’agent :</em><br>{messagePerso}</p><hr>"
        body += """
        <p>Madame, Monsieur,</p>
        <p>La <strong>Direction Générale des Impôts</strong> vous informe que votre facture est désormais disponible. 
        Veuillez trouver ci-joint le document correspondant.</p>
        <p>Nous vous prions de bien vouloir en prendre connaissance dans les meilleurs délais.</p>
        <p>
        Cordialement,<br>
        <strong>Direction Générale des Impôts</strong><br>
        📞 Service Facturation : +229 45 45 12 12
        </p>
        """
        if companyName:
            body += f"<p><strong>Entreprise concernée :</strong> {companyName}</p>"
        if refFacture:
            sujet += f" — Réf: {refFacture}"

        # Création du mail
        msg = MIMEMultipart()
        expediteur = os.getenv("GMAIL_USERNAME")
        msg["From"] = f"{fromName} | {fromContact} <{expediteur}>"
        msg["To"] = destinataire
        msg["Subject"] = sujet
        msg.attach(MIMEText(body, "html"))

        # 📎 Gestion de la pièce jointe
        if "attachment" in request.files:
            file = request.files["attachment"]
            if file and file.filename:
                ctype, encoding = mimetypes.guess_type(file.filename)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                part = MIMEBase(maintype, subtype)
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{file.filename}"'
                )
                msg.attach(part)

        # Connexion SMTP Gmail
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv("GMAIL_USERNAME"), os.getenv("GMAIL_PASSWORD"))
        server.send_message(msg)
        server.quit()

        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 📌 Nouvelle route pour fournir la liste des entreprises en JSON
@app.route("/api/entreprises")
def entreprises():
    entreprises = []
    try:
        with open("entreprises_geocodes.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entreprises.append({
                    "Nom_Entreprise": row.get("Nom_Entreprise"),
                    "Adresse_Complete": row.get("Adresse_Complete"),
                    "Latitude": row.get("Latitude"),
                    "Longitude": row.get("Longitude")
                })
    except Exception as e:
        return jsonify({"error": str(e)})
    return jsonify(entreprises)

# 📌 Lancer le serveur
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
