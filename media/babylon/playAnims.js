//Play the animation that is currently loaded
async function playLoadedAnims(scene, loaded) {
    if (scene && loaded) {
        // Initialize animation with standard vars, start frame + 30 frames, end frame - 30 frames
        await initializeAnimationGroups(loaded);

        if (keepAnimating) {
            await playAnimationForever(scene, loaded);
        } else {
            await playAnims(scene, loaded, 0);
        }
    } else {
        console.error("Scene or loaded variables are not set.");
    }
}

async function playAnimationForever(scene, loaded) {
    await playAnims(scene, loaded, 0) // 1 comes from loaded animation of gloss, 0 comes from baked-in animation of avatar.glb
        .then(animationPlayed => {
            if (animationPlayed) {
                // Replay the animation after 1 second timeout and after it stopped
                playAnimationForever(scene, loaded);
            }
        })
        .catch(err => {
            console.error("Error playing animation:", err);
        });
}

// Define an object to encapsulate animation sequencing logic
// That way, we can have the starting and stopping of the animation in this file instead
// of the main file. And we dont need to use a global continueloop variable.
const AnimationSequencer = (function () {
    let continueLoop = false;
    let notSequencing = false;
    let animationGroupFrom = 80;
    let animationGroupTo = 100;
    let blending = true;

    async function startAnimationLoop(basePath, scene, loadedMesh, animations, recording=false, recordingMethod="", keepPlaying=false) {
        continueLoop = true;
        console.log("recording: ", recording);

        // Load and initialize animations
        if (await preloadAndInitializeAnimations(basePath, scene, loadedMesh, animations)) {
            console.log("All animations preloaded and initialized.");
            await hideModal();

            recordingFile = zinArray.join(' ');
            if (recording && recordingMethod == "zin") await startRecording('renderCanvas', recordingFile); // Start recording;

            for (let i = 0; i < loadedMesh.animationGroups.length; i++) {
                if (!continueLoop) break;

                glos = loadedMesh.animationGroups[i].name;

                if (recording && recordingMethod != "zin") {
                    console.log("recording with method: ", recording, recordingMethod, glos);
                    await startRecording('renderCanvas', glos); // Start recording;
                }

                console.log(`Now playing: ${glos}`);
                if (await playAnims(scene, loadedMesh, i)) {
                    console.log(`Playing complete: ${glos}`);
                    // if (recording == "glos") { stopRecording(); }
                    if (recording != "zin") { stopRecording(); }
                } else {
                    console.log(`Failed to play animation: ${glos}`);
                }

                if (i == loadedMesh.animationGroups.length - 1 && keepPlaying == false) {
                    keepAnimating = true;
                    playLoadedAnims(scene, loadedMesh);
                }
                else if (i == loadedMesh.animationGroups.length - 1 && keepPlaying == true) {
                    if (recordingMethod == "zin" && recording) stopRecording();
                    recording = false;
                    //here i want to restart the for loop to 0
                    i = -1;
                    console.log("restart")
                }
            }
        } else {
            console.error("Failed to preload and initialize animations.");
        }

        return;
    }

    function stopAnimationLoop() {
        continueLoop = false;
    }

    function setBlending(value) {
        blending = value;
    }

    function getBlending() {
        return blending;
    }

    function setAnimationGroupFrom(value) {
        animationGroupFrom = value;
    }

    function setAnimationGroupTo(value) {
        animationGroupTo = value;
    }

    function getAnimationGroupFrom() {
        return animationGroupFrom;
    }

    function getAnimationGroupTo() {
        return animationGroupTo;
    }

    function sequencing() {
        return notSequencing;
    }

    function setSequencing(value) {
        notSequencing = value;
    }

    return {
        start: startAnimationLoop,
        stop: stopAnimationLoop,
        setFrom: setAnimationGroupFrom,
        setTo: setAnimationGroupTo,
        getFrom: getAnimationGroupFrom,
        getTo: getAnimationGroupTo,
        getSequencing: sequencing,
        setSequencing: setSequencing,
        getBlending: getBlending,
        setBlending: setBlending
    };
})();

