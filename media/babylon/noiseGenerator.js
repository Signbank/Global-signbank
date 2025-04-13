async function loadAndModifyAnimation(skeleton, mesh, noiseFactor, animationGroup) {
    // Load the animation
    
    animationGroup.stop();  // Stop the animation if it's playing

    // Modify the animation keyframes
    skeleton.bones.forEach(bone => {
        bone.animations.forEach(animation => {
            if (animation.targetProperty.includes("rotationQuaternion")) {
                for (let key of animation.getKeys()) {
                    // Generate random rotation offsets
                    let randomYaw = Math.random() * noiseFactor;
                    let randomPitch = Math.random() * noiseFactor;
                    let randomRoll = Math.random() * noiseFactor;
                    let randomQuaternion = BABYLON.Quaternion.RotationYawPitchRoll(randomYaw, randomPitch, randomRoll);

                    // Combine the original quaternion with the new random quaternion
                    let originalQuaternion = key.value;
                    let combinedQuaternion = originalQuaternion.multiply(randomQuaternion);
                    key.value = combinedQuaternion;
                }
            }
        });
    });

    // Play the modified animation
    animationGroup.start(true, 1.0, animationGroup.from, animationGroup.to, false);
}
