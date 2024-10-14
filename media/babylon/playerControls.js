// import '@babylonjs/gui'
// document.addEventListener("fullscreenchange", () => {
//     console.error("fullscreenchange");
//     resizeLogic();
// });

// window.addEventListener("resize", () => {
//     console.error("resize");
//     resizeLogic();
// });

// Flag to check if controls are enabled
let controlsEnabled = true;

function disableControls() {
    controlsEnabled = false;
}

function enableControls() {
    controlsEnabled = true;
}


function resizeLogic() {
    gui.scaleTo(engine.getRenderWidth(), engine.getRenderHeight());
    if (engine.getRenderHeight() >= 580) {
        gui.rootContainer.getChildByName("grid").getChildByName("animSlider").height = "2%";
        // gui.rootContainer.getChildByName("grid").getChildByName("playPause").top = "-3%";
    } else if (engine.getRenderHeight() < 220) {
        gui.rootContainer.getChildByName("grid").getChildByName("animSlider").height = "8%";
        // gui.rootContainer.getChildByName("grid").getChildByName("playPause").top = "-7%";
    } else {
        gui.rootContainer.getChildByName("grid").getChildByName("animSlider").height = "5%";
        // gui.rootContainer.getChildByName("grid").getChildByName("playPause").top = "-5%";
    }

    var percentage = window.innerWidth * 0.06;
    gui.rootContainer.getChildByName("grid").getChildByName("playPause").width = percentage + "px";
    gui.rootContainer.getChildByName("grid").getChildByName("playPause").height = percentage / 2 + "px";
    gui.rootContainer.getChildByName("grid").getChildByName("handTracking").width = percentage + "px";
    gui.rootContainer.getChildByName("grid").getChildByName("handTracking").height = percentage / 2 + "px";
}

function createRootContainer(gui) {
    var rootContainer = new BABYLON.GUI.Grid("grid");
    rootContainer.width = "100%";
    rootContainer.height = "100%";
    gui.addControl(rootContainer);

    return rootContainer;
}

function animSlider(animationGroup, rootContainer, scene) {
    // Remove previous controls
    rootContainer.clearControls();
    console.log("animationGroup: ", animationGroup);

    var currGroup = animationGroup;

    // Add a slider to control the animation
    var slider = new BABYLON.GUI.Slider("animSlider");
    slider.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
    slider.width = "50%";
    // Check if screen too small for slider 2% is minimum
    if (engine.getRenderHeight() >= 580) {
        slider.height = "2%";
    } else if (engine.getRenderHeight() < 220) {
        slider.height = "8%";
    } else {
        slider.height = "5%";
    }
    slider.top = "-5%";
    slider.color = "white";
    slider.thumbWidth = "0%"; // Use percentage for thumb width
    slider.isThumbCircle = true;
    rootContainer.addControl(slider, 1);
    rootContainer.animSlider = slider;
    rootContainer.playing = true;

    slider.onValueChangedObservable.add(function (value) {
        // header.text = ((value) | 0);
        currGroup.goToFrame(value);
        slider.minimum = currGroup.from;
        slider.maximum = currGroup.to;
    });

    slider.onPointerDownObservable.add(() => {
        animationGroup.pause();
    });

    slider.onPointerUpObservable.add(() => {
        if (rootContainer.playing) {
            animationGroup.play();
        }
    });

    scene.onBeforeRenderObservable.add(() => {
        if (currGroup) {
            var ta = currGroup.targetedAnimations;
            if (ta && ta.length) {
                var ra = ta[0].animation.runtimeAnimations;
                if (ra && ra.length) {
                    slider.value = ra[0].currentFrame;
                }
            }
        }
    });
}