async function initializeAnimationGroups(loadedResults) {
    console.log("Initializing animation groups...");
    loadedResults.animationGroups.forEach(animationGroup => {
        if (!animationGroup.initialized && AnimationSequencer.getSequencing()) {
            // animationGroup.normalize(0, 200); //messes up more
            animationGroup.from += AnimationSequencer.getFrom(); // for estimation of frames, we would need tool of amit to determine mid frame
            animationGroup.to -= AnimationSequencer.getTo();
            animationGroup.initialized = true;
            //console.log("Retargeting animation group: " + animationGroup.name);
            animationGroup.targetedAnimations.forEach((targetedAnimation) => {
                //this can be used to inject seed noise for randomization in coordinates/rotation of bones

                // const newTargetBone = targetSkeleton.bones.filter((bone) => { return bone.name === targetedAnimation.target.name })[0];
                // // //console.log("Retargeting bone: " + target.name + "->" + newTargetBone.name);
                // targetedAnimation.target = newTargetBone ? newTargetBone.getTransformNode() : null;
                // console.log(targetedAnimation.target);
            });
        }
    });
    return true;
}

async function playAnims(scene, loadedResults, animationIndex, loop = false, noRotation = false) {
    // Validate the input parameters
    if (!scene || !loadedResults || !loadedResults.animationGroups || loadedResults.animationGroups.length === 0) {
        console.error("Invalid input. Unable to play animations.");
        return false;
    }

    // Check if eye blink is enabled, play the eye blink animation.
    // Make sure to have this before other animations are played in the case we have morphs to overwrite
    if (ParamsManager.eyeBlink) {
        createBlinkAnimation(EngineController.loadedMesh);
    }

    // Check the range of the animation index
    if (animationIndex >= 0 && animationIndex <= loadedResults.animationGroups.length) {
        // animationIndex -= 1;
        const animationGroup = loadedResults.animationGroups[animationIndex];
        console.error(loadedResults.animationGroups);

        // Only blend if there are more than one animation groups
        if (animationIndex + 1 != loadedResults.animationGroups.length && EngineController.blending) {
            animationGroup.enableBlending = true;
        }
        animationGroup.normalize = true;
        if (!animationGroup.targetedAnimations || animationGroup.targetedAnimations.some(ta => ta.target === null)) {
            console.error("Animation target missing for some animations in the group:", animationGroup.name);
            console.log("Removing targeted animations with missing targets.");
            animationGroup.targetedAnimations = animationGroup.targetedAnimations.filter(ta => ta.target !== null);
        }

        if (ParamsManager.showGui) {
            animSlider(animationGroup, rootContainer, scene);
            pausePlaySpeedButtons(animationGroup, rootContainer);
            handTrackButtons(rootContainer);
            hideShowGui(rootContainer, true);
        }

        return new Promise((resolve) => {
            animationGroup.onAnimationEndObservable.addOnce(() => {
                console.log(`Animation in ${animationGroup.name} has ended.`);
                scene.onBeforeRenderObservable.clear();  // Remove the observer to clean up
                resolve(true);
                if (ParamsManager.returnToIdle && !ParamsManager.startingNewAnim) {
                    stopLoadAndPlayAnimation(basePath + "idle.glb", loop=true, noRotation=true);
                }
            });

            animationGroup.onAnimationGroupEndObservable.addOnce(() => {
                console.log(`AnimationGROUP ${animationGroup.name} has ended.`);
                EngineController.loadedMesh.hips.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.papa.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.opa.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.resetMorphs();
                EngineController.loadedMesh.skeletons[0].returnToRest();
                // EngineController.loadedMesh.hips.position = BABYLON.Vector3.Zero();
                hideShowGui(rootContainer, false);
            });

            animationGroup.onAnimationGroupPlayObservable.addOnce(() => {
                console.log(`AnimationGROUP ${animationGroup.name} has started.`);
                EngineController.loadedMesh.hips.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.papa.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.opa.rotationQuaternion = BABYLON.Quaternion.Identity();
                EngineController.loadedMesh.resetMorphs();
                console.error(EngineController.loadedMesh.morphTargetManagers);
                // EngineController.loadedMesh.hips.position = BABYLON.Vector3.Zero();

                // In animationGroup.targetedAnimations get target Hips
                let animHipsRotation;
                animationGroup.targetedAnimations.every(x => {
                    if (x.target.name === EngineController.loadedMesh.hips.name && x.animation.targetProperty === "rotationQuaternion") {
                        animHipsRotation = x.animation;
                        return false;
                    }

                    return true;
                });

                if (!noRotation) {
                    // Get the initial rotation of the hips of the first frame of the animation and orient the mesh upwards
                    let initialRotation = animHipsRotation.getKeys().at(0).value;
                    const inverse = initialRotation.negateInPlace();

                    // Compare currentRotation with inverseRotation
                    const epsilon = 0.004; // Threshold for considering rotations as "equal"
                    if (Math.abs(initialRotation.x - inverse.x) > epsilon ||
                        Math.abs(initialRotation.y - inverse.y) > epsilon ||
                        Math.abs(initialRotation.z - inverse.z) > epsilon ||
                        Math.abs(initialRotation.w - inverse.w) > epsilon) {

                        // If the current rotation is not already the inverse, apply the inverse rotation
                        EngineController.loadedMesh.papa.rotationQuaternion = inverse;

                        // Flip the papa object around the z axis
                        let tmp = EngineController.loadedMesh.papa.rotationQuaternion;
                        EngineController.loadedMesh.papa.rotationQuaternion = new BABYLON.Quaternion(-tmp.x, -tmp.y, tmp.z, tmp.w);
                    }
                }

                // wait 0.1 seconds for the animation to start playing then rotate opa or not TODO: change this to a better solution without a wait
                new Promise(resolve => {
                    setTimeout(() => {
                        resolve();
                    }, 100);
                }).then(() => {
                    // Refocus the camera
                    // Check coordinate system by looking if hips are pointing forward
                    const hips = EngineController.loadedMesh.hips.rotationQuaternion;
                    // Check y rotation of hips
                    const hipsEuler = hips.toEulerAngles();
                    console.log(hips);
                    console.log("Hips rotation in degrees: ", hipsEuler.scale(180/Math.PI).y);
                    // Floor the y rotation to the nearest 90 degrees
                    let zRotation = Math.abs(Math.round(hipsEuler.z * 2 / Math.PI) * Math.PI / 2);
                    console.log("Floored z rotation in degrees: ", zRotation * 180 / Math.PI);
                    // Check if the y rotation is close to 180 degrees, if so rotate opa 180 degrees over the y axis
                    if (Math.abs(zRotation - Math.PI) >= 0.1) {
                        console.log("Rotating opa 180 degrees.");
                        EngineController.loadedMesh.opa.rotationQuaternion = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.Y, Math.PI);
                    }
                    console.error("zRotation: ", zRotation);
                });
            });

            // Play the animation
            if (animationGroup === null) { 
                console.error("Animation group is null.");
            } else if (animationGroup.from === null || animationGroup.to === null) {
                // animationGroup.start(false, 1.0, loop=loop);
                animationGroup.play(loop);
            } else {
                // animationGroup.start(false, 1.0, animationGroup.from, animationGroup.to, loop=loop);
                animationGroup.play(loop);
            }
            // animationGroup.start();
        });
    } else {
        console.error("Invalid animation index:", animationIndex, "for loadedResults.animationGroups.length:", loadedResults.animationGroups.length, "animations.");
        return false;
    }
}

