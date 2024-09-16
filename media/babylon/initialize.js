const ParamsManager = {
    local: null,
    play: null,
    limit: null,
    glos: null,
    zin: null,
    gltf: null,
    animations: [],
    debug: false,
    lockRot: false,
    showGui: true,
    returnToIdle: true, // If for some reason later on we dont want to return to idle, we can set this to false
    startingNewAnim: false, // If we are starting a new animation, we can set this to true (to prevent race conditions)
    boneLock: 4,
    onboard: true,
    eyeBlink: true,
    meshURL: null,

    setParams(local, play, limit, glos, zin, gltf, debug, lockRot, noGui, onboard) {
        // No babylon database storage when testing locally
        if (local !== 1) {
            BABYLON.Database.IDBStorageEnabled = true;
        }

        this.local = local;
        this.play = play !== undefined ? play : true; // Set play if we have play, else default to true
        this.limit = limit !== null ? limit : 5; // Set limit if we have limit, else default to 5
        this.glos = glos !== null ? glos : "idle"; // Set glos if we have glos, else default to "idle"
        this.zin = zin;
        this.gltf = gltf;
        this.debug = debug === undefined ? false : ((debug === "1" || debug === "true") ? true : false);
        this.lockRot = lockRot === undefined ? false : ((lockRot === "1" || lockRot === "true") ? true : false);
        this.showGui = noGui === undefined ? true : ((noGui === "1" || noGui === "true") ? false : true);
        this.onboard = onboard === undefined ? true : ((onboard === "0" || onboard === "false") ? false : true);
        this.meshURL = meshURL === undefined ? null : meshURL;

        if (zin) {
            // We want to adjust frame from and to for blending
            AnimationSequencer.setFrom(80);
            AnimationSequencer.setTo(100);

            // Split zin with , and return as array
            this.animations = zin.split(",");
            console.log("Animations zin loaded:", this.animations);
        } else {
            // We want to adjust frame from and to for blending
            AnimationSequencer.setFrom(30);
            AnimationSequencer.setTo(30);

            console.log(loadSignCollectLabels(this.local, thema, this.limit, this.animations).then((animations) => {
                console.log("Animations loaded:", animations);
            }));
        }

        this.gltf = gltf;

        return [this.local, this.play, this.limit, this.glos, this.zin, this.gltf, this.animations];
    }
};

// singleton for engine related items
const EngineController = (function () {
    let engine = null;
    let scene = null;
    let loadedMesh = null;

    function setEngine(newEngine) {
        engine = newEngine;
    }

    function getEngine() {
        return engine;
    }

    function setScene(newScene) {
        scene = newScene;
    }

    function getScene() {
        return scene;
    }

    function setLoadedMesh(newLoadedMesh) {
        loadedMesh = newLoadedMesh;
    }

    function getLoadedMesh() {
        return loadedMesh;
    }

    return {
        set engine(newEngine) {
            setEngine(newEngine);
        },
        get engine() {
            return getEngine();
        },
        set scene(newScene) {
            setScene(newScene);
        },
        get scene() {
            return getScene();
        },
        set loadedMesh(newLoadedMesh) {
            setLoadedMesh(newLoadedMesh);
        },
        get loadedMesh() {
            return getLoadedMesh();
        }
    };
})();


// Usage:
// ParamsManager.setParams(local, play, limit, glos, zin, gltf, animations);

// function setParams(local, play, limit, glos, zin, gltf, animations) {
//     // No babylon database storage when testing locally
//     if (local != 1) {
//         BABYLON.Database.IDBStorageEnabled = true;
//     }

//     if (!play) {
//         play = true;
//     }

//     if (!limit) {
//         limit = 5;
//     }

//     if (glos == null) {
//         glos = "ERROR-SC";
//     }

//     if (zin) {
//         // We want to adjust frame from and to for blending
//         AnimationSequencer.setFrom(80);
//         AnimationSequencer.setTo(100);