function speedControlButton(animationGroup, playSpeedBtn) {
    const speedLevels = [1, 0.1, 0.3, 0.5];
    let currentSpeedIndex = 0;
    const selectedColor = new BABYLON.Color3(1/255, 150/255, 255/255).toHexString();
    const speedColor = new BABYLON.Color3(1/255, 255/255, 150/255).toHexString();

    // Create the clickable button and add the speed icon
    var clickable = new BABYLON.GUI.Button('clickable');
    clickable.width = "40%";
    clickable.height = "80%";
    clickable.background = "transparent";
    clickable.thickness = 0;
    clickable.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;

    var speedImage = new BABYLON.GUI.Image("speedImage", images + "/speed.svg");
    speedImage.width = "100%";
    speedImage.height = "100%";
    speedImage.shadowColor = speedColor;
    speedImage.shadowBlur = 1;
    speedImage.shadowOffsetX = 3;
    speedImage.shadowOffsetY = 2.5;
    clickable.addControl(speedImage);

    var letter = new BABYLON.GUI.TextBlock();
    letter.text = "1";
    letter.color = "white";
    letter.fontSize = "50%";
    letter.resizeToFit = true;
    letter.paddingRight = "10%";
    letter.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
    letter.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
    clickable.addControl(letter);


    // Function to cycle through the speed levels
    function cycleSpeed(direction) {
        if (direction === "next") {
            currentSpeedIndex = (currentSpeedIndex + 1) % speedLevels.length;
        } else if (direction === "prev") {
            currentSpeedIndex = (currentSpeedIndex - 1 + speedLevels.length) % speedLevels.length;
        }
        animationGroup.speedRatio = speedLevels[currentSpeedIndex];
        letter.text = speedLevels[currentSpeedIndex];
        updateSpeedDisplay();
    }

    // Function to update the button appearance based on the current speed
    function updateSpeedDisplay() {
        // Change icon color based on speed level
        speedImage.shadowColor = currentSpeedIndex === 0 ? selectedColor : speedColor;
    }

    // When the button is clicked, change the speed
    clickable.onPointerClickObservable.add(() => cycleSpeed("next"));

    // Add event listener for keyboard shortcuts
    window.addEventListener("keydown", function(event) {
        if (!controlsEnabled) { return; }

        if (event.code === "KeyS") {
            cycleSpeed("next");
            event.preventDefault();
        } else if (event.code === "ArrowRight") {
            cycleSpeed("next");
            event.preventDefault();
        } else if (event.code === "ArrowLeft") {
            cycleSpeed("prev");
            event.preventDefault();
        }
    });

    // Change the color of the button when the mouse hovers over it
    clickable.pointerEnterAnimation = () => {
        speedImage.shadowColor = "white";
    }

    // Change the color of the button when the mouse leaves it
    clickable.pointerOutAnimation = () => {
        updateSpeedDisplay();
    }


    playSpeedBtn.addControl(clickable);

    // Initial update
    updateSpeedDisplay();
}

function pausePlaySpeedButtons(animationGroup, rootContainer) {
    var playColor = new BABYLON.Color3(1/255, 255/255, 150/255).toHexString();
    var pauseColor = new BABYLON.Color3(1/255, 150/255, 255/255).toHexString();

    // Create the button container and set the position of the button based on the window size
    const playSpeedBtn = new BABYLON.GUI.Container("playPause");
    playSpeedBtn.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
    playSpeedBtn.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
    var percentage = window.innerWidth * 0.06;
    playSpeedBtn.width = percentage + "px";
    playSpeedBtn.height = percentage / 2 + "px";
    playSpeedBtn.left = "-15%";
    if (engine.getRenderHeight() >= 580) {
        playSpeedBtn.top = "-3%";
    } else if (engine.getRenderHeight() < 220) {
        playSpeedBtn.top = "-7%";
    } else {
        playSpeedBtn.top = "-5%";
    }
    playSpeedBtn.background = "transparent";

    // Create the clickable button and add the play/pause image to it
    var clickable = new BABYLON.GUI.Button('clickable');
    clickable.width = "40%";
    clickable.height = "80%";
    clickable.background = "transparent";
    clickable.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_LEFT;
    clickable.thickness = 0;

    var playImage = new BABYLON.GUI.Image("playImage", images + "/pause.svg");
    playImage.width = "70%";
    playImage.height = "70%";
    playImage.shadowColor = pauseColor;
    playImage.shadowBlur = 1;
    playImage.shadowOffsetX = 3;
    playImage.shadowOffsetY = 2.5;
    clickable.addControl(playImage);

    // Function to handle play/pause logic
    function togglePlayPause() {
        if (animationGroup.isPlaying) {
            animationGroup.pause();
            rootContainer.playing = false;
            playImage.source = images + "/play.svg";
        } else {
            animationGroup.play();
            rootContainer.playing = true;
            playImage.source = images + "/pause.svg";
        }
    }

    // When the button is clicked, pause or play the animation based on the current state
    clickable.onPointerClickObservable.add(togglePlayPause);

    // Add event listener for the spacebar to toggle play/pause
    window.addEventListener("keydown", function(event) {
        if (!controlsEnabled) { return; }

        if (event.code === "Space") {
            togglePlayPause();
            if (animationGroup.isPlaying) {
                playImage.shadowColor = pauseColor;
            } else {
                playImage.shadowColor = playColor;
            }
            // Prevent default spacebar behavior (e.g., scrolling down)
            event.preventDefault();
        }
    });

    // Change the color of the button when the mouse hovers over it
    clickable.pointerEnterAnimation = () => {
        playImage.shadowColor = "white";
    }

    // Change the color of the button when the mouse leaves it
    clickable.pointerOutAnimation = () => {
        if (animationGroup.isPlaying) {
            playImage.shadowColor = pauseColor;
        } else {
            playImage.shadowColor = playColor;
        }
    }

    playSpeedBtn.addControl(clickable); 

    // Get the speed control button and add it to the same container
    speedControlButton(animationGroup, playSpeedBtn);

    rootContainer.addControl(playSpeedBtn);
}

