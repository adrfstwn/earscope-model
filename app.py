# Wawan
import os
import cv2
import yaml
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO
from config import Config
import requests
import datetime
from collections import Counter
from threading import Event
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

stop_event = Event()
# Global variables to store recording data
recording_data = {
    "raw_path": None,
    "bbox_path": None,
    "diagnosis": None
}

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = app.config['APP_KEY']

if not app.secret_key:
    raise ValueError("APP_KEY is not set! Please define it in your .env file.")

# Load labels and colors from YAML file
with open('model-earscope/data.yml', 'r') as f:
    data = yaml.safe_load(f)
    labels = data['labels']
    colors = data['colors']


class Detection:
    def __init__(self):
        # Load the YOLO model
        self.model = YOLO(r"model-earscope/best.pt")

    def predict(self, img, classes=[], conf=0.5):
        if classes:
            results = self.model.predict(img, classes=classes, conf=conf)
        else:
            results = self.model.predict(img, conf=conf)
        return results

    def predict_and_detect(self, img, classes=[], conf=0.5, rectangle_thickness=2, text_thickness=1):
        results = self.predict(img, classes, conf=conf)
        for result in results:
            for box in result.boxes:
                # Get the class and color
                class_id = int(box.cls[0])
                color = colors.get(class_id, [255, 255, 255])  # Default to white if class not found

                # Draw bounding box with the assigned color
                cv2.rectangle(img, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
                              (int(box.xyxy[0][2]), int(box.xyxy[0][3])), color, rectangle_thickness)

                # Draw label text
                label = labels.get(class_id, "Unknown")
                cv2.putText(img, f"{label}",
                            (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                            cv2.FONT_HERSHEY_PLAIN, 1, color, text_thickness)

        return img, results

    def detect_from_image(self, image):
        result_img, _ = self.predict_and_detect(image, classes=[], conf=0.5)
        return result_img


detection = Detection()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_video')
def process_video():
    global recording_data
    # Reset recording data
    recording_data = {
        "raw_path": None,
        "bbox_path": None,
        "diagnosis": None
    }
    stop_event.clear()  # Reset the stop event
    logger.info("Starting video processing and recording")
    return Response(record_and_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    logger.info("Received request to stop recording")
    stop_event.set()  # Signal to stop the recording
    
    # Wait a moment for recording to finish and data to be set
    def delayed_api_send():
        # Small delay to ensure recording is complete
        time.sleep(1)
        if recording_data["raw_path"] and recording_data["bbox_path"] and recording_data["diagnosis"]:
            success = send_to_api(
                recording_data["raw_path"], 
                recording_data["bbox_path"], 
                recording_data["diagnosis"]
            )
            return success
        else:
            logger.error("Recording data incomplete. Cannot send to API.")
            return False
    
    # Start the API sending in a separate thread
    api_thread = threading.Thread(target=delayed_api_send)
    api_thread.start()
    
    return jsonify({'status': 'stopping', 'message': 'Recording stopped, processing data'})


def record_and_stream():
    global recording_data
    logger.info("Starting recording and streaming process")

    cap = cv2.VideoCapture(0)
    width, height = 512, 512

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"videos/{timestamp}"
    os.makedirs(folder, exist_ok=True)

    raw_path = os.path.join(folder, f"raw_{timestamp}.mp4")
    bbox_path = os.path.join(folder, f"bbox_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    raw_writer = cv2.VideoWriter(raw_path, fourcc, 20.0, (width, height))
    bbox_writer = cv2.VideoWriter(bbox_path, fourcc, 20.0, (width, height))

    detected_classes = []

    try:
        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                break

            frame = cv2.resize(frame, (width, height))
            raw_writer.write(frame)

            result_img, results = detection.predict_and_detect(frame.copy())

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    detected_classes.append(class_id)

            bbox_writer.write(result_img)

            ret, buffer = cv2.imencode('.jpg', result_img)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    except Exception as e:
        logger.error(f"Error during recording: {e}")
    finally:
        # Release resources
        logger.info("Releasing video resources")
        cap.release()
        raw_writer.release()
        bbox_writer.release()

        # Store diagnosis and paths for API sending
        diagnosis_id = Counter(detected_classes).most_common(1)[0][0] if detected_classes else -1
        diagnosis_label = labels.get(diagnosis_id, "Unknown")
        
        # Save the recording data for API sending
        recording_data["raw_path"] = raw_path
        recording_data["bbox_path"] = bbox_path
        recording_data["diagnosis"] = diagnosis_label
        
        logger.info(f"Recording complete. Diagnosis: {diagnosis_label}")


def send_to_api(raw_path, bbox_path, diagnosis):
    """Send recorded videos to API and return success status"""
    url = app.config['API_VIDEO_URL']

    logger.info(f"Sending data to API at {url}")
    logger.info(f"Raw Video: {raw_path}")
    logger.info(f"Processed Video: {bbox_path}")
    logger.info(f"Diagnosis: {diagnosis}")

    try:
        with open(raw_path, 'rb') as raw, open(bbox_path, 'rb') as bbox:
            files = {
                'raw_video': raw,
                'processed_video': bbox
            }

            data = {
                'hasil_diagnosis': diagnosis
            }

            response = requests.post(url, files=files, data=data)

        logger.info(f"API Response Status Code: {response.status_code}")

        try:
            response_data = response.json()
            logger.info(f"API JSON Response: {response_data}")
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.info(f"Raw Text Response: {response.text}")

        # Return True if successful (status code 2xx)
        return 201 <= response.status_code < 300
    
    except Exception as e:
        logger.error(f"Error sending to API: {e}")
        return False


if __name__ == '__main__':
    # Make sure to import time module at the top if not already there
    import time
    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'])