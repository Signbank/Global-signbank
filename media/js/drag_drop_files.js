function preventDefaults(e) {
    e.preventDefault()
    e.stopPropagation()
}

/**
 * Change the drop area to red/green to accept/deny dragged files
 * @param {event} e event
 * @param {label} dropContainerStatus shows drop feedback
 * @param {string} dropContainerTitle normally "Drop here..."
 * @param {div} dropArea the area to drag files in
 * @param {label} inputArea normally "no file chosen"
 * @param {label} typeButtons the button to choose a file
 * @param {div} typeGallery the gallery that shows file previews
 * @param {string} fileType either "video/mp4", "video/quicktime" or "image/jpeg"
 * @param {string} fileTypeT either "video" or "image"
 */
 function highlight(e, dropContainerStatus, dropContainerTitle, dropArea, inputArea, typeButtons, typeGallery, fileType, fileTypeT) {
    dropContainerStatus.classList.remove('hide');
    dropContainerTitle.classList.add('hide');
    inputArea.classList.add('hide');
    typeButtons.classList.add('hide');
    typeGallery.classList.add('hide');
    let feedback = checkinput(e, fileType, fileTypeT);
    dropContainerStatus.innerHTML = feedback;
    if (feedback == "Drop") {
        dropArea.classList.add('highlight-green');
    } else{
        dropArea.classList.add('highlight-red');
    }
    e.preventDefault();
}

/**
 * Revert back to original/grey upload forms
 * @param {event} e 
 * @param {div} dropArea the area to drag files in
 * @param {label} inputArea normally "no file chosen"
 * @param {string} dropContainerTitle normally "Drop here..."
 * @param {label} dropContainerStatus shows drop feedback
 * @param {label} typeButtons the button to choose a file
 * @param {div} typeGallery the gallery that shows file previews
 */
function unhighlight(e, dropArea, inputArea, dropContainerTitle, dropContainerStatus, typeButtons, typeGallery) {
    dropArea.classList.remove('highlight-green', 'highlight-red');
    dropContainerTitle.classList.remove('hide');
    inputArea.classList.remove('hide');
    typeButtons.classList.remove('hide');
    typeGallery.classList.remove('hide');
    dropContainerStatus.classList.add('hide');
    e.preventDefault();
}


/**
 * Check if the input file is allowed to be uploaded
 * in this case: if it is 1 file and of the right type
 * @param {event} e event
 * @param {string} file_type either "video/mp4", "video/quicktime" or "image/jpeg"
 * @param {string} file_placeholder either "video" or "image"
 * @returns {string} feedback string to view during hovering
 */
function checkinput(e, file_type, file_placeholder) {
    inputfiles = e.dataTransfer.items
    if (inputfiles.length != 1) {
        return "Only 1 file accepted";
    }
    else if (!file_type.includes(inputfiles[0].type)){
        return "Only "+file_placeholder+" files accepted";
    }
    else{
        return "Drop";
    }
}

/**
 * If upload through regular input button, also show previews in gallery
 * @param {event} files event
 * @param {string} dropContainerTitle normally "Drop here..."
 * @param {string} fileType either "video/mp4", "video/quicktime" or "image/jpeg"
 * @param {string} fileTypeP either "video" or "img" for making gallery element
 * @param {label} inputArea normally "no file chosen"
 * @param {div} typeGallery the gallery that shows file previews
 */
function handleByButton(files, dropContainerTitle, fileType, fileTypeP, inputArea, typeGallery) {
    if (files[0].size > 5242880){
        dropContainerTitle.innerHTML = "<p style='color:#FF0000';>Error, try again: <br>keep the file size under 5 MB</p>";
        inputArea.value = '';
        removeUploads(true, inputArea, dropContainerTitle, typeGallery)
    }
    else if (fileType.includes(files[0].type)) {
        dropContainerTitle.classList.add('hide');
        previewFile(files[0], fileTypeP, typeGallery)
    }
    else {
        inputArea.value = '';
        if (typeGallery.childNodes.length > 0){
            if (!dropContainerTitle.classList.contains('hide')){
                dropContainerTitle.classList.add('hide');
            }
        }
        else {
            if (dropContainerTitle.classList.contains('hide')){
                dropContainerTitle.classList.remove('hide');
            }
        }
    }
}


/**
 * If upload through drag&drop, empty gallery and show new previews
 * @param {event} e event
 * @param {string} fileType either "video/mp4", "video/quicktime" or "image/jpeg"
 * @param {string} fileTypeT either "video" or "image"
 * @param {string} fileTypeP either "video" or "img" for making gallery element
 * @param {label} inputArea normally "no file chosen"
 * @param {div} typeGallery the gallery that shows file previews
 * @param {label} dropContainerTitle normally "Drop here..."
 */
function handleDrop(e, fileType, fileTypeT, fileTypeP, inputArea, typeGallery, dropContainerTitle){
    files = e.dataTransfer.files
    if (files[0].size > 5242880){
        dropContainerTitle.innerHTML = "<p style='color:#FF0000';>Error, try again: <br>keep the file size under 5 MB</p>";
        inputArea.value = '';
        removeUploads(true, inputArea, dropContainerTitle, typeGallery)
    }
    else if (checkinput(e, fileType, fileTypeT) == "Drop") {
        inputArea.value = '';
        removeUploads(true, inputArea, dropContainerTitle, typeGallery)
        dropContainerTitle.classList.add('hide');
        previewFile(files[0], fileTypeP, typeGallery)
        inputArea.files = files
        dropContainerTitle.innerHTML = "Drop "+fileTypeT+" here";
    }
    else if (typeGallery.childNodes.length > 0){
        if (!dropContainerTitle.classList.contains('hide')){
        dropContainerTitle.classList.add('hide');
        }
    }
    else {
        if (dropContainerTitle.classList.contains('hide')){
        dropContainerTitle.classList.remove('hide');
        }
    }
    e.preventDefault();
}


