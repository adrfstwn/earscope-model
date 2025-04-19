# REST API

# import os
# import cv2
# import yaml
# from flask import Flask, render_template, Response, jsonify, request
# from ultralytics import YOLO
# from config import Config
# import requests
# import datetime
# from collections import Counter
# from threading import Event
# import threading
# import logging
# import numpy as np
# import base64
# import time

# # Configure logging
# logging.basicConfig(level=logging.INFO, 
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# stop_event = Event()
# # Global variables to store recording data
# recording_data = {
#     "raw_path": None,
#     "bbox_path": None,
#     "diagnosis": None
# }

# app = Flask(__name__)
# app.config.from_object(Config)

# app.secret_key = app.config['APP_KEY']

# if not app.secret_key:
#     raise ValueError("APP_KEY is not set! Please define it in your .env file.")

# # Load labels and colors from YAML file
# with open('model-earscope/data.yml', 'r') as f:
#     data = yaml.safe_load(f)
#     labels = data['labels']
#     colors = data['colors']


# class Detection:
#     def __init__(self):
#         # Load the YOLO model
#         self.model = YOLO(r"model-earscope/best.pt")

#     def predict(self, img, classes=[], conf=0.5):
#         if classes:
#             results = self.model.predict(img, classes=classes, conf=conf)
#         else:
#             results = self.model.predict(img, conf=conf)
#         return results

#     def predict_and_detect(self, img, classes=[], conf=0.5, rectangle_thickness=2, text_thickness=1):
#         results = self.predict(img, classes, conf=conf)
#         for result in results:
#             for box in result.boxes:
#                 # Get the class and color
#                 class_id = int(box.cls[0])
#                 color = colors.get(class_id, [255, 255, 255])  # Default to white if class not found

#                 # Draw bounding box with the assigned color
#                 cv2.rectangle(img, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
#                               (int(box.xyxy[0][2]), int(box.xyxy[0][3])), color, rectangle_thickness)

#                 # Draw label text
#                 label = labels.get(class_id, "Unknown")
#                 cv2.putText(img, f"{label}",
#                             (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
#                             cv2.FONT_HERSHEY_PLAIN, 1, color, text_thickness)

#         return img, results

#     def detect_from_image(self, image):
#         result_img, _ = self.predict_and_detect(image, classes=[], conf=0.5)
#         return result_img


# detection = Detection()

# @app.route('/')
# def index():
#     return render_template('index.html')

# # Variabel global untuk menyimpan frames yang dikirim dari browser
# browser_frames = []
# browser_frame_lock = threading.Lock()

# @app.route('/upload_frame', methods=['POST'])
# def upload_frame():
#     try:
#         # Ambil frame dari data POST
#         data = request.json
#         frame_data = data.get('frame', '')
        
#         # Decode base64 image
#         if frame_data.startswith('data:image/jpeg;base64,'):
#             frame_data = frame_data.replace('data:image/jpeg;base64,', '')
        
#         img_data = base64.b64decode(frame_data)
#         nparr = np.frombuffer(img_data, np.uint8)
#         frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
#         if frame is None:
#             logger.error("Failed to decode image from browser")
#             return jsonify({'status': 'error', 'message': 'Failed to decode image'}), 400
        
#         # Simpan frame untuk diproses
#         with browser_frame_lock:
#             browser_frames.append(frame)
        
#         return jsonify({'status': 'success'}), 200
    
#     except Exception as e:
#         logger.error(f"Error processing uploaded frame: {e}")
#         return jsonify({'status': 'error', 'message': str(e)}), 500

# @app.route('/process_video')
# def process_video():
#     global recording_data, browser_frames
#     # Reset recording data
#     recording_data = {
#         "raw_path": None,
#         "bbox_path": None,
#         "diagnosis": None
#     }
#     with browser_frame_lock:
#         browser_frames = []  # Reset frames buffer
    
