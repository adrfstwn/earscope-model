import os
import cv2
import yaml
from flask import Flask, request, render_template, Response, jsonify, abort
from ultralytics import YOLO
from config import Config
import requests
import datetime
from collections import Counter
from threading import Event
import logging
import threading
import queue
import socket
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Global variables 

network_available = False
stop_event = Event()
send_queue = queue.Queue()

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
# with open('model-earscope/data.yml', 'r') as f:
#     data = yaml.safe_load(f)
#     labels = data['labels']
#     colors = data['colors']
with open('model-earscope/data2.yml', 'r') as f:
    data = yaml.safe_load(f)
    labels = data['labels']
    colors = data['colors']

def check_internet(host="8.8.8.8", port=53, timeout=3):
    """
    Cek koneksi internet dengan mencoba connect ke DNS Google.
    Return True jika berhasil, False kalau tidak.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False

def network_monitor():
    global network_available
    while True:
        connected = check_internet()
        if connected != network_available:
            network_available = connected
            logger.info(f"Network status changed: {'Available' if connected else 'Not available'}")
        time.sleep(10)  # cek tiap 10 detik

# Start thread network monitor saat app start
threading.Thread(target=network_monitor, daemon=True).start()

class Detection:
    def __init__(self):
        # Load the YOLO model
        # self.model = YOLO(r"model-earscope/best.pt")
        self.model = YOLO(r"model-earscope/best2.pt")

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
    if not network_available:
        logger.warning("Tidak bisa mulai recording: jaringan tidak tersedia")
        return jsonify({'status': 'error', 'message': 'Tidak ada koneksi internet. Coba lagi nanti.'}), 503
    global recording_data
    # Reset recording data
    recording_data = {
        "raw_path": None,
        "bbox_path": None,
        "diagnosis": None
    }
    stop_event.clear()
    logger.info("Starting video processing and recording")
    return Response(record_and_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    if not network_available:
        logger.warning("Tidak bisa stop recording: jaringan tidak tersedia")
        return jsonify({'status': 'error', 'message': 'Tidak ada koneksi internet. Stop recording tidak tersedia.'}), 503
    
    logger.info("Received request to stop recording")
    stop_event.set()  # Hanya set event stop, biar record_and_stream berhenti

    return jsonify({'status': 'stopping', 'message': 'Recording stopped, processing data'})

# Thread worker untuk kirim data ke API secara async
def api_sender_worker():
    while True:
        record_data = send_queue.get()  # Tunggu data rekaman masuk queue
        try:
            success = send_to_api(record_data["raw_path"], record_data["bbox_path"], record_data["diagnosis"])
            logger.info(f"Send to API finished with success={success}")
        except Exception as e:
            logger.error(f"Exception in sending to API: {e}")
        send_queue.task_done()

# Jalankan worker thread sekali saat app mulai
threading.Thread(target=api_sender_worker, daemon=True).start()

def record_and_stream():
    global recording_data
    logger.info("Starting recording and streaming process")

    cap = cv2.VideoCapture(0)
    width, height = 1280, 720

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"videos/{timestamp}"
    os.makedirs(folder, exist_ok=True)

    raw_path = os.path.join(folder, f"raw_{timestamp}.mp4")
    bbox_path = os.path.join(folder, f"bbox_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    raw_writer = cv2.VideoWriter(raw_path, fourcc, 20.0, (width, height))

    frames = []

    try:
        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                break

            frame = cv2.resize(frame, (width, height))
            raw_writer.write(frame)
            frames.append(frame)

            # Tampilkan frame mentah saja (tanpa bounding box)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    except Exception as e:
        logger.error(f"Error during recording: {e}")
    finally:
        logger.info("Releasing video resources")
        cap.release()
        raw_writer.release()

        # Proses deteksi setelah selesai merekam
        logger.info("Processing detection on recorded frames")
        bbox_writer = cv2.VideoWriter(bbox_path, fourcc, 20.0, (width, height))
        detected_classes = []

        for frame in frames:
            # result_img, results = detection.predict_and_detect(frame.copy())
            resized_frame = cv2.resize(frame.copy(), (640, 640))  # untuk input ke model
            result_img, results = detection.predict_and_detect(resized_frame)

            result_img = cv2.resize(result_img, (1280, 720))

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    detected_classes.append(class_id)
            bbox_writer.write(result_img)

        bbox_writer.release()

        diagnosis_id = Counter(detected_classes).most_common(1)[0][0] if detected_classes else -1
        diagnosis_label = labels.get(diagnosis_id, "Unknown")

        record_data = {
            "raw_path": raw_path,
            "bbox_path": bbox_path,
            "diagnosis": diagnosis_label
        }
        send_queue.put(record_data)
        logger.info("Recording data enqueued for sending to API")

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