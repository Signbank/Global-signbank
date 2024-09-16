var CameraController = (function() {
    // Private variables and functions
    var camera;
    var focusSphere;
    var targetHips;
    var forwardVec;
    var distance;
    var position = {x: null, y: null, z: null};
    var trackingHand = null;
    
    function setNearPlane(value) {
        camera.minZ = value;
    }

    function setAngleAlpha(angle) {
        camera.alpha = BABYLON.Tools.ToRadians(angle);
    }

    function setAngleBeta(angle) {
        camera.beta = BABYLON.Tools.ToRadians(angle);
    }

    function getAngleAlpha() {
        return BABYLON.Tools.ToDegrees(camera.alpha);
    }

    function getAngleBeta() {
        return BABYLON.Tools.ToDegrees(camera.beta);
    }

    function getFocusSphere() {
        return focusSphere;
    }

    function setPositionValues(x, y, z) {
        position.x = x;
        position.y = y;
        position.z = z;
    }

    function getPosition() {
        console.log("Camera position: ", position);
        return position;
    }

    function setCameraParams(scene, cameraAngle, cameraAngleBeta, movingCamera) {
        // cameraAngle is in degrees so we set it to radians
        if (cameraAngle) {
            setAngleAlpha(cameraAngle);
        }
    
        // cameraAngleBeta is in degrees so we set it to radians
        if (cameraAngleBeta) {
            setAngleBeta(cameraAngleBeta);
        }
    
        if (movingCamera) {
            createCameraRotationAnimation(scene, 220, 340, 600); // Rotates from 0 to 180 degrees over 100 frames
    
            /*        async function playLoadedAnims() {
                        if (scene && loaded) {
                            
                            await playAnims(scene, loaded, 0);
                        } else {
                            console.error('Scene or loaded variables are not set.');*/
        }
    }
    
    function setCameraOnBone(scene, targetMesh, skeleton, boneIndex = 4, visualizeSphere = false, setLocalAxis = false) {
        /* Creating a camera that we set to the position of the bone attached to the mesh's neck bone:
        * 1. Create an empty object that we visualize as a sphere
        * 2. Attach the sphere to the bone
        * 3. Create a camera that we aim at the sphere
        * 4. Profit
        */
    
        // Create a sphere that we attach to the bone
        console.log("Setting camera on bone...");
        var sphere = BABYLON.Mesh.CreateSphere("sphere1", 16, 2, scene);
        sphere.scaling = new BABYLON.Vector3(0.1, 0.1, 0.1);
        sphere.attachToBone(skeleton.bones[boneIndex], targetMesh);
        console.log("Sphere attached to bone: ", skeleton.bones[boneIndex].name);
        console.log("Target mesh: ", targetMesh.name);

        // Set the position and rotation of the sphere relative to the bone
        sphere.position = new BABYLON.Vector3(0, 0, 0); // Adjust according to your needs
        sphere.rotation = new BABYLON.Vector3(0, 0, 0); // Adjust according to your needs

        
        // Debugging funcs
        sphere.setEnabled(visualizeSphere);
        if (setLocalAxis) {
            var sphere2 = BABYLON.Mesh.CreateSphere("sphere2", 16, 2, scene);
            sphere2.scaling = new BABYLON.Vector3(0.4, 0.4, 0.4);
            console.log("Sphere2: ", sphere2.forward);
            localAxes(4, sphere2, scene);
            localAxes(4, sphere, scene);
            hipsFrontAxes(4, sphere, scene);
            forwardVec = sphere.getChildren()[3];
            console.log("Forward vector: ", forwardVec);
        }

        // Initializes an ArcRotateCamera named "camera1" in the scene.
        // This camera is positioned to rotate around a target point defined by the vector (0, 0, -1).
        // The 'alpha' parameter, set as Math.PI / -2, positions the camera at -90 degrees on the XZ plane,
        // effectively placing it on the negative X-axis and facing towards the origin.
        // The 'beta' parameter of 1 radian tilts the camera slightly downward from the vertical top view.
        // The 'radius' parameter of 3 units sets the distance from the camera to the target point, placing it 3 units away.
    
        // This setup provides a unique side and slightly elevated view of the scene centered around the target point on the negative Z-axis.
        camera.target = sphere;
        focusSphere = sphere;
        targetHips = skeleton.bones[0];
    };

    function createCameraRotationAnimation(scene, startDegree, endDegree, duration) {
        // Convert degrees to radians for the alpha property
        var startRadians = BABYLON.Tools.ToRadians(startDegree);
        var endRadians = BABYLON.Tools.ToRadians(endDegree);

        // Create a new animation object for the alpha property
        var alphaAnimation = new BABYLON.Animation(
            "alphaAnimation", 
            "alpha", 
            30, 
            BABYLON.Animation.ANIMATIONTYPE_FLOAT,
            BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE // Loop mode
        );

        // Define key frames for the animation
        var keys = []; 
        keys.push({ frame: 0, value: startRadians });
        keys.push({ frame: duration/2, value: endRadians });
        keys.push({ frame: duration, value: startRadians });
        alphaAnimation.setKeys(keys);

        // Add easing function for smooth animation (optional)
        // var easingFunction = new BABYLON.CubicEase();
        // easingFunction.setEasingMode(BABYLON.EasingFunction.EASINGMODE_EASEINOUT);
        // alphaAnimation.setEasingFunction(easingFunction);

        // Apply the animation to the camera
        camera.animations = [];
        camera.animations.push(alphaAnimation);

        // Begin the animation
        scene.beginAnimation(camera, 0, 600, true, 1);
    };

    function zoom(distanceFromBone) {
        camera.radius = distanceFromBone;
    };

    function resetZoom() {
        camera.radius = CameraController.distance-1;
        camera.beta = Math.PI/2.5;
        camera.alpha = Math.PI / -2;
    };

    // Public interface
    return {
        setCameraParams: setCameraParams,
        setCameraOnBone: setCameraOnBone,
        setAngleAlpha: setAngleAlpha,
        setAngleBeta: setAngleBeta,
        getAngleAlpha: getAngleAlpha,
        getAngleBeta: getAngleBeta,
        setNearPlane: setNearPlane,
        getFocusSphere: getFocusSphere,
        setPositionValues: setPositionValues,
        getPosition: getPosition,
        zoom: zoom,
        resetZoom: resetZoom,
        getInstance: function(scene, canvas, distance=5) {
            CameraController.distance = distance;

            if (!camera) {
                console.log("Initializing camera instance...");
                // Parameters: name, alpha, beta, radius, target position, scene
                camera = new BABYLON.ArcRotateCamera("camera1", Math.PI / -2, 1, distance, new BABYLON.Vector3(0, 0, 0), scene);
                camera.attachControl(canvas, true);
                camera.wheelPrecision = 50; //Mouse wheel speed

                // Set the camera's position
                const alpha = camera.alpha;
                const beta = camera.beta;
                const radius = camera.radius;
                const target = camera.target;

                // Calculate camera position in world space
                const x = target.x + radius * Math.cos(beta) * Math.sin(alpha);
                const y = target.y + radius * Math.sin(beta);
                const z = target.z + radius * Math.cos(beta) * Math.cos(alpha);

                const cameraPosition = new BABYLON.Vector3(x, y, z);

                setPositionValues(cameraPosition.x, cameraPosition.y, cameraPosition.z);
            }

            // Attach pointer events to the scene, we dont want to interact with the gui when we are rotating the camera
            if (scene) {
                scene.onPointerDown = (e) => {
                    rootContainer.isEnabled = false;
                }
        
                scene.onPointerUp = (e) => {
                    rootContainer.isEnabled = true;
                }
            } else {
                console.error("Scene is not defined. Cannot attach pointer events.");
            }

            CameraController.camera = camera;
            return camera;
        }
    };
})();

function addAngle(angle) {
    console.log(CameraController.getAngleAlpha());
    CameraController.setAngleAlpha(CameraController.getAngleAlpha() + angle);
}
function getAngle() {
    // CameraController.logTargetHipsAngles();
    CameraController.closest();
}