#     stop_event.clear()  # Reset the stop event
#     logger.info("Starting video processing and streaming")
#     return Response(process_browser_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/stop_recording', methods=['POST'])
# def stop_recording():
#     logger.info("Received request to stop recording")
#     stop_event.set()  # Signal to stop the recording
    
#     # Wait a moment for recording to finish and data to be set
#     def delayed_api_send():
#         # Small delay to ensure recording is complete
#         time.sleep(1)
#         if recording_data["raw_path"] and recording_data["bbox_path"] and recording_data["diagnosis"]:
#             success = send_to_api(
#                 recording_data["raw_path"], 
#                 recording_data["bbox_path"], 
#                 recording_data["diagnosis"]
#             )
#             return success
#         else:
#             logger.error("Recording data incomplete. Cannot send to API.")
#             return False
    
#     # Start the API sending in a separate thread
#     api_thread = threading.Thread(target=delayed_api_send)
#     api_thread.start()
    
#     return jsonify({'status': 'stopping', 'message': 'Recording stopped, processing data'})

# def process_browser_stream():
#     global recording_data, browser_frames
#     logger.info("Starting processing of browser stream")

#     width, height = 512, 512
#     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#     folder = f"videos/{timestamp}"
#     os.makedirs(folder, exist_ok=True)

#     raw_path = os.path.join(folder, f"raw_{timestamp}.mp4")
#     bbox_path = os.path.join(folder, f"bbox_{timestamp}.mp4")

#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     raw_writer = cv2.VideoWriter(raw_path, fourcc, 20.0, (width, height))
#     bbox_writer = cv2.VideoWriter(bbox_path, fourcc, 20.0, (width, height))

#     detected_classes = []
#     last_frame_time = time.time()
#     empty_frame_count = 0

#     try:
#         while not stop_event.is_set():
#             # Check if there are new frames from browser
#             frame = None
#             with browser_frame_lock:
#                 if browser_frames:
#                     frame = browser_frames.pop(0)
            
#             if frame is not None:
#                 # Reset empty frame counter when we get a frame
#                 empty_frame_count = 0
#                 last_frame_time = time.time()
                
#                 # Resize frame to match expected dimensions
#                 frame = cv2.resize(frame, (width, height))
#                 raw_writer.write(frame)

#                 # Process frame with detection model
#                 result_img, results = detection.predict_and_detect(frame.copy())

#                 for result in results:
#                     for box in result.boxes:
#                         class_id = int(box.cls[0])
#                         detected_classes.append(class_id)

#                 bbox_writer.write(result_img)

#                 # Send processed frame back to browser
#                 ret, buffer = cv2.imencode('.jpg', result_img)
#                 frame_bytes = buffer.tobytes()
#                 yield (b'--frame\r\n'
#                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
#             else:
#                 # No new frames, check if we've been waiting too long
#                 if time.time() - last_frame_time > 5:  # 5 seconds without frames
#                     empty_frame_count += 1
#                     if empty_frame_count > 10:  # After several checks
#                         logger.warning("No frames received for extended period, stopping stream")
#                         break
                
#                 # Sleep a bit to prevent CPU overuse when idle
#                 time.sleep(0.1)

#     except Exception as e:
#         logger.error(f"Error during browser stream processing: {e}")
#     finally:
#         # Release resources
#         logger.info("Releasing video resources")
#         raw_writer.release()
#         bbox_writer.release()

#         # Store diagnosis and paths for API sending
#         diagnosis_id = Counter(detected_classes).most_common(1)[0][0] if detected_classes else -1
#         diagnosis_label = labels.get(diagnosis_id, "Unknown")
        
#         # Save the recording data for API sending
#         recording_data["raw_path"] = raw_path
#         recording_data["bbox_path"] = bbox_path
#         recording_data["diagnosis"] = diagnosis_label
        
#         logger.info(f"Recording complete. Diagnosis: {diagnosis_label}")

# def send_to_api(raw_path, bbox_path, diagnosis):
#     """Send recorded videos to API and return success status"""
#     url = app.config['API_VIDEO_URL']

