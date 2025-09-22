import google.generativeai as genai
from insightface.app import FaceAnalysis
import cv2
from ultralytics import YOLO
from PIL import Image
import piexif
from flask import Flask, request, render_template, redirect, url_for,jsonify,session
import os
from werkzeug.utils import secure_filename
import requests
import secrets

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
genai.configure(api_key="AIzaSyAhqeBYe7s-64i04iU47ydf8M-6V_gI9Uk")
model = genai.GenerativeModel("gemini-1.5-flash-latest")
app.secret_key = secrets.token_hex(16)
@app.route("/")
def home():
    return render_template("index.html")


@app.route('/privacyscore', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return "No image uploaded", 400

    image = request.files['image']
    if image.filename == '':
        return "No selected file", 400

    filename = secure_filename(image.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(filepath)

    score = privacyapp(filepath)
    privacy_score,_ = score.privacy_invade()
    privacy_score,_ = score.face_detect()
    privacy_score,_ = score.show_gps()
    _,risk_factor = score.privacy_invade()
    _,risk_factor = score.face_detect()
    _,risk_factor = score.show_gps()

    risk_level = ''
    if privacy_score < 40:
        risk_level = 'LOW'
    elif privacy_score < 80:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'HIGH'

    sanitized_path = score.blur_sensitive_regions()
    sanitized_filename = os.path.basename(sanitized_path)

    session['privacy_score'] = privacy_score
    session['risk_factors'] = risk_factor
    session['risk_level'] = risk_level
    session['sanitized_filename'] = sanitized_filename

    return render_template('privacyscore.html', image_filename=filename, score=privacy_score, risk_level=risk_level)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    privacy_score = session.get('privacy_score', 0)
    risk_level=session.get('risk_level','')
    risk_factors = session.get('risk_factors', [])
    chat_history = session.get('chat_history', [])

    if request.method == 'POST':
        user_message = request.form['user_query']

        prompt = f"""
        A user uploaded an image with a privacy score of {privacy_score}/100.
        and the risk level is {risk_level}
        The detected risks include: {', '.join(risk_factors)}.
        The user asked: "{user_message}"

        Please explain the privacy risks in simple terms and offer suggestions to reduce exposure.
        """

        try:
            response = model.generate_content(prompt)
            gemini_reply = response.text
        except Exception as e:
            gemini_reply = f"Error: {str(e)}"

        # Append to chat history
        chat_history.append({"user": user_message, "bot": gemini_reply})
        session['chat_history'] = chat_history

        return render_template('chatbot.html', score=privacy_score, chat_history=chat_history)

    return render_template('chatbot.html', score=privacy_score, chat_history=chat_history)

@app.route('/preview')
def preview_blurred():
    sanitized_filename = session.get('sanitized_filename', 'blurred.jpg')
    return render_template('blur.html', image_filename=sanitized_filename)

class privacyapp:
    def __init__(self, img):
        self.img = img
        self.privacy = 0
        self.risk_factors = []
        self.blur_regions = []  # Store regions to blur

    def privacy_invade(self):
        model = YOLO('best.pt')
        result = model(self.img, conf=0.4)
        skip_class_id = 7
        filtered_boxes = [box for box in result[0].boxes if int(box.cls.item()) != skip_class_id]
        result[0].boxes = filtered_boxes

        class_id = [0, 1, 2, 3, 4, 5, 6]
        for box in result[0].boxes:
            cls = int(box.cls.item())
            if cls in class_id:
                self.privacy += 20
                self.risk_factors.append(model.names[cls])
                if model.names[cls]=='with_id_card':
                    continue
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                self.blur_regions.append((x1, y1, x2 - x1, y2 - y1))

        return self.privacy, self.risk_factors

    def face_detect(self):
        count = 0
        app_1 = FaceAnalysis(name='buffalo_l')
        app_1.prepare(ctx_id=0, det_size=(1280, 1280))
        image = cv2.imread(self.img)
        if image.shape[0] > 1000 or image.shape[1] > 1000:
            image = cv2.resize(image, (800, 800))

        faces = app_1.get(image)
        for face in faces:
            count += 1
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            # self.blur_regions.append((x1, y1, x2 - x1, y2 - y1))

        if count > 0:
            self.privacy += count * 10
            self.risk_factors.append('faces')
        else:
            print("no faces detected")

        return self.privacy, self.risk_factors

    def show_gps(self):
        exif_dict = piexif.load(self.img)
        gps_data = exif_dict.get("GPS", {})
        if gps_data:
            self.privacy += 20
            self.risk_factors.append('exif_data')
            print('gps data yes')
        return self.privacy, self.risk_factors

    def blur_sensitive_regions(self, output_path='static/sanitized/blurred.jpg'):
        image = cv2.imread(self.img)
        for (x, y, w, h) in self.blur_regions:
            roi = image[y:y+h, x:x+w]
            blurred_roi = cv2.GaussianBlur(roi, (101, 101), 0)
            image[y:y+h, x:x+w] = blurred_roi

        temp_path = "temp_blur.jpg"
        cv2.imwrite(temp_path, image)

        pil_img = Image.open(temp_path)
        pil_img.save(output_path, "jpeg", exif=piexif.dump({}))
        os.remove(temp_path)

        print(f"Sanitized image saved at: {output_path}")
        return output_path

if __name__ == "__main__":
    app.run(debug=True)