function stopAnims(scene, loadedResults) {
    // Validate the input parameters
    if (!scene) {
        console.error("Scene is not set.");
        console.log(scene);
        return false;
    }

    if (!loadedResults) {
        console.error("loadedResults is not set.");
        console.log(loadedResults);
        return false;
    }

    if (!loadedResults.animationGroups || loadedResults.animationGroups.length === 0) {
        console.error("AnimGroups are not present and therefore already stopped.");
        console.log(loadedResults.animationGroups);
        console.log(loadedResults.animationGroups.length);
        return true;
    }

    removeEyeBlinkAnimation(EngineController.loadedMesh);

    // Stop animations on all meshes
    loadedResults.fetched.meshes.forEach(mesh => {
        scene.stopAnimation(mesh);
    });

    // If you need to stop animation groups as well
    loadedResults.animationGroups.forEach(animationGroup => {
        animationGroup.stop();  // Stops the animation group from playing
        // For each animation in the group stop it as well
        animationGroup.targetedAnimations.forEach(targetedAnimation => {
            scene.stopAnimation(targetedAnimation.target);
        });
    });

    scene.animationGroups.forEach(animationGroup => {
        animationGroup.stop();  // Stops the animation group from playing
    });

    console.log("All animations have been stopped.");
    return true;
}


async function preloadAndInitializeAnimations(basePath, scene, loaded, animations) {
    if (animations === null || animations.length === 0) {
        console.error("No animations to preload.");
        return false;
    }

    console.log(animations)
    for (let animName of animations) {
        console.log(`Preloading animation: ${animName}`);
        //add animName to modal 
        $('#errorModalLabel').append(`<p>${animName}</p>`);
        let result = await getAnims(basePath, scene, loaded, animName);
        if (!result) {
            console.error(`Failed to preload animation: ${animName}`);
            return false;
        }
    }
    await initializeAnimationGroups(loaded);  // Initialize all at once after loading

    return true;
}

function signFetcher() {
    disableControls();
    $("#glossModal").modal("show")
}