#     logger.info(f"Sending data to API at {url}")
#     logger.info(f"Raw Video: {raw_path}")
#     logger.info(f"Processed Video: {bbox_path}")
#     logger.info(f"Diagnosis: {diagnosis}")

#     try:
#         with open(raw_path, 'rb') as raw, open(bbox_path, 'rb') as bbox:
#             files = {
#                 'raw_video': raw,
#                 'processed_video': bbox
#             }

#             data = {
#                 'hasil_diagnosis': diagnosis
#             }

#             response = requests.post(url, files=files, data=data)

#         logger.info(f"API Response Status Code: {response.status_code}")

#         try:
#             response_data = response.json()
#             logger.info(f"API JSON Response: {response_data}")
#         except Exception as e:
#             logger.error(f"Failed to parse JSON response: {e}")
#             logger.info(f"Raw Text Response: {response.text}")

#         # Return True if successful (status code 2xx)
#         return 201 <= response.status_code < 300
    
#     except Exception as e:
#         logger.error(f"Error sending to API: {e}")
#         return False


# if __name__ == '__main__':
#     app.run(host=app.config['HOST'],
#             port=app.config['PORT'],
#             debug=app.config['DEBUG'])










# Websocket

import os
import cv2
import yaml
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit
from ultralytics import YOLO
from config import Config
import requests
import datetime
from collections import Counter
from threading import Event, Thread
import threading
import logging
import numpy as np
import base64
import time
import queue
import io

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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

app.secret_key = app.config['APP_KEY']

if not app.secret_key:
    raise ValueError("APP_KEY is not set! Please define it in your .env file.")

# Load labels and colors from YAML file
with open('model-earscope/data.yml', 'r') as f:
    data = yaml.safe_load(f)
    labels = data['labels']
    colors = data['colors']

# Frame processing queue dan worker threads
frame_queue = queue.Queue(maxsize=500)  # Perbesar queue untuk menghindari drop frame
MAX_WORKERS = 4  # Jumlah worker thread
processed_frames = {}  # Dictionary untuk menyimpan frame yang sudah diproses
frame_counter = 0  # Counter untuk mengidentifikasi frame
frame_lock = threading.Lock()  # Lock untuk akses thread-safe ke frame counter
worker_threads = []  # Simpan referensi ke semua worker thread

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

