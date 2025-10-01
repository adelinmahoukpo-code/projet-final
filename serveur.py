from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import csv
import re
from dotenv import load_dotenv
import json
from datetime import datetime

# Charger les variables d'environnement depuis .env (local)
load_dotenv()

EMAIL = os.getenv("GMAIL_USERNAME")
PASSWORD = os.getenv("GMAIL_PASSWORD")

app = Flask(__name__)
CORS(app)  # Autoriser toutes les origines

# 📌 Route principale : sert index.html
@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")


# 📌 Route pour envoyer un mail
@app.route("/sendmail", methods=["POST"])
def sendmail():
    try:
        data = request.get_json() if request.is_json else request.form

        if not EMAIL or not PASSWORD:
            return jsonify({
                "status": "error",
                "message": "Configuration email manquante. Vérifiez GMAIL_USERNAME et GMAIL_PASSWORD."
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

        # Message "multipart/mixed" avec une partie alternative texte+HTML
        msg = MIMEMultipart("mixed")
        msg["From"] = EMAIL
        msg["To"] = destinataire
        msg["Subject"] = sujet

        # Ces variables seront utilisées après le traitement des pièces jointes
        attached_filename = None
        preview_cid = None

        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                original_filename = file.filename
                print(f"[DEBUG] ============================================")
                print(f"[DEBUG] FICHIER REÇU: '{original_filename}'")
                print(f"[DEBUG] Type de fichier Flask: {type(file)}")
                
                # Obtenir la taille du fichier
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                print(f"[DEBUG] Taille du fichier: {file_size} bytes")

                if file_size > 10 * 1024 * 1024:
                    return jsonify({"status": "error", "message": "Fichier trop volumineux (max 10MB)"}), 400

                # Vérification de l'extension
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                file_ext = os.path.splitext(original_filename)[1].lower()
                print(f"[DEBUG] Extension détectée: '{file_ext}'")
                
                if file_ext not in allowed_extensions:
                    return jsonify({"status": "error", "message": "Type de fichier non autorisé. Utilisez: PDF, JPG, PNG"}), 400

                # Lire le contenu du fichier
                file_content = file.read()
                print(f"[DEBUG] Contenu lu: {len(file_content)} bytes")
                print(f"[DEBUG] Premières bytes: {file_content[:20].hex() if len(file_content) >= 20 else 'Fichier trop petit'}")
                
                # Déterminer le type MIME en fonction de l'extension ET du contenu
                if file_ext == '.pdf':
                    # Vérifier que c'est vraiment un PDF
                    if file_content.startswith(b'%PDF'):
                        maintype, subtype = 'application', 'pdf'
                        print(f"[DEBUG] PDF validé par signature")
                    else:
                        print(f"[WARNING] Fichier .pdf sans signature PDF valide!")
                        maintype, subtype = 'application', 'pdf'  # On fait confiance à l'extension
                elif file_ext in ['.jpg', '.jpeg']:
                    maintype, subtype = 'image', 'jpeg'
                elif file_ext == '.png':
                    maintype, subtype = 'image', 'png'
                else:
                    maintype, subtype = 'application', 'octet-stream'
                
                print(f"[DEBUG] Type MIME déterminé: {maintype}/{subtype}")
                
                # Nettoyer et normaliser le nom de fichier, avec un fallback ASCII
                import re, unicodedata
                # Conserver Unicode mais retirer les caractères problématiques
                safe_filename = re.sub(r'[^\w\-\.\s]', '_', original_filename or '').strip()
                safe_filename = re.sub(r'\s+', ' ', safe_filename)
                if not os.path.splitext(safe_filename)[1] and file_ext:
                    safe_filename += file_ext
                # Fallback ASCII strict pour compatibilité maximale
                ascii_filename = unicodedata.normalize('NFKD', safe_filename).encode('ascii', 'ignore').decode('ascii')
                ascii_filename = re.sub(r'[^A-Za-z0-9._-]', '_', ascii_filename)
                if not ascii_filename:
                    ascii_filename = f"facture{file_ext or '.pdf'}"
                print(f"[DEBUG] Nom de fichier nettoyé: '{original_filename}' -> '{safe_filename}' | ASCII: '{ascii_filename}'")
                
                # Créer la pièce jointe avec une méthode différente pour PDF
                if file_ext == '.pdf':
                    print(f"[DEBUG] Traitement spécial PDF")
                    # Méthode spécifique pour PDF
                    from email.mime.application import MIMEApplication
                    
                    part = MIMEApplication(file_content, _subtype='pdf')
                    # Encodage base64 requis pour une compatibilité maximale avec les clients mail
                    encoders.encode_base64(part)
                    # Assurer des métadonnées complètes pour activer l'aperçu/telechargement sur un maximum de clients
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=ascii_filename
                    )
                    # Assurer aussi filename* (RFC2231) et name/name*
                    try:
                        from email.utils import encode_rfc2231
                        part.set_param('filename*', encode_rfc2231(safe_filename, 'utf-8'), header='Content-Disposition')
                        part.set_param('name', ascii_filename, header='Content-Type')
                        part.set_param('name*', encode_rfc2231(safe_filename, 'utf-8'), header='Content-Type')
                    except Exception:
                        pass
                    # Headers supplémentaires pour PDF
                    part.add_header('Content-Description', f'PDF Document: {safe_filename}')

                    # Tenter de générer un aperçu image du 1er feuillet (si PyMuPDF est disponible)
                    try:
                        import uuid as _uuid
                        from email.mime.image import MIMEImage
                        try:
                            import fitz  # PyMuPDF
                            doc = fitz.open(stream=file_content, filetype='pdf')
                            page = doc.load_page(0)
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                            img_bytes = pix.tobytes('png')
                            preview_cid = f"pdfpreview-{_uuid.uuid4()}@local"
                            img_part = MIMEImage(img_bytes, _subtype='png')
                            img_part.add_header('Content-ID', f'<{preview_cid}>')
                            img_part.add_header('Content-Disposition', 'inline', filename=f'preview_{safe_filename}.png')
                            img_part.add_header('Content-Description', f'Preview of {safe_filename}')
                            msg.attach(img_part)
                            print("[DEBUG] Aperçu PNG du PDF généré et inclus inline.")
                        except Exception as pe:
                            print(f"[INFO] Aperçu non généré (PyMuPDF indisponible ou erreur): {pe}")
                    except Exception as ee:
                        print(f"[INFO] Impossible de joindre l'aperçu: {ee}")

                    attached_filename = safe_filename or ascii_filename
                else:
                    print(f"[DEBUG] Traitement standard pour image")
                    # Méthode standard pour images
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(file_content)
                    encoders.encode_base64(part)
                    # Définir filename ASCII + variantes RFC2231
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=ascii_filename
                    )
                    try:
                        from email.utils import encode_rfc2231
                        part.set_param('filename*', encode_rfc2231(safe_filename, 'utf-8'), header='Content-Disposition')
                        part.set_param('name', ascii_filename, header='Content-Type')
                        part.set_param('name*', encode_rfc2231(safe_filename, 'utf-8'), header='Content-Type')
                    except Exception:
                        pass
                
                # Joindre la pièce jointe (sans Content-ID pour éviter un affichage inline non désiré)
                msg.attach(part)
                print(f"[DEBUG] Pièce jointe ajoutée avec succès!")
                print(f"[DEBUG] Headers de la pièce jointe:")
                for header_name, header_value in part.items():
                    print(f"[DEBUG]   {header_name}: {header_value}")
                print(f"[DEBUG] ===========================================")

        # Construire le corps du message après traitement des pièces jointes (pour insérer l'aperçu si présent)
        text_lines = [
            "Direction Générale des Impôts - Facture",
            "",
            f"Entreprise concernée : {companyName}" if companyName else "",
            f"Référence facture : {refFacture}" if refFacture else "",
            "",
            "Veuillez trouver ci-joint votre facture.",
            "",
            f"Contact de l'agent : {fromName}",
            f"Téléphone : {fromContact}" if fromContact else "",
        ]
        text_body = "\n".join([l for l in text_lines if l != ""])

        preview_section = f'''
                <div style="margin:16px 0;">
                    <p style="margin:0 0 8px 0; color:#555;">Aperçu de la facture (PDF) :</p>
                    <img src="cid:{preview_cid}" alt="Aperçu PDF" style="max-width:100%; border:1px solid #eee; border-radius:6px;">
                    <div style="font-size:0.9em; color:#666; margin-top:6px;">{attached_filename or ''}</div>
                </div>
        ''' if preview_cid else ''

        corps = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style=\"color: #007bff; text-align: center;\">Direction Générale des Impôts</h2>
                <h3 style=\"color: #28a745;\">Facture - République du Bénin</h3>
                
                <p>Bonjour,</p>
                
                {f'<p><strong>Entreprise concernée :</strong> {companyName}</p>' if companyName else ''}
                {f'<p><strong>Référence facture :</strong> {refFacture}</p>' if refFacture else ''}
                
                <p>Veuillez trouver ci-joint votre facture émise par la Direction Générale des Impôts.</p>
                
                {f'<p><strong>Message :</strong> {messagePerso}</p>' if messagePerso else ''}

                {preview_section}
                
                <hr style=\"margin: 20px 0; border: none; border-top: 1px solid #eee;\">
                
                <p style=\"font-size: 0.9em; color: #666;\">
                    <strong>Contact de l'agent :</strong> {fromName}<br>
                    {f'<strong>Téléphone :</strong> {fromContact}' if fromContact else ''}
                </p>
                
                <p style=\"font-size: 0.8em; color: #999; text-align: center; margin-top: 30px;\">
                    Ce message a été envoyé automatiquement par le système de distribution des factures.<br>
                    Direction Générale des Impôts - République du Bénin
                </p>
            </div>
        </body>
        </html>
        """

        # Ajouter la partie alternative (texte + HTML)
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text_body, "plain", "utf-8"))
        alt.attach(MIMEText(corps, "html", "utf-8"))
        msg.attach(alt)

        try:
            print(f"[INFO] Tentative d'envoi d'email à {destinataire}")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            print(f"[INFO] Connexion SMTP établie, tentative de login...")
            server.login(EMAIL, PASSWORD)
            print(f"[INFO] Login SMTP réussi, envoi du message...")
            server.sendmail(EMAIL, destinataire, msg.as_string())
            server.quit()
            print(f"[SUCCESS] Email envoyé avec succès à {destinataire}")
        except smtplib.SMTPAuthenticationError as e:
            print(f"[ERREUR] Authentification SMTP échouée: {e}")
            return jsonify({"status": "error", "message": "Identifiants Gmail invalides. Vérifiez le mot de passe d'application Gmail ou réactivez l'accès aux applications moins sécurisées."}), 401
        except smtplib.SMTPRecipientsRefused as e:
            print(f"[ERREUR] Destinataire refusé: {e}")
            return jsonify({"status": "error", "message": "Adresse email destinataire invalide ou refusée."}), 400
        except smtplib.SMTPException as e:
            print(f"[ERREUR] Exception SMTP: {e}")
            return jsonify({"status": "error", "message": f"Problème SMTP lors de l'envoi: {str(e)}"}), 500
        except Exception as e:
            print(f"[ERREUR] Erreur générale lors de l'envoi: {e}")
            return jsonify({"status": "error", "message": f"Erreur lors de l'envoi: {str(e)}"}), 500

        return jsonify({"status": "success", "message": f"Email envoyé avec succès à {destinataire}"})

    except Exception as e:
        print(f"Erreur générale: {e}")
        return jsonify({"status": "error", "message": f"Erreur serveur: {e}"}), 500


# 📌 Route pour renvoyer la liste des entreprises
@app.route("/entreprises")
def get_entreprises():
    entreprises = []
    csv_path = os.path.join(os.path.dirname(__file__), "entreprises_geocodes.csv")

    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "public", "entreprises_geocodes.csv")

    if not os.path.exists(csv_path):
        return jsonify({"error": "Fichier CSV non trouvé", "path_checked": csv_path}), 404

    try:
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(csv_path, newline="", encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row.get('Nom_Entreprise') and row.get('Latitude') and row.get('Longitude'):
                            entreprises.append(row)
                break
            except UnicodeDecodeError:
                continue
        if not entreprises:
            return jsonify({"error": "Aucune entreprise trouvée ou problème d'encodage"}), 404
    except Exception as e:
        return jsonify({"error": f"Erreur lecture CSV: {str(e)}"}), 500

    return jsonify(entreprises)


# 📌 Nouvelles routes pour la synchronisation en temps réel
# Route pour soumettre un rapport de livraison
@app.route("/submit-report", methods=["POST"])
def submit_report():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Données manquantes"}), 400

        # Ajouter un timestamp si non présent
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        # Sauvegarder le rapport dans un fichier
        reports_file = os.path.join(os.path.dirname(__file__), "delivery_reports.json")
        
        # Lire les rapports existants
        reports = []
        if os.path.exists(reports_file):
            try:
                with open(reports_file, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                reports = []

        # Ajouter le nouveau rapport
        reports.append(data)

        # Sauvegarder tous les rapports
        with open(reports_file, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "success", "message": "Rapport soumis avec succès"}), 200
    except Exception as e:
        print(f"Erreur lors de la soumission du rapport: {e}")
        return jsonify({"status": "error", "message": f"Erreur serveur: {e}"}), 500


# Route pour récupérer tous les rapports de livraison
@app.route("/reports", methods=["GET"])
def get_reports():
    try:
        reports_file = os.path.join(os.path.dirname(__file__), "delivery_reports.json")
        
        if not os.path.exists(reports_file):
            return jsonify([]), 200

        with open(reports_file, 'r', encoding='utf-8') as f:
            reports = json.load(f)
        
        return jsonify(reports), 200
    except Exception as e:
        print(f"Erreur lors de la récupération des rapports: {e}")
        return jsonify({"error": f"Erreur serveur: {e}"}), 500


# Route pour servir les fichiers statiques
@app.route("/public/<path:filename>")
def serve_static(filename):
    return send_from_directory("public", filename)


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Démarrage du serveur Flask pour l'envoi de factures")
    print(f"📧 Email configuré: {'✅' if EMAIL else '❌'} {EMAIL if EMAIL else 'Non configuré'}")
    print(f"🔑 Mot de passe configuré: {'✅' if PASSWORD else '❌'}")
    
    if not EMAIL or not PASSWORD:
        print("⚠️  ATTENTION: Configuration email manquante!")
        print("   Vérifiez le fichier .env avec GMAIL_USERNAME et GMAIL_PASSWORD")
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Serveur démarré sur http://localhost:{port}")
    print(f"📬 Route d'envoi: http://localhost:{port}/sendmail")
    print("=" * 50)
    
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Erreur lors du démarrage du serveur: {e}")
        input("Appuyez sur Entrée pour continuer...")