function handTrackButtons(rootContainer) {
    var handTrackColor = new BABYLON.Color3(1/255, 150/255, 255/255).toHexString();
    var selectedColor = new BABYLON.Color3(1/255, 255/255, 150/255).toHexString();

    const trackHandContainer = new BABYLON.GUI.Container("handTracking");
    trackHandContainer.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
    trackHandContainer.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
    var percentage = window.innerWidth * 0.06;
    trackHandContainer.width = percentage + "px";
    trackHandContainer.height = percentage / 2 + "px";
    trackHandContainer.left = "-5%";

    if (engine.getRenderHeight() >= 580) {
        trackHandContainer.top = "-3%";
    } else if (engine.getRenderHeight() < 220) {
        trackHandContainer.top = "-7%";
    } else {
        trackHandContainer.top = "-5%";
    }
    trackHandContainer.background = "transparent";

    function createClickableButton(name, alignment, boneIndex, letterText) {
        var clickable = new BABYLON.GUI.Button(name);
        clickable.width = "40%";
        clickable.height = "80%";
        clickable.background = "transparent";
        clickable.horizontalAlignment = alignment;
        clickable.thickness = 0;
        trackHandContainer.addControl(clickable);

        var handImage = new BABYLON.GUI.Image(name + "Image", images + "/hand.svg");
        handImage.width = "100%";
        handImage.height = "100%";
        handImage.shadowColor = handTrackColor;
        handImage.shadowBlur = 1;
        handImage.shadowOffsetX = 3;
        handImage.shadowOffsetY = 2.5;
        clickable.addControl(handImage);

        var letter = new BABYLON.GUI.TextBlock();
        letter.text = letterText;
        letter.color = "white";
        letter.fontSize = "50%";
        letter.resizeToFit = true;
        letter.paddingRight = "10%";
        letter.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
        letter.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
        clickable.addControl(letter);

        clickable.pointerEnterAnimation = () => {
            handImage.shadowColor = "white";
        }

        clickable.pointerOutAnimation = () => {
            handImage.shadowColor = (CameraController.trackingHand == boneIndex) ? selectedColor : handTrackColor;
        }

        clickable.onPointerClickObservable.add(() => {
            // If already tracking, untrack the hand
            if (CameraController.trackingHand == boneIndex) {
                CameraController.trackingHand = null;
                CameraController.setCameraOnBone(scene, loadedMesh.fetched.meshes[1], loadedMesh.skeletons[0], ParamsManager.boneLock);
                handImage.shadowColor = handTrackColor;
                CameraController.resetZoom();
                return;
            }
            // If tracking a different hand, switch to the new hand
            else if (CameraController.trackingHand != null && CameraController.trackingHand != boneIndex) {
                var otherHand = trackHandContainer.getChildByName(name == "clickableL" ? 'clickableR' : 'clickableL');
                var otherHandImage = otherHand.getChildByName(name == "clickableL" ? 'clickableRImage' : 'clickableLImage');
                otherHandImage.shadowColor = handTrackColor;
            }
            CameraController.trackingHand = boneIndex;
            CameraController.setCameraOnBone(
                scene, 
                loadedMesh.fetched.meshes[1], 
                loadedMesh.skeletons[0], 
                CameraController.trackingHand ? boneIndex : ParamsManager.boneLock
            );
            CameraController.zoom(1.5);
            handImage.shadowColor = selectedColor;
        });
    }

    // Fetch left and right hand bone indices from EngineController.loadedMesh
    const leftHand = EngineController.loadedMesh.fetched.skeletons[0].bones.find(bone => (bone.name === "LeftHand" || bone.name === "leftHand" || bone.name === "hand.L" || bone.name === "Hand.L"))._index;
    const rightHand = EngineController.loadedMesh.fetched.skeletons[0].bones.find(bone => (bone.name === "RightHand" || bone.name === "rightHand" || bone.name === "hand.R" || bone.name === "Hand.R"))._index;
    createClickableButton('clickableL', BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_LEFT, leftHand, "L");
    createClickableButton('clickableR', BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT, rightHand, "R");

    rootContainer.addControl(trackHandContainer);
}

function hideShowGui(rootContainer, show) {
    if (show == null) {
        rootContainer.isVisible = !rootContainer.isVisible;

        // If the GUI is now invisible, reset the camera to the original position
        if (!rootContainer.isVisible) {
            CameraController.trackingHand = null;
            CameraController.setCameraOnBone(scene, loadedMesh.fetched.meshes[1], loadedMesh.skeletons[0], ParamsManager.boneLock);
        }
        return;
    }

    // If the GUI is now invisible, reset the camera to the original position
    if (!show) {
        CameraController.trackingHand = null;
        CameraController.setCameraOnBone(scene, loadedMesh.fetched.meshes[1], loadedMesh.skeletons[0], ParamsManager.boneLock);
    }

    rootContainer.isVisible = show;
}
