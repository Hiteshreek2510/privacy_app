import cv2
from ultralytics import YOLO
from PIL import Image
import piexif
import os


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

    # def face_detect(self):
    #     count = 0
    #     app_1 = FaceAnalysis(name='buffalo_l')
    #     app_1.prepare(ctx_id=0, det_size=(1280, 1280))
    #     image = cv2.imread(self.img)
    #     if image.shape[0] > 1000 or image.shape[1] > 1000:
    #         image = cv2.resize(image, (800, 800))
    #
    #     faces = app_1.get(image)
    #     for face in faces:
    #         count += 1
    #         x1, y1, x2, y2 = [int(v) for v in face.bbox]
    #         # self.blur_regions.append((x1, y1, x2 - x1, y2 - y1))
    #
    #     if count > 0:
    #         self.privacy += count * 10
    #         self.risk_factors.append('faces')
    #     else:
    #         print("no faces detected")
    #
    #     return self.privacy, self.risk_factors

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
