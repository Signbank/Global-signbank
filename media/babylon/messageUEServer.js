function sendMessageUEProxy(messageType, messageContent) {
    return new Promise((resolve, reject) => {
        // Construct the POST request to the Flask server
        console.log(`Sending message: ${JSON.stringify({ messageType, messageContent })}`);
        fetch('/proxy_retarget', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json'
            },
            body: JSON.stringify({
            messageType: messageType,
            messageContent: messageContent
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log(`Received from Flask: ${data.response}`);
                resolve(data.response);
            } else {
                console.error(`Error from Flask: ${data.message}`);
                reject(new Error(data.message));
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            reject(new Error('Fetch error: ' + error.message));
        });
    });
}

function sendMessageUE(messageType, messageContent, host = retargetServerHost, port = retargetServerPort) {
    return new Promise((resolve, reject) => {
        // WebSocket connection
        console.log(`Connecting to ws://${host}:${port}`);
        const socket = new WebSocket(`ws://${host}:${port}`);
        var response = null;

        // Connection opened
        socket.addEventListener('open', function (event) {
            console.log('WebSocket connected');
            
            // Create the message string
            const message = `${messageType}:${messageContent}`;
            
            // Send the message
            socket.send(message);
            console.log(`Sent message: ${message}`);
        });

        // Listen for messages from the server
        socket.addEventListener('message', function (event) {
            console.log(`Received: ${event.data}`);
            response = event.data; // Resolve the promise with received data
        });

        // Listen for connection close
        socket.addEventListener('close', function (event) {
            console.log('Connection closed');
            resolve(response);
        });

        // Listen for errors
        socket.addEventListener('error', function (event) {
            console.error('WebSocket error:', event);
            reject(new Error('WebSocket error'));
        });
    });
}
/**
 * Sends a command to import a mesh in Unreal Engine.
 * 
 * @param {string} meshURL - The URL of the mesh to import.
 * @returns {Promise<boolean>} - A promise that resolves to true if the command is successfully sent, or false if there is an error.
 */
function sendCommandUEMesh(meshURL) {
    const meshName = meshURL.split('/').pop().split('.')[0];

    return sendMessageUEProxy('import_fbx_from_url', meshURL)
        .then(meshPath => {
            if (!meshPath.includes("path")) {
                throw new Error("Invalid response, meshPath does not contain 'path'\tResponse: " + meshPath);
            }

            // Response form "File downloaded successfully path(/usr/src/your_project/imports/ERROR-SC.fbx)." Only the path is needed
            meshPath = meshPath.split(' ').pop().slice(0, -2);
            // Remove path( from the beginning
            meshPath = meshPath.slice(5);
            return sendMessageUEProxy('import_fbx', meshPath);
        })
        .then(meshPathUE => {
            return true;
        })
        .catch(error => {
            console.error("Error in sendCommandUEMeshRig:", error);
            return false;
        });
}

function sendCommandUEAnim(animURL, skeletonPath = null) {
    const animName = animURL.split('/').pop().split('.')[0].replace('.fbx', '');
    const UEDestPath = `/Game/ImportedAssets/`;

    return sendMessageUEProxy('import_fbx_from_url', animURL)
        .then(animPath => {
            console.log("animPath:", animPath)
            // Response form "File downloaded successfully path(/usr/src/your_project/imports/ERROR-SC.fbx)." Only the path is needed
            animPath = animPath.split(' ').pop().slice(0, -2);
            // Remove path( from the beginning
            animPath = animPath.slice(5);
            if (skeletonPath) {
                return sendMessageUEProxy('import_fbx_animation', animPath + "," + UEDestPath + "," + animName + "," + skeletonPath);
            }

            return sendMessageUEProxy('import_fbx_animation', animPath + "," + UEDestPath + "," + animName);
        })
        .then(res => {
            return true;
        })
        .catch(error => {
            console.error("Error in sendCommandUEAnim:", error);
            return false;
        });
}

function sendCommandUEAnimRetargetSend(sourceMeshPath, targetMeshPath, animPath, sendPath) {
    console.log("sendCommandUEAnimRetargetSend", sourceMeshPath, targetMeshPath, animPath, sendPath);
    // Make sure animPath is a string containing /Game/ImportedAssets/
//    if (typeof animPath !== 'string' || !animPath.includes('/Game/ImportedAssets/')) {
//        return Promise.reject(new Error("animPath must be a string containing /Game/ImportedAssets/"));
//    }

    return sendMessageUEProxy('rig_retarget_send', sourceMeshPath + "," + targetMeshPath + "," + animPath + "," + sendPath)
        .then(sourceMeshPathUE => {
            return true;
        })
        .catch(error => {
            console.error("Error in sendCommandUEAnimRetarget:", error);
            return false;
        });
}

/**
 * Helper function to execute the entire process: import source and target meshes,
 * import an animation, retarget the animation, and send it to the specified endpoint.
 * 
 * @param {string} sourceMeshURL - The URL of the source mesh to import.
 * @param {string} targetMeshURL - The URL of the target mesh to import.
 * @param {string} animURL - The URL of the animation to import.
 * @param {string} sendPath - The URL to send the retargeted animation to.
 * @param {string|null} sourceMeshPath - (Optional) The source mesh path in Unreal Engine. Defaults based on sourceMeshURL.
 * @param {string|null} targetMeshPath - (Optional) The target mesh path in Unreal Engine. Defaults based on targetMeshURL.
 * @param {string|null} skeletonPath - (Optional) The path to the skeleton in Unreal Engine. Defaults based on sourceMeshPath.
 * @returns {Promise<boolean>} - A promise that resolves to true if all steps succeed, or false if any step fails.
 */
function retargetUE(sourceMeshURL, targetMeshURL, animURL, sendPath, sourceMeshPath = null, targetMeshPath = null, skeletonPath = null) {
    const UEDestPath = MeshesAndAnims;
    const animName = animURL.split('/').pop().split('.')[0].replace('.fbx', '');

    // Derive mesh names from the URLs
    const sourceMeshName = sourceMeshURL.split('/').pop().split('.')[0];
    const targetMeshName = targetMeshURL.split('/').pop().split('.')[0];

    // Set default paths based on the mesh names if not provided
    sourceMeshPath = sourceMeshPath || `/Game/SkeletalMeshes/${sourceMeshName}/${sourceMeshName}`;
    targetMeshPath = targetMeshPath || `/Game/SkeletalMeshes/${targetMeshName}/${targetMeshName}`;
    skeletonPath = skeletonPath || sourceMeshPath; // Default to sourceMeshPath if skeletonPath is not provided

    let animPath;

    // Import the source and target meshes, then the animation, then retarget and send
    return sendCommandUEMesh(sourceMeshURL)
        .then(() => sendCommandUEMesh(targetMeshURL))
        .then(() => sendCommandUEAnim(animURL, skeletonPath))
        .then(() => {
            const fullAnimPath = `${UEDestPath}${animName}`;
            return sendCommandUEAnimRetargetSend(sourceMeshPath, targetMeshPath, fullAnimPath, sendPath);
        })
        .then(() => true)
        .catch(error => {
            console.error("Error in executeFullProcess:", error);
            return false;
        });
}

// Example usage
// sendCommandUEMeshRig('http://example.com/mesh.fbx');
