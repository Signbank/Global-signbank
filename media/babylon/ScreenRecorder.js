let mediaRecorder;
let recordedChunks = [];

async function startRecording(canvasId, animFilename) {
    return new Promise((resolve, reject) => {
        const canvas = document.getElementById(canvasId);
        const stream = canvas.captureStream(60); // Capture at 30 frames per second

        recordedChunks = [];
        const options = {
            mimeType: 'video/webm',
            videoBitsPerSecond: 8000000, // Set video bitrate to 8 Mbps
            width: 1920, // Set video width to 1920 pixels
            height: 1080 // Set video height to 1080 pixels
        };

        mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = function() {
            onSaveRecording(animFilename); // Pass the animFilename to the onSaveRecording function
        };

        mediaRecorder.start();

        mediaRecorder.onstart = () =>{

            resolve();

        }
    });
}

async function stopRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
        console.log('Recording stopped');
    }
}

function onSaveRecording(animFilename) {
    const blob = new Blob(recordedChunks, { type: "video/webm" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    const filenameWithoutExtension = animFilename.replace(/\.glb$/, ''); 

    a.download = filenameWithoutExtension + ".webm"; 

    a.href = url;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Attach the functions to the window object to make them accessible from other scripts
window.startRecording = startRecording;
window.stopRecording = stopRecording;