/**
 * Remove the previewed files from the gallery
 * @param {boolean} remove_file_name whether to remove filename from regular input form
 * @param {label} inputArea normally "no file chosen"
 * @param {string} dropContainerTitle normally "Drop here..."
 * @param {div} typeGallery the gallery that shows file previews
 */
function removeUploads(remove_file_name, inputArea, dropContainerTitle, typeGallery){
    if (remove_file_name){
        inputArea.value = '';
    }
    dropContainerTitle.classList.remove('hide');
    while (typeGallery.firstChild) {
        typeGallery.removeChild(typeGallery.firstChild);
    }
}


/**
 * Show the file to upload as preview
 * @param {file} file file to preview
 * @param {string} fileTypeP either "video" or "img" for making gallery element
 * @param {div} typeGallery the gallery that shows file previews
 */
function previewFile(file, fileTypeP, typeGallery) {
    let reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onloadend = function() {
        prev = document.createElement(fileTypeP)
        prev.src = reader.result
        typeGallery.appendChild(prev)
    }
}


///////////////////////////////////////////////
// Initialize variables for video
let dropVideoArea = document.getElementById('drop-container-video')
let inputVideoArea = document.getElementById('id_videofile')
inputVideoArea.onchange = function(){handleVideoByButton(this.files)}
let dropContainerVideoStatus = document.getElementById('drop-container-video-status')
let dropContainerVideoTitle = document.getElementById('drop-container-title-video')
let videoButtons = document.getElementById('video-buttons')
let videoGallery = document.getElementById('videogallery')

// Set event listeners for hovering/dropping files
;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropVideoArea.addEventListener(eventName, preventDefaults, false)
})

;['dragenter', 'dragover'].forEach(eventName => {
    dropVideoArea.addEventListener(eventName, highlightvideo, false)
})

;['dragleave', 'drop'].forEach(eventName => {
    dropVideoArea.addEventListener(eventName, unhighlightvideo, false)
})

function highlightvideo(e) {
    const allowed_file_types = ["video/mp4","video/quicktime"]
    highlight(e, dropContainerVideoStatus, dropContainerVideoTitle, dropVideoArea, inputVideoArea, videoButtons, videoGallery, allowed_file_types, 'video')
}

function unhighlightvideo(e) {
    unhighlight(e, dropVideoArea, inputVideoArea, dropContainerVideoTitle, dropContainerVideoStatus, videoButtons, videoGallery)
}

function handleVideoByButton(files) {
    removeVideoUploads(false)
    const allowed_file_types = ["video/mp4","video/quicktime"]
    handleByButton(files, dropContainerVideoTitle, allowed_file_types, 'video', inputVideoArea, videoGallery)
}

dropVideoArea.addEventListener('drop', handleVideoDrop, false)
function handleVideoDrop(e) {
    const allowed_file_types = ["video/mp4","video/quicktime"]
    handleDrop(e, allowed_file_types, 'video', 'video', inputVideoArea, videoGallery, dropContainerVideoTitle)
}

function removeVideoUploads(remove_file_name){
    removeUploads(remove_file_name, inputVideoArea, dropContainerVideoTitle, videoGallery)
}

///////////////////////////////////////////////////////
// Initialize variables for image, if this is possible
let dropImageArea = document.getElementById('drop-container-image')
let image = false
if (typeof(dropImageArea) != 'undefined' && dropImageArea != null){
    image = true
}

if (image === true){
    let inputImageArea = document.getElementById('id_imagefile')
    inputImageArea.onchange = function(){handleImageByButton(this.files)}
    let dropContainerImageStatus = document.getElementById('drop-container-image-status')
    let dropContainerImageTitle = document.getElementById('drop-container-title-image')
    let imageButtons = document.getElementById('image-buttons')
    let imageGallery = document.getElementById('imagegallery')
    
    // Set event listeners for hovering/dropping files
    ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropImageArea.addEventListener(eventName, preventDefaults, false)
    })

    ;['dragenter', 'dragover'].forEach(eventName => {
        dropImageArea.addEventListener(eventName, highlightimage, false)
    })

    ;['dragleave', 'drop'].forEach(eventName => {
        dropImageArea.addEventListener(eventName, unhighlightimage, false)
    })

    function highlightimage(e) {
        highlight(e, dropContainerImageStatus, dropContainerImageTitle, dropImageArea, inputImageArea, imageButtons, imageGallery, ['image/jpeg'], 'image')
    }

    function unhighlightimage(e) {
        unhighlight(e, dropImageArea, inputImageArea, dropContainerImageTitle, dropContainerImageStatus, imageButtons, imageGallery)
    }

    function handleImageByButton(files) {
        removeImageUploads(false)
        handleByButton(files, dropContainerImageTitle, ['image/jpeg'], 'img', inputImageArea, imageGallery)
    }

    dropImageArea.addEventListener('drop', handleImageDrop, false)
    function handleImageDrop(e) {
        handleDrop(e, ['image/jpeg'], 'image', 'img', inputImageArea, imageGallery, dropContainerImageTitle)
    }

    function removeImageUploads(remove_file_name){
        removeUploads(remove_file_name, inputImageArea, dropContainerImageTitle, imageGallery)
    }
}

