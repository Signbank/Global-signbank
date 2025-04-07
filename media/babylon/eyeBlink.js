function createBlinkAnimation(loadedResults) {
    if (!loadedResults) {
        console.log("loadedResults is null");
    }

    console.log("Creating blink animation...");

    function createBlinkAnimation(morph1, morph2) {
        const blinkAnimation = new BABYLON.Animation(
            "blinkAnimation",
            "influence",
            30, // FPS
            BABYLON.Animation.ANIMATIONTYPE_FLOAT,
            BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE
        );

        // Keyframes for the blink animation with varied timing
        const blinkKeys = [];

        // Initial state: eyes open
        blinkKeys.push({ frame: 0, value: 0 });

        // First blink (quick)
        blinkKeys.push({ frame: 10, value: 0 });   // Eyes closed
        blinkKeys.push({ frame: 15, value: 1 });   // Eyes closed
        blinkKeys.push({ frame: 20, value: 0 });   // Eyes open

        // Pause (slightly longer)
        blinkKeys.push({ frame: 140, value: 0 });   // Eyes open

        // Double blink
        blinkKeys.push({ frame: 145, value: 0 });   // Eyes Open
        blinkKeys.push({ frame: 150, value: 1 });   // Eyes closed
        blinkKeys.push({ frame: 155, value: 0 });   // Eyes open
        blinkKeys.push({ frame: 170, value: 0 });   // Eyes open
        blinkKeys.push({ frame: 175, value: 1 });   // Eyes closed
        blinkKeys.push({ frame: 180, value: 0 });   // Eyes open
        
        // Long pause
        blinkKeys.push({ frame: 280, value: 0 });   // Eyes open

        blinkAnimation.setKeys(blinkKeys);
        
        // Apply the animation to both eye morph targets
        morph1.animations = [blinkAnimation];
        morph2.animations = [blinkAnimation];
    }

    loadedResults.morphTargetManagers.forEach(morphTargetManager => {
        const morph1 = morphTargetManager.getTarget(57);
        const morph2 = morphTargetManager.getTarget(58);
        createBlinkAnimation(morph1, morph2);

        // Play the blink animation
        scene.beginAnimation(morph1, 0, morph1.animations[0].getKeys().at(-1).frame, true);
        scene.beginAnimation(morph2, 0, morph2.animations[0].getKeys().at(-1).frame, true);
    });
}

function removeEyeBlinkAnimation(loadedResults) {
    console.log("Removing eye blink animation...");

    // Stop and remove the blink animation called blinkAnimation manually from both eye morph targets
    loadedResults.morphTargetManagers.forEach(morphTargetManager => {
        const morph1 = morphTargetManager.getTarget(57);
        const morph2 = morphTargetManager.getTarget(58);

        // Stop the animation
        scene.stopAnimation(morph1);
        scene.stopAnimation(morph2);

        // Remove the animation
        morph1.animations = [];
        morph2.animations = [];
    });
}