function stopLoadAndPlayAnimation(path, loop = false, noRotation = false) {
    console.log(path);
    console.log(EngineController.scene);

    // Check if the path ends with 'idle.glb'
    if (!path.endsWith('idle.glb')) {
        ParamsManager.startingNewAnim = true;
    }

    // Stop the currently playing animation
    stopAnims(EngineController.scene, EngineController.loadedMesh);

    // Remove the currently loaded animation
    removeAnims(EngineController.scene, loadedMesh);
    removeAnims(EngineController.scene, scene);

    // Fetch the new animation and play
    getAnims(path, EngineController.scene, EngineController.loadedMesh, ParamsManager.glos, ParamsManager.gltf, fullPath = true)
        .then(anim => {
            console.log("getAnims returned: ", anim);
            anim.animationGroups.push(retargetAnimWithBlendshapes(EngineController.loadedMesh, anim.animationGroups[0], "freshAnim"));
            // console.log(anim.animationGroups);
            keepOnlyAnimationGroup(EngineController.scene, anim, EngineController.loadedMesh, "freshAnim");
            EngineController.loadedMesh.animationGroups = anim.animationGroups;
            EngineController.scene.animationGroups = anim.animationGroups;


            playAnims(EngineController.scene, EngineController.loadedMesh, 0, loop, noRotation=noRotation);
            ParamsManager.startingNewAnim = false;
            
            // wait for the EngineController.loadedMesh.animationGroups[0].isPlaying to start playing then refocus camera
            new Promise(resolve => {
                const checkPlaying = setInterval(() => {
                    if (EngineController.loadedMesh.animationGroups[0].isPlaying) {
                        clearInterval(checkPlaying);
                        resolve();
                    }
                }, 1000);
            }).then(() => {            
                // Code to execute after the animation starts playing
                // Refocus the camera
                // CameraController.reFocusCamera();
            });

        })
        .catch(error => {
            console.error('Failed to load animations:', error);
            ParamsManager.startingNewAnim = false;
            if (ParamsManager.returnToIdle) {
                stopLoadAndPlayAnimation(basePath + "idle.glb", loop=true, noRotation=true);
            }
            $('#errorModal2 .modal-body').html(`<p>${error}</p>`);
            $('#errorModal2').modal('show').css('z-index', 1065);
            $('.modal-backdrop').css('z-index', 1064);
        });
}

// function getClosestAxis(quat) {
//     if (!quat) {
//         console.error("Invalid quaternion passed to getClosestAxis.");
//         return BABYLON.Quaternion.Identity(); // Return a default identity quaternion
//     }

//     // Apply the initial rotation to the world up vector (0, 1, 0)
//     let transformedUp;
//     try {
//         console.log("A");

//         transformedUp = BABYLON.Vector3.TransformCoordinates(BABYLON.Vector3.Up(), quat);
//     } catch (error) {
//         console.log("B");

//         console.error("Failed to transform coordinates:", error);
//         return BABYLON.Quaternion.Identity();
//     }

//     // Find the axis with the largest component in the transformed up vector
//     let absX = Math.abs(transformedUp.x);
//     let absY = Math.abs(transformedUp.y);
//     let absZ = Math.abs(transformedUp.z);

//     // Identify the closest world axis
//     let closestAxis;
//     if (absY >= absX && absY >= absZ) {
//         // Closest to Y-axis
//         closestAxis = BABYLON.Axis.Y;
//     } else if (absX >= absY && absX >= absZ) {
//         // Closest to X-axis
//         closestAxis = BABYLON.Axis.X;
//     } else {
//         // Closest to Z-axis
//         closestAxis = BABYLON.Axis.Z;
//     }

//     // Create a quaternion that represents alignment with the closest axis
//     let alignedQuat = BABYLON.Quaternion.Identity();
//     if (closestAxis === BABYLON.Axis.X) {
//         alignedQuat = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.X, Math.PI / 2);
//     } else if (closestAxis === BABYLON.Axis.Y) {
//         alignedQuat = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.Y, 0); // Identity already represents this
//     } else if (closestAxis === BABYLON.Axis.Z) {
//         alignedQuat = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.Z, Math.PI / 2);
//     }

//     return alignedQuat;
// }

/*
The following functions are deprecated and should not be used.
We are fetching this information on load of the model itself.

// Get a list of loaded animations
function getLoadedAnimations(loadedResults) {
    const loadedAnimations = [];

    // Store each animation group
    loadedResults.animationGroups.forEach(animationGroup => {
        loadedAnimations.push(animationGroup);
    });

    return loadedAnimations;
}

// Get a list of loaded meshes
function getLoadedMeshes(loadedResults) {
    const loadedMeshes = [];

    // Store each mesh
    for (let mesh in loadedResults.meshes) {
        loadedMeshes.push(loadedResults.meshes[mesh]);
    }

    return loadedMeshes;
}
*/