# Worker thread untuk memproses frame dari queue
def process_frame_worker():
    global recording_data
    
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
        while not stop_event.is_set():
            try:
                # Ambil frame dari queue dengan timeout untuk cek stop_event secara periodik
                frame_data = frame_queue.get(timeout=0.5)
                frame_id = frame_data["id"]
                frame = frame_data["frame"]
                
                # Resize frame dan tulis ke raw video
                frame = cv2.resize(frame, (width, height))
                raw_writer.write(frame)
                
                # Proses dengan model deteksi
                result_img, results = detection.predict_and_detect(frame.copy())
                
                # Rekam hasil deteksi
                for result in results:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        detected_classes.append(class_id)
                
                # Tulis ke video terproses
                bbox_writer.write(result_img)
                
                # Konversi hasil ke JPEG untuk dikirim kembali ke browser
                ret, buffer = cv2.imencode('.jpg', result_img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                processed_frame = base64.b64encode(buffer).decode('utf-8')
                
                # Kirim hasilnya ke browser via WebSocket
                socketio.emit('processed_frame', {'frame': processed_frame, 'id': frame_id})
                
                # Tandai frame sudah selesai di queue
                frame_queue.task_done()
                
            except queue.Empty:
                # Queue kosong, lanjutkan loop untuk cek stop_event
                continue
    
    except Exception as e:
        logger.error(f"Error in frame processing worker: {e}")
    
    finally:
        # Tutup video writers
        raw_writer.release()
        bbox_writer.release()
        
        # Simpan diagnosis
        diagnosis_id = Counter(detected_classes).most_common(1)[0][0] if detected_classes else -1
        diagnosis_label = labels.get(diagnosis_id, "Unknown")
        
        # Simpan data rekaman untuk API
        recording_data["raw_path"] = raw_path
        recording_data["bbox_path"] = bbox_path
        recording_data["diagnosis"] = diagnosis_label
        
        logger.info(f"Recording complete. Diagnosis: {diagnosis_label}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('start_stream')
def handle_start_stream(data=None):  # Tambahkan parameter default data=None
    global frame_counter, processed_frames, worker_threads
    
    # Reset data
    stop_event.clear()
    with frame_lock:
        frame_counter = 0
        processed_frames = {}
    
    recording_data["raw_path"] = None
    recording_data["bbox_path"] = None
    recording_data["diagnosis"] = None
    
    # Bersihkan worker threads yang mungkin masih berjalan
    worker_threads = []
    
    # Mulai worker threads untuk pemrosesan frame
    for _ in range(MAX_WORKERS):
        worker = Thread(target=process_frame_worker)
        worker.daemon = True
        worker.start()
        worker_threads.append(worker)
    
    logger.info("Started streaming and processing")
    emit('stream_started', {'status': 'started'})
    return {'status': 'started'}

@socketio.on('frame')
def handle_frame(data):
    global frame_counter
    
    if stop_event.is_set():
        return {'status': 'stopped'}
    
    try:
        # Decode frame dari base64
        frame_data = data['frame']
        if frame_data.startswith('data:image/jpeg;base64,'):
            frame_data = frame_data.replace('data:image/jpeg;base64,', '')
        
        img_data = base64.b64decode(frame_data)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("Failed to decode image")
            return {'status': 'error', 'message': 'Failed to decode image'}
        
        # Beri ID pada frame
        with frame_lock:
            current_frame_id = frame_counter
            frame_counter += 1
        
        # Masukkan ke queue untuk diproses (gunakan block=False sebagai gantinya)
        try:
            # Gunakan timeout singkat sebagai gantinya put_nowait untuk lebih handal
            frame_queue.put({"id": current_frame_id, "frame": frame}, timeout=0.1)
        except queue.Full:
            logger.warning("Frame processing queue is full, dropping frame")
        
        return {'status': 'received', 'id': current_frame_id}
    
    except Exception as e:
        logger.error(f"Error processing frame: {e}")
        return {'status': 'error', 'message': str(e)}

@socketio.on('stop_stream')
def handle_stop_stream(data=None):  # Tambahkan parameter default data=None
    logger.info("Received request to stop streaming")
    stop_event.set()
    
    # Tunggu queue kosong dengan timeout
    try:
        frame_queue.join()
    except:
        logger.warning("Failed to join queue, continuing anyway")
    
    # Kirim data ke API setelah pemrosesan selesai
    def delayed_api_send():
        time.sleep(1)  # Tunggu sebentar untuk memastikan worker threads selesai
        if recording_data["raw_path"] and recording_data["bbox_path"] and recording_data["diagnosis"]:
            success = send_to_api(
                recording_data["raw_path"], 
                recording_data["bbox_path"], 
                recording_data["diagnosis"]
            )
            # Beritahu client tentang status pengiriman API
            socketio.emit('api_result', {
                'success': success,
                'diagnosis': recording_data["diagnosis"]
            })
            return success
        else:
            logger.error("Recording data incomplete. Cannot send to API.")
            socketio.emit('api_result', {'success': False, 'message': 'Data rekaman tidak lengkap'})
            return False
    
    # Mulai thread untuk kirim ke API
    api_thread = Thread(target=delayed_api_send)
    api_thread.daemon = True
    api_thread.start()
    
    emit('stream_stopped', {'status': 'stopping', 'message': 'Recording stopped, processing data'})
    return {'status': 'stopping', 'message': 'Recording stopped, processing data'}

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
        return response.status_code >= 200 and response.status_code < 300
    
    except Exception as e:
        logger.error(f"Error sending to API: {e}")
        return False

if __name__ == '__main__':
    socketio.run(app,
                host=app.config['HOST'],
                port=app.config['PORT'],
                debug=app.config['DEBUG'])