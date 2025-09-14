from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os

app = Flask(__name__)
CORS(app)  # Autoriser l’accès depuis ton frontend Render

@app.route("/sendmail", methods=["POST"])
def send_mail():
    try:
        to_email = request.form.get("to_email")
        invoice_ref = request.form.get("invoice_ref", "")
        message = request.form.get("message", "")
        file = request.files.get("attachment")

        # ⚠️ configure ton compte SMTP
        sender_email = os.environ.get("SMTP_USER")
        sender_pass = os.environ.get("SMTP_PASS")

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = f"Facture {invoice_ref}"

        msg.attach(MIMEText(message, "plain"))

        if file:
            part = MIMEApplication(file.read(), Name=file.filename)
            part["Content-Disposition"] = f'attachment; filename="{file.filename}"'
            msg.attach(part)

        # Ex : Gmail SMTP (nécessite mot de passe d’application)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        return "SUCCESS"

    except Exception as e:
        return f"ERROR: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
