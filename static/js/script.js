// REST
let isStreaming = false;
let mediaStream = null;
const videoElement = document.getElementById("video");
const startButton = document.querySelector(".open");
const stopButton = document.querySelector(".close");
const localVideo = document.createElement("video");

// Configurasi webcam browser
const constraints = {
  video: {
    width: { ideal: 512 },
    height: { ideal: 512 },
    facingMode: "user", // Gunakan kamera depan, ubah ke "environment" untuk kamera belakang
  },
};

// Setup canvas untuk ekstrak frame
const canvas = document.createElement("canvas");
canvas.width = 512;
canvas.height = 512;
const ctx = canvas.getContext("2d");

// Create notification element
function createNotification() {
  // Check if notification container already exists
  if (document.getElementById("notification-container")) {
    return;
  }

  // Create notification container
  const notificationContainer = document.createElement("div");
  notificationContainer.id = "notification-container";
  notificationContainer.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 15px 25px;
    border-radius: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    opacity: 0;
    transition: opacity 0.3s ease;
    font-family: Arial, sans-serif;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  `;

  document.body.appendChild(notificationContainer);
  return notificationContainer;
}

// Show notification
function showNotification(message, isSuccess = true) {
  const container = createNotification();

  // Set content based on success/error
  if (isSuccess) {
    container.innerHTML = `
      <div style="display: flex; align-items: center;">
        <div style="color: #4CAF50; font-size: 24px; margin-right: 10px;">✓</div>
        <div>${message}</div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div style="display: flex; align-items: center;">
        <div style="color: #F44336; font-size: 24px; margin-right: 10px;">✕</div>
        <div>${message}</div>
      </div>
    `;
  }

  // Show notification
  setTimeout(() => {
    container.style.opacity = "1";
  }, 10);

  // Hide and remove after delay
  setTimeout(() => {
    container.style.opacity = "0";
    setTimeout(() => {
      if (container && container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }, 300);
  }, 1500); // Show for 1.5 seconds
}

// Function untuk ekstrak dan kirim frame ke server
let frameInterval = null;
async function captureAndSendFrames() {
  if (!isStreaming || !mediaStream) return;

  try {
    // Gambar frame dari video ke canvas
    ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);

    // Ambil data gambar sebagai base64
    const imageData = canvas.toDataURL("image/jpeg", 0.8);

    // Kirim ke server
    const response = await fetch("/upload_frame", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ frame: imageData }),
    });

    if (!response.ok) {
      console.error("Error sending frame to server:", response.statusText);
    }
  } catch (error) {
    console.error("Error capturing or sending frame:", error);
  }
}

// Tombol Start
startButton.addEventListener("click", async function () {
  if (!isStreaming) {
    try {
      // Minta izin akses webcam
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

      // Tampilkan stream webcam lokal (tidak terlihat pengguna)
      localVideo.srcObject = mediaStream;
      localVideo.play();

      // Mulai stream hasil pemrosesan dari server
      videoElement.src = "/process_video";

      // Mulai kirim frame ke server
      frameInterval = setInterval(captureAndSendFrames, 100); // 10 FPS

      isStreaming = true;
      startButton.disabled = true;
      stopButton.disabled = false;

      console.log("Recording started");
      showNotification("Recording started", true);
    } catch (error) {
      console.error("Error accessing webcam:", error);
      showNotification("Gagal mengakses kamera", false);
    }
  }
});

// Tombol Stop
stopButton.addEventListener("click", async function () {
  if (isStreaming) {
    // Disable buttons during processing
    stopButton.disabled = true;

    try {
      // Hentikan pengiriman frame
      clearInterval(frameInterval);

      // Hentikan stream webcam
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
      }

      console.log("Sending stop request to server");
      const response = await fetch("/stop_recording", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Server response:", data);
        showNotification("Recording stopped, processing data", true);
      } else {
        console.error("Server returned error:", response.status);
        showNotification("Failed to stop recording", false);
      }
    } catch (error) {
      console.error("Error stopping recording:", error);
      showNotification("Error contacting server", false);
    } finally {
      // Stop the video stream
      videoElement.src = "";
      isStreaming = false;
      startButton.disabled = false;
      console.log("Recording stopped");
    }
  }
});

// Reset Page
function resetPage() {
  // Hentikan semua media streams sebelum refresh
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
  window.location.reload();
}

// Tampilkan pesan jika browser tidak mendukung getUserMedia
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
  showNotification("Maaf, browser Anda tidak mendukung akses kamera", false);
  startButton.disabled = true;
}

// Websocket

// Websocket - optimized for better performance

// let isStreaming = false;
// let mediaStream = null;
// let socket = null;
// const videoElement = document.getElementById("video");
// const startButton = document.querySelector(".open");
// const stopButton = document.querySelector(".close");
// const localVideo = document.createElement("video");

// // Optimasi 1: Kurangi FPS untuk mengurangi beban pada server
// const FPS = 60; // Turunkan FPS dari 15 ke 10

// // Optimasi 2: Turunkan resolusi untuk performa lebih baik
// const constraints = {
//   video: {
//     width: { ideal: 480 }, // Turunkan dari 512 ke 480
//     height: { ideal: 480 }, // Turunkan dari 512 ke 480
//     facingMode: "user",
//   },
// };

// // Optimasi 3: Kurangi ukuran canvas untuk pengolahan lebih cepat
// const canvas = document.createElement("canvas");
// canvas.width = 480; // Sesuaikan dengan constraints
// canvas.height = 480; // Sesuaikan dengan constraints
// const ctx = canvas.getContext("2d");

// // Create notification element
// function createNotification() {
//   // Check if notification container already exists
//   if (document.getElementById("notification-container")) {
//     return document.getElementById("notification-container");
//   }

//   // Create notification container
//   const notificationContainer = document.createElement("div");
//   notificationContainer.id = "notification-container";
//   notificationContainer.style.cssText = `
//     position: fixed;
//     top: 50%;
//     left: 50%;
//     transform: translate(-50%, -50%);
//     background: rgba(0, 0, 0, 0.8);
//     color: white;
//     padding: 15px 25px;
//     border-radius: 5px;
//     display: flex;
//     align-items: center;
//     justify-content: center;
//     z-index: 9999;
//     opacity: 0;
//     transition: opacity 0.3s ease;
//     font-family: Arial, sans-serif;
//     box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
//   `;

//   document.body.appendChild(notificationContainer);
//   return notificationContainer;
// }

// // Show notification
// function showNotification(message, isSuccess = true) {
//   const container = createNotification();

//   // Set content based on success/error
//   if (isSuccess) {
//     container.innerHTML = `
//       <div style="display: flex; align-items: center;">
//         <div style="color: #4CAF50; font-size: 24px; margin-right: 10px;">✓</div>
//         <div>${message}</div>
//       </div>
//     `;
//   } else {
//     container.innerHTML = `
//       <div style="display: flex; align-items: center;">
//         <div style="color: #F44336; font-size: 24px; margin-right: 10px;">✕</div>
//         <div>${message}</div>
//       </div>
//     `;
//   }

//   // Show notification
//   setTimeout(() => {
//     container.style.opacity = "1";
//   }, 10);

//   // Hide and remove after delay
//   setTimeout(() => {
//     container.style.opacity = "0";
//     setTimeout(() => {
//       if (container && container.parentNode) {
//         container.parentNode.removeChild(container);
//       }
//     }, 300);
//   }, 1500); // Show for 1.5 seconds
// }

// // Menampilkan frame yang diproses pada elemen video
// function displayProcessedFrame(base64Image) {
//   if (!isStreaming) return;

//   // Optimasi 4: Menerapkan frame skipping jika sistem lag
//   const now = performance.now();
//   if (now - lastFrameDisplayed < 50) {
//     // Jangan tampilkan frame jika interval kurang dari 50ms
//     return;
//   }
//   lastFrameDisplayed = now;

//   // Optimasi 5: Simplifikasi proses rendering dengan img.src langsung
//   videoElement.src = "data:image/jpeg;base64," + base64Image;
// }

// // Inisialisasi WebSocket
// function initSocket() {
//   if (socket) {
//     socket.disconnect();
//   }

//   // Ambil socket.io dari CDN jika belum diload
//   if (typeof io === "undefined") {
//     console.error(
//       "Socket.IO not loaded! Please ensure socket.io is properly included."
//     );
//     showNotification("Error: Socket.IO not loaded", false);
//     return null;
//   }

//   // Optimasi 6: Tingkatkan timeout untuk menghindari koneksi terputus karena jaringan lambat
//   socket = io.connect(window.location.origin, {
//     reconnection: true,
//     reconnectionAttempts: 5,
//     timeout: 10000, // Tambah timeout koneksi jadi 10 detik
//   });

//   socket.on("connect", () => {
//     console.log("WebSocket connected");
//   });

//   socket.on("disconnect", () => {
//     console.log("WebSocket disconnected");
//     if (isStreaming) {
//       showNotification("Koneksi terputus", false);
//       stopStreaming();
//     }
//   });

//   socket.on("processed_frame", (data) => {
//     // Tampilkan frame yang sudah diproses
//     if (isStreaming) {
//       displayProcessedFrame(data.frame);
//     }
//   });

//   socket.on("stream_started", (data) => {
//     console.log("Stream started confirmation from server:", data);
//   });

//   socket.on("stream_stopped", (data) => {
//     console.log("Stream stopped confirmation from server:", data);
//   });

//   socket.on("api_result", (data) => {
//     if (data.success) {
//       showNotification(`Diagnosa: ${data.diagnosis}`, true);
//     } else {
//       showNotification("Gagal mengirim data ke API", false);
//     }
//   });

//   socket.on("connect_error", (error) => {
//     console.error("Connection error:", error);
//     showNotification("Koneksi ke server gagal", false);
//   });

//   return socket;
// }

// // Function untuk ekstrak dan kirim frame ke server melalui WebSocket
// let lastFrameTime = 0;
// let lastFrameDisplayed = 0;
// const frameDuration = 1000 / FPS; // Durasi antar frame dalam ms
// let frameSkipCounter = 0; // Untuk adaptive frame skipping

// // Optimasi 7: Tambahkan adaptive frame skipping untuk mengurangi beban
// async function captureAndSendFrame() {
//   if (!isStreaming || !mediaStream || !socket || !socket.connected) return;

//   const now = performance.now();
//   const elapsed = now - lastFrameTime;

//   // Pembatasan FPS
//   if (elapsed < frameDuration) {
//     requestAnimationFrame(captureAndSendFrame);
//     return;
//   }

//   // Optimasi 8: Adaptive frame skipping berdasarkan response time
//   if (frameSkipCounter > 0) {
//     frameSkipCounter--;
//     lastFrameTime = now;
//     if (isStreaming) {
//       requestAnimationFrame(captureAndSendFrame);
//     }
//     return;
//   }

//   lastFrameTime = now;

//   try {
//     // Gambar frame dari video ke canvas
//     ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);

//     // Optimasi 9: Kompresi gambar lebih tinggi - turunkan kualitas JPEG
//     const imageData = canvas.toDataURL("image/jpeg", 0.65); // Turunkan kualitas untuk mengurangi ukuran data

//     // Ukur waktu kirim
//     const sendTime = performance.now();

//     // Tambahkan timestamp ke frame untuk mengukur round-trip time
//     socket.emit(
//       "frame",
//       { frame: imageData, timestamp: sendTime },
//       (response) => {
//         if (response && response.status === "throttled") {
//           // Jika server throttling, tambah frame skipping
//           frameSkipCounter = 2; // Skip 2 frame berikutnya
//         } else if (response && response.status === "received") {
//           // Ukur round-trip time
//           const rtt = performance.now() - sendTime;

//           // Sesuaikan frame skipping berdasarkan RTT
//           if (rtt > 200) {
//             frameSkipCounter = 3; // Skip lebih banyak frame jika jaringan lambat
//           } else if (rtt > 100) {
//             frameSkipCounter = 1; // Skip sedikit frame
//           } else {
//             frameSkipCounter = 0; // Tidak perlu skip frame
//           }
//         }
//       }
//     );
//   } catch (error) {
//     console.error("Error capturing or sending frame:", error);
//   }

//   // Lanjutkan loop jika masih streaming
//   if (isStreaming) {
//     requestAnimationFrame(captureAndSendFrame);
//   }
// }

// // Indikator status koneksi
// let connectionStatus = document.createElement("div");
// connectionStatus.style.cssText = `
//   position: absolute;
//   bottom: 10px;
//   right: 10px;
//   width: 15px;
//   height: 15px;
//   border-radius: 50%;
//   background-color: gray;
// `;
// document.querySelector(".camera-container").appendChild(connectionStatus);

// // Optimasi 10: Tambahkan monitoring koneksi untuk notifikasi visual
// function updateConnectionStatus() {
//   if (!socket) {
//     connectionStatus.style.backgroundColor = "gray";
//     return;
//   }

//   if (socket.connected) {
//     connectionStatus.style.backgroundColor = "green";
//   } else {
//     connectionStatus.style.backgroundColor = "red";
//   }
// }

// // Update status koneksi setiap 2 detik
// setInterval(updateConnectionStatus, 2000);

// // Start streaming
// async function startStreaming() {
//   if (isStreaming) return;

//   try {
//     // Inisialisasi WebSocket jika belum
//     if (!socket || !socket.connected) {
//       socket = initSocket();
//       if (!socket) {
//         showNotification("Gagal menghubungkan ke server", false);
//         return;
//       }
//     }

//     // Minta izin akses webcam
//     mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

//     // Tampilkan stream webcam lokal (tidak terlihat pengguna)
//     localVideo.srcObject = mediaStream;
//     await localVideo.play();

//     // Beri tahu server untuk mempersiapkan streaming
//     socket.emit("start_stream", {});

//     // Mulai pengiriman frame menggunakan requestAnimationFrame
//     isStreaming = true;
//     lastFrameTime = 0;
//     lastFrameDisplayed = 0;
//     frameSkipCounter = 0;

//     // Mulai loop pengiriman frame
//     requestAnimationFrame(captureAndSendFrame);

//     startButton.disabled = true;
//     stopButton.disabled = false;

//     console.log("Recording started");
//     showNotification("Recording started", true);
//   } catch (error) {
//     console.error("Error accessing webcam:", error);
//     showNotification("Gagal mengakses kamera", false);
//   }
// }

// // Stop streaming
// async function stopStreaming() {
//   if (!isStreaming) return;

//   // Disable buttons during processing
//   stopButton.disabled = true;

//   try {
//     // Beri tahu server untuk menghentikan streaming
//     if (socket && socket.connected) {
//       socket.emit("stop_stream", {});
//     }

//     // Hentikan stream webcam
//     if (mediaStream) {
//       mediaStream.getTracks().forEach((track) => track.stop());
//       mediaStream = null;
//     }

//     // Bersihkan elemen video
//     videoElement.src = "";

//     isStreaming = false;

//     console.log("Recording stopped");
//     showNotification("Recording stopped, processing data", true);
//   } catch (error) {
//     console.error("Error stopping recording:", error);
//     showNotification("Error stopping recording", false);
//   } finally {
//     startButton.disabled = false;
//   }
// }

// // Tombol Start dengan anti-double click
// startButton.addEventListener("click", () => {
//   if (startButton.disabled) return;
//   startButton.disabled = true;
//   setTimeout(() => startStreaming(), 100); // Delay kecil untuk UI feedback
// });

// // Tombol Stop dengan anti-double click
// stopButton.addEventListener("click", () => {
//   if (stopButton.disabled) return;
//   stopButton.disabled = true;
//   setTimeout(() => stopStreaming(), 100); // Delay kecil untuk UI feedback
// });

// // Reset Page
// function resetPage() {
//   // Hentikan semua media streams sebelum refresh
//   stopStreaming();
//   if (socket) {
//     socket.disconnect();
//   }
//   window.location.reload();
// }

// // Tambahkan script Socket.IO ke halaman
// function loadSocketIO() {
//   // Periksa apakah Socket.IO sudah diload
//   if (typeof io !== "undefined") {
//     console.log("Socket.IO already loaded");
//     initSocket();
//     return;
//   }

//   console.log("Loading Socket.IO script");
//   const script = document.createElement("script");
//   script.src =
//     "https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.min.js";
//   script.onload = () => {
//     console.log("Socket.IO loaded");
//     initSocket();
//   };
//   script.onerror = (error) => {
//     console.error("Failed to load Socket.IO:", error);
//     showNotification("Failed to load Socket.IO library", false);
//   };
//   document.head.appendChild(script);
// }

// // Load Socket.IO saat halaman dimuat
// document.addEventListener("DOMContentLoaded", loadSocketIO);

// // Tambahkan template HTML untuk Socket.IO jika belum ada
// document.addEventListener("DOMContentLoaded", () => {
//   // Pastikan script socket.io sudah diinclude di template
//   const socketScripts = document.querySelectorAll('script[src*="socket.io"]');
//   if (socketScripts.length === 0) {
//     loadSocketIO();
//   }
// });

// // Tampilkan pesan jika browser tidak mendukung getUserMedia
// if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
//   showNotification("Maaf, browser Anda tidak mendukung akses kamera", false);
//   startButton.disabled = true;
// }
