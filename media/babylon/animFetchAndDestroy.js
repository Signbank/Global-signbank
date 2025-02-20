// Import animations for BabylonJS
async function getAnims(basePath, scene, loadedResults, glos, gltf, fullPath = false) {
    if (!scene) {
        console.error("Scene is undefined. Unable to import animations.");
        return false;
    }

    if (fullPath === false) {
        console.log("Loading animations for " + glos + "...");
    } else {
        console.log("Loading animations for " + basePath + "...");
    }
    // Import animations asynchronously without auto-starting them
    try {
        if (!basePath) {
            console.log("basePath is null");
        }

        if (!scene) {
            console.log("scene is null");
        }

        if (!loadedResults) {
            console.log("loadedResults is null");
        }

        if (!glos) {
            console.log("glos is null");
        }

        const result = {
            fetched: await BABYLON.SceneLoader.ImportAnimationsAsync(
                basePath,
                (fullPath === false ? glos + (gltf == 1 ? ".gltf" : ".glb") : ""),
                scene,
                false,
                BABYLON.SceneLoaderAnimationGroupLoadingMode.NoSync,
                null),
            animationGroups: [],
            lockRotHips: function () {
                // for the anim, disable the hips rotationQuaternion animation and rotate the mesh 180 degrees
                this.animationGroups.forEach(group => {
                    if (group !== null) {
                        group.targetedAnimations.forEach(targetedAnim => {
                            if (targetedAnim.target !== null && targetedAnim.animation !== null) {
                                if (targetedAnim.target.name === "Hips") {
                                    if (targetedAnim.animation.targetProperty === "rotationQuaternion") {
                                        targetedAnim.animation._keys.forEach(key => {
                                            key.value.x = 0;
                                            key.value.y = 0;
                                            key.value.z = 1;
                                        });

                                        console.log("Hips rotation disabled.");
                                    }
                                }
                            }
                        });
                    }
                });
            }
        };

        if (!result.fetched || !result.fetched.animationGroups || result.fetched.animationGroups.length === 0) {
            console.error("No animations found or unable to load animations.");
            return false;
        }

        // Find all animation groups, makes accessing it later easier
        for (animGroup of result.fetched.animationGroups) {
            result.animationGroups.push(animGroup);
        }

        // make name of last fetched group the glos name
        const lastIndex = result.animationGroups.length - 1;
        result.animationGroups[lastIndex].name = glos;

        // // Empty the animationGroups array in loadedResults
        // loadedResults.animationGroups = [];
        // lastIndex = result.animationGroups.length - 1;
        // result.animationGroups[lastIndex].glos = glos;

        // Add animations to the loadedResults's animation group
        loadedResults.animationGroups = result.animationGroups;
        console.log("Animations loaded for " + (fullPath ? basePath : glos));

        if (ParamsManager.lockRot === true) {
            result.lockRotHips();
        }

        return result;
    } catch (error) {
        console.error("Failed to load animations:", error);
        return null;
    }
}

// Keep only a single animation group
// This function is not done yet, we cant remove animation groups while looping over the groups
function keepOnlyAnimationGroup(scene, animAsset, loadedMesh, groupName = "anim") {
    function iterateAndDestroyAnimationGroups(animationGroups) {
        // Remove all animation groups except the one with the specified name
        for (let i = 0; i < animationGroups.length; i++) {
            if (animationGroups[i] == null) { continue; }

            if (animationGroups[i].name !== groupName) {
                console.log("Removing animation group: " + animationGroups[i].name);
                animationGroups[i].dispose();
                animationGroups[i] = null;
            }
        }
    }

    iterateAndDestroyAnimationGroups(scene.animationGroups);
    iterateAndDestroyAnimationGroups(animAsset.animationGroups);
    iterateAndDestroyAnimationGroups(loadedMesh.animationGroups);

    // After removing references, make sure that the array is cleaned up
    scene.animationGroups = scene.animationGroups.filter((obj) => obj !== null);
    animAsset.animationGroups = animAsset.animationGroups.filter((obj) => obj !== null);
    loadedMesh.animationGroups = loadedMesh.animationGroups.filter((obj) => obj !== null);
}

function removeAnims(scene, animHolder) {
    console.log("Removing animations...");
    // Validate the input parameters
    if (!scene) {
        console.error("Scene is undefined. Unable to remove animations.");
        return false;
    }

    if (!animHolder) {
        console.error("animHolder is undefined. Unable to remove animations.");
        return false;
    }

    if (!animHolder.animationGroups || animHolder.animationGroups.length === 0) {
        console.error("No animation groups found and therefore already removed.");
        return true;
    }

    // remove all animations from the loaded mesh
    animHolder.animationGroups.forEach(animationGroup => {
        scene.stopAnimation(animationGroup);
        animationGroup.dispose();
        animationGroup = null;
    });

    // Remove all animations from the scene
    scene.animationGroups.forEach(animationGroup => {
        scene.stopAnimation(animationGroup);
        animationGroup.dispose();
        animationGroup = null;
    });

    animHolder.animationGroups = null;
    scene.animationGroups = null;
    animHolder.animationGroups = [];
    scene.animationGroups = [];

    console.log("All animations have been removed.");
    return true;
}

//module.exports = { getAnims, keepOnlyAnimationGroup, removeAnims };
