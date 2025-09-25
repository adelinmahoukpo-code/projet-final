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
    try:
        # Support JSON ou form-data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        # Vérifications des variables d'environnement
        if not EMAIL or not PASSWORD:
            return jsonify({
                "status": "error", 
                "message": "Configuration email manquante. Vérifiez les variables d'environnement GMAIL_USERNAME et GMAIL_PASSWORD."
            }), 500

        destinataire = data.get("to_email")
        if not destinataire:
            return jsonify({"status": "error", "message": "Adresse email destinataire requise"}), 400

        messagePerso = data.get("message", "")
        refFacture   = data.get("invoice_ref", "")
        fromName     = data.get("from_name", "Service des Impôts")
        fromContact  = data.get("agent_contact", "")
        companyName  = data.get("company_name", "")
        sujet        = data.get("subject", "Facture Direction Générale des Impôts")

        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = destinataire
        msg["Subject"] = sujet

        # Corps du message amélioré
        corps = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #007bff; text-align: center;">Direction Générale des Impôts</h2>
                <h3 style="color: #28a745;">Facture - République du Bénin</h3>
                
                <p>Bonjour,</p>
                
                {f'<p><strong>Entreprise concernée :</strong> {companyName}</p>' if companyName else ''}
                {f'<p><strong>Référence facture :</strong> {refFacture}</p>' if refFacture else ''}
                
                <p>Veuillez trouver ci-joint votre facture émise par la Direction Générale des Impôts.</p>
                
                {f'<p><strong>Message :</strong> {messagePerso}</p>' if messagePerso else ''}
                
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                
                <p style="font-size: 0.9em; color: #666;">
                    <strong>Contact de l'agent :</strong> {fromName}<br>
                    {f'<strong>Téléphone :</strong> {fromContact}' if fromContact else ''}
                </p>
                
                <p style="font-size: 0.8em; color: #999; text-align: center; margin-top: 30px;">
                    Ce message a été envoyé automatiquement par le système de distribution des factures.<br>
                    Direction Générale des Impôts - République du Bénin
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corps, "html"))

        # Gestion des fichiers joints
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                # Vérifier la taille du fichier (max 10MB)
                file.seek(0, 2)  # Aller à la fin du fichier
                file_size = file.tell()
                file.seek(0)  # Revenir au début
                
                if file_size > 10 * 1024 * 1024:  # 10MB
                    return jsonify({"status": "error", "message": "Fichier trop volumineux (max 10MB)"}), 400
                
                # Vérifier l'extension
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    return jsonify({"status": "error", "message": "Type de fichier non autorisé. Utilisez: PDF, JPG, PNG"}), 400
                
                # Attacher le fichier
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {file.filename}'
                )
                msg.attach(part)

        # Envoi de l'email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, destinataire, msg.as_string())
        server.quit()
        
        return jsonify({
            "status": "success", 
            "message": f"Email envoyé avec succès à {destinataire}"
        })
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "status": "error", 
            "message": "Erreur d'authentification email. Vérifiez les identifiants Gmail."
        }), 401
    except smtplib.SMTPRecipientsRefused:
        return jsonify({
            "status": "error", 
            "message": "Adresse email destinataire invalide."
        }), 400
    except Exception as e:
        print(f"Erreur détaillée: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Erreur lors de l'envoi: {str(e)}"
        }), 500

# 📌 Route pour renvoyer la liste des entreprises
@app.route("/entreprises")
def get_entreprises():
    entreprises = []
    csv_path = os.path.join(os.path.dirname(__file__), "entreprises_geocodes.csv")
    
    # Essayer aussi le chemin public/
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "public", "entreprises_geocodes.csv")
    
    # Vérifie si le fichier existe
    if not os.path.exists(csv_path):
        return jsonify({"error": "Fichier CSV non trouvé", "path_checked": csv_path}), 404

    try:
        # Essayer différents encodages
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(csv_path, newline="", encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row.get('Nom_Entreprise') and row.get('Latitude') and row.get('Longitude'):
                            entreprises.append(row)
                break  # Si succès, sortir de la boucle
            except UnicodeDecodeError:
                continue  # Essayer l'encodage suivant
                
        if not entreprises:
            return jsonify({"error": "Aucune entreprise trouvée ou problème d'encodage"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la lecture: {str(e)}"}), 500

    return jsonify(entreprises)

# 📌 Route pour servir les fichiers statiques (CSS, CSV, etc.)
@app.route("/public/<path:filename>")
def serve_static(filename):
    return send_from_directory("public", filename)

if __name__ == "__main__":
    # Afficher les informations de configuration au démarrage
    print("=" * 50)
    print("🚀 Démarrage du serveur Flask")
    print(f"📧 Email configuré: {'✅' if EMAIL else '❌'} {EMAIL if EMAIL else 'Non configuré'}")
    print(f"🔑 Mot de passe configuré: {'✅' if PASSWORD else '❌'}")
    
    # Vérifier la présence du fichier CSV
    csv_path = os.path.join(os.path.dirname(__file__), "entreprises_geocodes.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "public", "entreprises_geocodes.csv")
    print(f"📊 Fichier CSV: {'✅' if os.path.exists(csv_path) else '❌'} {csv_path}")
    print("=" * 50)
    
    # Récupérer le port fourni par Render ou utiliser 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur: {e}")
        print("Tentative de redémarrage sur le port 5001...")
        try:
            app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
        except Exception as e2:
            print(f"Erreur critique: {e2}")
