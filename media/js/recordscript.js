// Make a recorded and blobs to save the mediastream
let mediaRecorder
let recordedBlobs

// Get the modaluploadInput
const modal = document.getElementById("recordModal");
            
// Get the button that opens the modal
const modalButton = document.getElementById("recordBtn");

// Get the <span> element that closes the modal
const span = document.getElementsByClassName("close")[0];

// Get the record controlling buttons
const startButton = document.querySelector("button#start")
const errorMsgElement = document.querySelector('span#errorMsg');
const recordedVideo = document.querySelector('video#recorded');
const recordButton = document.querySelector('button#record');
const playButton = document.querySelector('button#play');
const downloadButton = document.querySelector('button#download');
const uploadInput = document.querySelector('input#uploadrecorded');

// Get the countdown overlay images
const img1 = document.getElementById("img1");
const img2 = document.getElementById("img2");
const img3 = document.getElementById("img3");

/**
 * When the user clicks the button, open the modal 
 */
modalButton.onclick = function() {
    modal.style.display = "block";
    startCamera()
  }
  
/**
 * When the user clicks on <span> (x), close the modal and stop the webcam
 */
span.onclick = function() {
    modal.style.display = "none";
    stopCamera()
}

/**
 * When the user clicks anywhere outside of the modal, close it
 */
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
        stopCamera()
    }
}

/**
 * Start or stop the camera
 */
startButton.addEventListener('click', async function(){
    if(startButton.textContent === "Stop Camera"){
        stopCamera()
    }else{
        startCamera()
    }
});

/**
 * Start the camera
 */
async function startCamera(){
    const constraints = {
        audio: false,
        video:{
            width:1280, height:720
        }
    };
    console.log('Using media constraints:', constraints);
    await init(constraints);
}

/**
 * Stop the camera
 */
async function stopCamera(){
    stream.getTracks().forEach(function(track) {
        track.stop();
    });
    startButton.textContent = "Start Camera"
    recordButton.disabled=true
}

/**
 * Start the camera stream or give error
 */
async function init(constraints){
    try{
        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        handleSuccess(stream)
        startButton.textContent = "Stop Camera"
    }catch (e){
        console.error('navigator.getUserMedia error:', e)
        errorMsgElement.innerHTML = "Could not start the camera. Please try another browser."
    }
}

/**
 * Show the video input stream
 */
function handleSuccess(stream){
    recordButton.disabled=false;
    console.log('getUserMedia() got stream:', stream);
    window.stream = stream;

    const gumVideo = document.querySelector("video#gum");
    gumVideo.srcObject=stream;
}

/**
 * Start or stop the recording
 */
recordButton.addEventListener('click',() => {
    if(recordButton.textContent === "Record"){
        startRecording();
    }else{
        mediaRecorder.stop();
    }
});

/**
 * Sleep for given number of ms
 */
function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}


/**
 * Check the recorded video and set to file input field or discard
 */
function processBlobs(recordedBlobs){
    // Add the recorded video to a hidden file input field
    if(recordedBlobs[0].size<5242880){ // Hardcoded: better take settings.FILE_UPLOAD_MAX_MEMORY_SIZE value
        const blob = new Blob(recordedBlobs, {type: 'video/mp4'});
        var file = new File([blob], "temp.mp4",{type:"video/mp4, lastModified:new Date().getTime()"})
        let container = new DataTransfer();
        container.items.add(file)
        document.getElementById('videofile').files = container.files;
    }
    else{   // size is too big to upload
        errorMsgElement.innerHTML = "Recorded file is too big. Make a shorter video or try another camera. "
        recordedBlobs = []
        document.getElementById('videofile').value = null
        uploadInput.disabled = true;
    }
}


/**
 * 1) countdown
 * 2) Start the webcam mediarecorded stream
 * 3) Enable the stop recording button
 */
async function startRecording(){

    errorMsgElement.innerHTML = ""
    playButton.disabled = true;
    downloadButton.disabled = true;
    recordButton.disabled = true;
    uploadInput.disabled = true;
    startButton.disabled = true;

    // Count down
    img1.classList.remove("invis")
    img1.classList.add("vis")
    await sleep(1000);
    img1.classList.remove("vis")
    img1.classList.add("invis")
    img2.classList.remove("invis")
    img2.classList.add("vis")
    await sleep(1000);
    img2.classList.remove("vis")
    img2.classList.add("invis")
    img3.classList.remove("invis")
    img3.classList.add("vis")
    await sleep(1000);
    img3.classList.remove("vis")
    img3.classList.add("invis")

    // Recording settings
    recordedBlobs = [];
    let options = {mimeType:'video/webm;codecs:vp9'};

    // Start the recording
    try{
        mediaRecorder = new MediaRecorder(window.stream, options);
    }catch (e){
        console.log(e);
        errorMsgElement.innerHTML = "Cannot start the recording. Please try another browser. "
    };
    mediaRecorder.ondataavailable = handleDataAvailable;
    mediaRecorder.start();
    console.log("MediaRecorded started ", mediaRecorder)

    // Enable "stop recording"
    console.log("Created MediaRecorded", mediaRecorder, "with options:", options)
    recordButton.disabled = false;
    recordButton.textContent = "Stop recording"
    
    // Save the video when recording is stopped
    mediaRecorder.onstop = (event) => {
        console.log("Recording stopped: ", event, "\nRecorded blobs: ", recordedBlobs);

        recordButton.textContent="Record";
        playButton.disabled=false;
        downloadButton.disabled=false;
        uploadInput.disabled=false;
        startButton.disabled=false;

        processBlobs(recordedBlobs)
    }
}


/**
 * Send the recorded stream to a data element
 */
function handleDataAvailable(event){
    if(event.data && event.data.size > 0){
        recordedBlobs.push(event.data);
    }
}

/**
 * Make the recorded video play when the play button is clicked
 */
playButton.addEventListener('click', () =>{
    const superBuffer = new Blob(recordedBlobs,{type:'video/mp4'});

    recordedVideo.srcObject = null;
    recordedVideo.src = window.URL.createObjectURL(superBuffer);
    recordedVideo.controls=true;
    recordedVideo.play();
})

/**
 * Enable downloading of the recorded video on click of the download button
 */
downloadButton.addEventListener('click', () => {
    const blob = new Blob(recordedBlobs, {type: 'video/mp4'});
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'glossvideo.mp4';
    document.body.appendChild(a);
    a.click();
    setTimeout(() =>{
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 100);
});
