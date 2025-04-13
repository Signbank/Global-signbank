function onboardAnimation() {
    // Create an image and add it to the GUI
    const fingerImage = new BABYLON.GUI.Image("finger", images + "/finger.svg");
    var percentage = window.innerWidth * 0.06;
    fingerImage.width = percentage + "px";
    fingerImage.height = percentage + "px";
    fingerImage.horizontalAlignment = BABYLON.GUI.Control.HORIZONTAL_ALIGNMENT_CENTER;
    fingerImage.verticalAlignment = BABYLON.GUI.Control.VERTICAL_ALIGNMENT_CENTER;
    gui.addControl(fingerImage);

    // Create the shake animation
    const dragAnimation = new BABYLON.Animation(
        "dragAnimation",
        "left",
        30,
        BABYLON.Animation.ANIMATIONTYPE_FLOAT,
        BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE
    );

    // Keyframes for the shaking effect
    const shakeKeys = [];
    shakeKeys.push({ frame: 0, value: 200 });
    shakeKeys.push({ frame: 40, value: -200 });
    dragAnimation.setKeys(shakeKeys);

    // Apply the easing function
    const easingFunction = new BABYLON.QuadraticEase();
    easingFunction.setEasingMode(BABYLON.EasingFunction.EASINGMODE_EASEINOUT);
    dragAnimation.setEasingFunction(easingFunction);

    // Create the rotation animation
    const rotateAnimation = new BABYLON.Animation(
        "rotateAnimation",
        "rotation",
        30,
        BABYLON.Animation.ANIMATIONTYPE_FLOAT,
        BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
    );

    // Keyframes for the rotation effect
    const rotateKeys = [];
    rotateKeys.push({ frame: 0, value: BABYLON.Tools.ToRadians(15) }); // Start with a slight rotation
    rotateKeys.push({ frame: 20, value: BABYLON.Tools.ToRadians(15) });  // Straighten by halfway
    rotateKeys.push({ frame: 40, value: BABYLON.Tools.ToRadians(0) });  // Remain straight

    rotateAnimation.setKeys(rotateKeys);

    // Apply the easing function to the rotation animation
    rotateAnimation.setEasingFunction(easingFunction);

    // Create the fade-in and fade-out animation (opacity)
    const fadeAnimation = new BABYLON.Animation(
        "fadeAnimation",
        "alpha",
        30,
        BABYLON.Animation.ANIMATIONTYPE_FLOAT,
        BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
    );
    
    const fadeKeys = [];
    fadeKeys.push({ frame: 0, value: 0 });   // Start fully transparent
    fadeKeys.push({ frame: 10, value: 1 });  // Fully visible by frame 10
    fadeKeys.push({ frame: 30, value: 1 });  // Stay fully visible until frame 30
    fadeKeys.push({ frame: 40, value: 0 });  // Fade out by frame 40

    fadeAnimation.setKeys(fadeKeys);

    
    // Apply and start the animation
    fingerImage.animations = [dragAnimation, rotateAnimation, fadeAnimation];
    scene.beginAnimation(fingerImage, 0, 40, false, 1, function() {
        // Remove the image after the animation is complete
        gui.removeControl(fingerImage);
    });
}