//         //split zin with , and return as array
//         animations = zin.split(",");
//     }
//     else {
//         //we want to adjust frame from and to for blending
//         AnimationSequencer.setFrom(30);
//         AnimationSequencer.setTo(30);

//         animations = loadSignCollectLabels(local, thema, limit, animations);
//     }

//     return [local, play, limit, glos, zin, gltf, animations];
// }

async function initialize(scene, engine, canvas, basePath, basePathMesh, loadedMesh, cameraAngle, cameraAngleBeta, movingCamera, boneLock=4, blending=false, animRotation=null) {
    [scene, engine] = await createScene(
        document.getElementById("renderCanvas")
    );

    if (ParamsManager.meshURL) {
        // Split meshURL on last / and get the last element for filename and the rest for basePath
        const meshURLSplit = ParamsManager.meshURL.split("/");
        var meshName = meshURLSplit.pop();
        var meshPath = meshURLSplit.join("/") + "/";

        // If meshPath misses http:// or https://, add it
        if (!meshPath.includes("http://") && !meshPath.includes("https://")) {
            meshPath = "http://" + meshPath;
        }
        loadedMesh = await loadAssetMesh(scene, meshPath, filename=meshName, bugger=ParamsManager.debug);
    } else {
        loadedMesh = await loadAssetMesh(scene, basePathMesh, filename="glassesGuyNew.glb", bugger=ParamsManager.debug);
    }
    // loadedMesh = await loadAssetMesh(scene, basePathMesh, filename="Nemu.glb", bugger=ParamsManager.debug);
    // loadedMesh = await loadAssetMesh(scene);

    // for all meshes in disable frustum culling
    loadedMesh.fetched.meshes.forEach(mesh => {
        mesh.alwaysSelectAsActiveMesh = true;
    });

    // Make sure we have a boneLock, fetch it from the name Neck or neck
    if (!boneLock) {
        var bone = loadedMesh.fetched.skeletons[0].bones.find(bone => (bone.name === "Neck" || bone.name === "neck"));

        if (bone) {
            boneLock = bone._index;
        } else {
            boneLock = 4;
        }

        ParamsManager.boneLock = boneLock;
    }


    // Create first camera, then access it through the singleton
    var camera = CameraController.getInstance(scene, canvas);
    camera.lowerRadiusLimit = 0.5;
    camera.upperRadiusLimit = 6;
    camera.inputs.removeByType("ArcRotateCameraKeyboardMoveInput");
    CameraController.setNearPlane(0.1);
    // CameraController.setCameraOnBone(scene, loadedMesh.root, loadedMesh.skeletons[0], boneIndex=boneLock);
    CameraController.setCameraOnBone(scene, loadedMesh.fetched.meshes[1], loadedMesh.skeletons[0], boneIndex=boneLock, visualizeSphere=ParamsManager.debug, setLocalAxis=ParamsManager.debug);
    CameraController.setCameraParams(scene, cameraAngle, cameraAngleBeta, movingCamera);
    createPineapple(scene, basePathMesh, loadedMesh.root);

    // Run the render loop
    engine.runRenderLoop(function () {
        scene.render();
        document.addEventListener("fullscreenchange", () => {
            // console.error("fullscreenchange");
            resizeLogic();
        });
        
        window.addEventListener("resize", () => {
            // console.error("resize");
            resizeLogic();
        });
        
    });

    // Resize the canvas when the window is resized
    window.addEventListener("resize", function () {
        engine.resize();
    });

    AnimationSequencer.setBlending(blending);

    try {
        if (animRotation !== null) {
            // Convert the rotation from degrees to radians
            let rotationY = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.Y, BABYLON.Tools.ToRadians(animRotation));
            
            // Apply the rotation quaternion to the mesh
            loadedMesh.god.rotationQuaternion = rotationY;
        }
    } catch (error) {
        console.error("An error occurred while applying the rotation:", error);
    }

    return [scene, engine, loadedMesh];
}
