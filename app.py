import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)  # autorise ton frontend à appeler l’API

@app.route('/sendmail', methods=['POST'])
def sendmail():
    try:
        # Récupération des champs envoyés par le frontend
        to_email = request.form['to']
        subject = request.form['subject']
        message = request.form['message']
        file = request.files.get('file')  # fichier optionnel

        # Configuration SMTP (à mettre dans Render → Environment Variables)
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        # Vérification
        if not smtp_user or not smtp_pass:
            return jsonify({"success": False, "error": "SMTP_USER ou SMTP_PASS manquant"}), 500

        # Création de l’email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, "plain"))

        # Ajout de la pièce jointe
        if file:
            part = MIMEApplication(file.read(), Name=file.filename)
            part['Content-Disposition'] = f'attachment; filename="{file.filename}"'
            msg.attach(part)

        # Connexion et envoi
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()

        return jsonify({"success": True, "message": "Email envoyé avec succès"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    # Render donne automatiquement un port dans la variable PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
