let isStreaming = false;
const videoElement = document.getElementById('video');
const startButton = document.querySelector('.open');
const stopButton = document.querySelector('.close');

// Create notification element
function createNotification() {
  // Check if notification container already exists
  if (document.getElementById('notification-container')) {
    return;
  }
  
  // Create notification container
  const notificationContainer = document.createElement('div');
  notificationContainer.id = 'notification-container';
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
    container.style.opacity = '1';
  }, 10);
  
  // Hide and remove after delay
  setTimeout(() => {
    container.style.opacity = '0';
    setTimeout(() => {
      if (container && container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }, 300);
  }, 1500); // Show for 1.5 seconds
}

// Tombol Start
startButton.addEventListener('click', function () {
  if (!isStreaming) {
    videoElement.src = '/process_video';
    isStreaming = true;
    startButton.disabled = true;
    stopButton.disabled = false;
    console.log("Recording started");
  }
});

// Tombol Stop
stopButton.addEventListener('click', async function () {
  if (isStreaming) {
    // Disable buttons during processing
    stopButton.disabled = true;
    
    try {
      console.log("Sending stop request to server");
      const response = await fetch('/stop_recording', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
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
      videoElement.src = '';
      isStreaming = false;
      startButton.disabled = false;
      console.log("Recording stopped");
    }
  }
});

// Reset Page
function resetPage() {
  window.location.reload();
}