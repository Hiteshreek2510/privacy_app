import os
import secrets
import tempfile
from PIL import Image
from flask import Flask, request, render_template, session, send_file, after_this_request
from utils.process import privacyapp

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = secrets.token_hex(16)

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/privacyscore', methods=['GET', 'POST'])
def upload_image():
    if 'image' not in request.files:
        return "No image uploaded", 400

    image = request.files['image']
    if image.filename == '':
        return "No selected file", 400

    # Delete previous image if it exists
    old_path = session.get('image_path')
    if old_path and os.path.exists(old_path):
        os.remove(old_path)
        print(f"Deleted previous image: {old_path}")

    # Resize and save new image
    img = Image.open(image.stream).convert("RGB")
    img = img.resize((640, 640))
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img.save(temp.name, format='JPEG', quality=85)
    temp_path = temp.name
    temp.close()

    # Run privacy scoring
    score = privacyapp(temp_path)
    privacy_score, _ = score.privacy_invade()
    privacy_score, _ = score.show_gps()
    _, risk_factor = score.privacy_invade()
    _, risk_factor = score.show_gps()

    privacy_score = min(privacy_score, 100)

    if privacy_score < 40:
        risk_level = 'LOW'
    elif privacy_score < 80:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'HIGH'

    session['privacy_score'] = privacy_score
    session['risk_factors'] = risk_factor
    session['risk_level'] = risk_level
    session['image_path'] = temp_path

    return render_template('privacyscore.html', score=privacy_score, risk_level=risk_level)

@app.route('/uploaded')
def serve_uploaded_image():
    image_path = session.get('image_path')
    if not image_path or not os.path.exists(image_path):
        return "No image to display", 404
    return send_file(image_path, mimetype='image/jpeg')

@app.route('/explanation', methods=['GET'])
def explanation():
    privacy_score = session.get('privacy_score', 0)
    risk_level = session.get('risk_level', "")
    risk_factors = session.get('risk_factors', [])

    if privacy_score == 0:
        explanation_text = "Your image is completely safe. No privacy risks were detected, so you can share it confidently."
    else:
        explanation_text = f"""
        Based on our analysis, your image has a privacy score of {privacy_score}/100, indicating a {risk_level.lower()} risk level.
        The following privacy risks were detected:
        {chr(10).join(f"- {factor}" for factor in risk_factors)}
        """

    return render_template('explain.html', explanation=explanation_text.strip(), risk_level=risk_level.lower())

@app.route('/blur_image')
def blur_image():
    return render_template('blur.html')

@app.route('/preview', methods=['GET'])
def preview():
    image_path = session.get('image_path')
    if not image_path or not os.path.exists(image_path):
        return "No image available", 400

    scanner = privacyapp(image_path)
    scanner.privacy_invade()
    scanner.show_gps()
    sanitized = scanner.blur_sensitive_regions()

    @after_this_request
    def cleanup(response):
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Deleted original image after preview: {image_path}")
        return response

    if sanitized and os.path.exists(sanitized):
        return send_file(sanitized, mimetype='image/jpeg')
    else:
        return "No blurred image available", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
