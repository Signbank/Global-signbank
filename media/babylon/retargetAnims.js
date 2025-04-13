/*
    Function: retargetAnimWithBlendshapes

    Description:
    This function takes a target mesh and an animation group and retargets the animation group
    to the target mesh. Most importantly, it will also retarget the animation group to the blendshapes
    which babylon does not do by default.

    Parameters:
    - targetMeshAsset: The mesh to retarget the animation to.
    - animGroup: The animation group to retarget.
    - cloneName: The name of the cloned animation group.

    Returns:
    Void, but the animation group will be retargeted to the target mesh.
    And we are able to play this animation group on the target mesh through the scene object.
*/
function retargetAnimWithBlendshapes(targetMeshAsset, animGroup, cloneName = "anim") {
    console.log("Retargeting animation to target mesh...");

    var morphName = null;
    var curMTM = 0;
    var morphIndex = 0;
    var mtm;

    return animGroup.clone(cloneName, (target) => {
        if (!target) {
            console.log("No target.");
            return null;
        }

        // First set all bone targets to the linkedTransformNode
        let idx = targetMeshAsset.skeletons[0].getBoneIndexByName(target.name);
        var targetBone = targetMeshAsset.skeletons[0].bones[idx];
        if (targetBone) {
            return targetBone._linkedTransformNode;
        }

        // Iterate over morphManagers if we don't have a new morph target
        // Otherwise reset the index
        if (morphName !== target.name) {
            curMTM = 0;
            morphName = target.name;
        }

        // If we don't have bones anymore, we can assume we are in the morph target section
        morphIndex = getMorphTargetIndex(targetMeshAsset.morphTargetManagers[curMTM], target.name);

        // Sometimes a mesh has extra bits of clothing like glasses, which are not part of the morph targets.
        // Because we don't know the order of the morph targets, we need to copy these values to the previous one.
        if (morphIndex === -1) {
            if (!mtm) { return null; }
            else { return mtm; }
        }

        mtm = targetMeshAsset.morphTargetManagers[curMTM].getTarget(morphIndex);
        curMTM++;

        return mtm;
    });
}

// Helper function to get the morph target index, since babylon only provides
// morph targets through the index. Which follow GLTF standards but is not useful for us.
function getMorphTargetIndex(morphTargetManager, targetName) {
    if (!morphTargetManager) {
        console.error("Morph target manager not found.");
        return -1;
    }

    for (var i = 0; i < morphTargetManager.numTargets; i++) {
        if (morphTargetManager.getTarget(i).name === targetName) {
            return i;
        }
    }

    return -1;
}

/*
    The following functions work, but are not used in the current implementation.
    They are kept here for future reference.
*/

// Helper function that takes a blendshape target name, and returns the value of a json object
// that contains the blendshape targets.
// function getBlendshapeValue(blendshapeTargetName, blendshapeValues) {
//     return blendshapeValues[blendshapeTargetName];
//     // for (var i = 0; i < blendshapeValues.length; i++) {
//     //     if (blendshapeValues[i].name === blendshapeTargetName) {
//     //         return blendshapeValues[i].value;
//     //     }
//     // }

//     // return null;
// }

// // Helper function to fetch JSON data from a file
// function fetchJSONData(filePath) {
//     return fetch(filePath)
//         .then(response => response.json())
//         .then(data => {
//             console.log(data);
//             return data;
//         })
//         .catch(error => {
//             console.error('There was a problem with your fetch operation:', error);
//         });
// }

// function glassesGuyMap() {
//     return {
//         "morphTarget0": "glassesGuy_mesh_0_23_MorphTarget",
//         "morphTarget1": "glassesGuy_mesh_0_25_MorphTarget",
//         "morphTarget2": "glassesGuy_mesh_0_27_MorphTarget",
//         "morphTarget3": "glassesGuy_mesh_0_29_MorphTarget",
//         "morphTarget4": "glassesGuy_mesh_1_24_MorphTarget",
//         "morphTarget5": "glassesGuy_mesh_1_26_MorphTarget",
//         "morphTarget6": "glassesGuy_mesh_1_28_MorphTarget",
//         "morphTarget7": "glassesGuy_mesh_1_30_MorphTarget",
//         "morphTarget8": "glassesGuy_mesh_2_0_MorphTarget",
//         "morphTarget9": "glassesGuy_mesh_2_1_MorphTarget",
//         "morphTarget10": "glassesGuy_mesh_2_2_MorphTarget",
//         "morphTarget11": "glassesGuy_mesh_2_3_MorphTarget",
//         "morphTarget12": "glassesGuy_mesh_2_4_MorphTarget",
//         "morphTarget13": "glassesGuy_mesh_2_5_MorphTarget",
//         "morphTarget14": "glassesGuy_mesh_2_6_MorphTarget",
//         "morphTarget15": "glassesGuy_mesh_2_7_MorphTarget",
//         "morphTarget16": "glassesGuy_mesh_2_8_MorphTarget",
//         "morphTarget17": "glassesGuy_mesh_2_9_MorphTarget",
//         "morphTarget18": "glassesGuy_mesh_2_10_MorphTarget",
//         "morphTarget19": "glassesGuy_mesh_2_11_MorphTarget",
//         "morphTarget20": "glassesGuy_mesh_2_12_MorphTarget",
//         "morphTarget21": "glassesGuy_mesh_2_13_MorphTarget",
//         "morphTarget22": "glassesGuy_mesh_2_14_MorphTarget",
//         "morphTarget23": "glassesGuy_mesh_2_15_MorphTarget",
//         "morphTarget24": "glassesGuy_mesh_2_16_MorphTarget",
//         "morphTarget25": "glassesGuy_mesh_2_17_MorphTarget",
//         "morphTarget26": "glassesGuy_mesh_2_18_MorphTarget",
//         "morphTarget27": "glassesGuy_mesh_2_19_MorphTarget",
//         "morphTarget28": "glassesGuy_mesh_2_20_MorphTarget",
//         "morphTarget29": "glassesGuy_mesh_2_21_MorphTarget",
//         "morphTarget30": "glassesGuy_mesh_2_22_MorphTarget",
//         "morphTarget31": "glassesGuy_mesh_2_23_MorphTarget",
//         "morphTarget32": "glassesGuy_mesh_2_24_MorphTarget",
//         "morphTarget33": "glassesGuy_mesh_2_25_MorphTarget",
//         "morphTarget34": "glassesGuy_mesh_2_26_MorphTarget",
//         "morphTarget35": "glassesGuy_mesh_2_27_MorphTarget",
//         "morphTarget36": "glassesGuy_mesh_2_28_MorphTarget",
//         "morphTarget37": "glassesGuy_mesh_2_29_MorphTarget",
//         "morphTarget38": "glassesGuy_mesh_2_30_MorphTarget",
//         "morphTarget39": "glassesGuy_mesh_2_31_MorphTarget",
//         "morphTarget40": "glassesGuy_mesh_2_32_MorphTarget",
//         "morphTarget41": "glassesGuy_mesh_2_33_MorphTarget",
//         "morphTarget42": "glassesGuy_mesh_2_34_MorphTarget",
//         "morphTarget43": "glassesGuy_mesh_2_35_MorphTarget",
//         "morphTarget44": "glassesGuy_mesh_2_36_MorphTarget",
//         "morphTarget45": "glassesGuy_mesh_2_37_MorphTarget",
//         "morphTarget46": "glassesGuy_mesh_2_38_MorphTarget",
//         "morphTarget47": "glassesGuy_mesh_2_39_MorphTarget",
//         "morphTarget48": "glassesGuy_mesh_2_40_MorphTarget",
//         "morphTarget49": "glassesGuy_mesh_2_41_MorphTarget",
//         "morphTarget50": "glassesGuy_mesh_2_42_MorphTarget",
//         "morphTarget51": "glassesGuy_mesh_2_43_MorphTarget",
//         "morphTarget52": "glassesGuy_mesh_2_44_MorphTarget",
//         "morphTarget53": "glassesGuy_mesh_2_45_MorphTarget",
//         "morphTarget54": "glassesGuy_mesh_2_46_MorphTarget",
//         "morphTarget55": "glassesGuy_mesh_2_47_MorphTarget",
//         "morphTarget56": "glassesGuy_mesh_2_48_MorphTarget",
//         "morphTarget57": "glassesGuy_mesh_2_50_MorphTarget",
//         "morphTarget58": "glassesGuy_mesh_2_51_MorphTarget",
//         "morphTarget59": "glassesGuy_mesh_3_9_MorphTarget",
//         "morphTarget60": "glassesGuy_mesh_3_10_MorphTarget",
//         "morphTarget61": "glassesGuy_mesh_3_11_MorphTarget",
//         "morphTarget62": "glassesGuy_mesh_3_34_MorphTarget",
//         "morphTarget63": "glassesGuy_mesh_3_49_MorphTarget",
//         "morphTarget64": "glassesGuy_mesh_5_0_MorphTarget",
//         "morphTarget65": "glassesGuy_mesh_5_1_MorphTarget",
//         "morphTarget66": "glassesGuy_mesh_6_0_MorphTarget",
//         "morphTarget67": "glassesGuy_mesh_6_1_MorphTarget",
//         "morphTarget68": "glassesGuy_mesh_7_0_MorphTarget",
//         "morphTarget69": "glassesGuy_mesh_7_1_MorphTarget"
//     };
// }
// function NPMGlassesGuyMap() {
//         return {
//             "glassesGuy_mesh_0_23_MorphTarget": "morphTarget0",
//             "glassesGuy_mesh_0_25_MorphTarget": "morphTarget1",
//             "glassesGuy_mesh_0_27_MorphTarget": "morphTarget2",
//             "glassesGuy_mesh_0_29_MorphTarget": "morphTarget3",
//             "glassesGuy_mesh_1_24_MorphTarget": "morphTarget4",
//             "glassesGuy_mesh_1_26_MorphTarget": "morphTarget5",
//             "glassesGuy_mesh_1_28_MorphTarget": "morphTarget6",
//             "glassesGuy_mesh_1_30_MorphTarget": "morphTarget7",
//             "glassesGuy_mesh_2_0_MorphTarget": "morphTarget8",
//             "glassesGuy_mesh_2_1_MorphTarget": "morphTarget9",
//             "glassesGuy_mesh_2_2_MorphTarget": "morphTarget10",
//             "glassesGuy_mesh_2_3_MorphTarget": "morphTarget11",
//             "glassesGuy_mesh_2_4_MorphTarget": "morphTarget12",
//             "glassesGuy_mesh_2_5_MorphTarget": "morphTarget13",
//             "glassesGuy_mesh_2_6_MorphTarget": "morphTarget14",
//             "glassesGuy_mesh_2_7_MorphTarget": "morphTarget15",
//             "glassesGuy_mesh_2_8_MorphTarget": "morphTarget16",
//             "glassesGuy_mesh_2_9_MorphTarget": "morphTarget17",
//             "glassesGuy_mesh_2_10_MorphTarget": "morphTarget18",
//             "glassesGuy_mesh_2_11_MorphTarget": "morphTarget19",
//             "glassesGuy_mesh_2_12_MorphTarget": "morphTarget20",
//             "glassesGuy_mesh_2_13_MorphTarget": "morphTarget21",
//             "glassesGuy_mesh_2_14_MorphTarget": "morphTarget22",
//             "glassesGuy_mesh_2_15_MorphTarget": "morphTarget23",
//             "glassesGuy_mesh_2_16_MorphTarget": "morphTarget24",
//             "glassesGuy_mesh_2_17_MorphTarget": "morphTarget25",
//             "glassesGuy_mesh_2_18_MorphTarget": "morphTarget26",
//             "glassesGuy_mesh_2_19_MorphTarget": "morphTarget27",
//             "glassesGuy_mesh_2_20_MorphTarget": "morphTarget28",
//             "glassesGuy_mesh_2_21_MorphTarget": "morphTarget29",
//             "glassesGuy_mesh_2_22_MorphTarget": "morphTarget30",
//             "glassesGuy_mesh_2_23_MorphTarget": "morphTarget31",
//             "glassesGuy_mesh_2_24_MorphTarget": "morphTarget32",
//             "glassesGuy_mesh_2_25_MorphTarget": "morphTarget33",
//             "glassesGuy_mesh_2_26_MorphTarget": "morphTarget34",
//             "glassesGuy_mesh_2_27_MorphTarget": "morphTarget35",
//             "glassesGuy_mesh_2_28_MorphTarget": "morphTarget36",
//             "glassesGuy_mesh_2_29_MorphTarget": "morphTarget37",
//             "glassesGuy_mesh_2_30_MorphTarget": "morphTarget38",
//             "glassesGuy_mesh_2_31_MorphTarget": "morphTarget39",
//             "glassesGuy_mesh_2_32_MorphTarget": "morphTarget40",
//             "glassesGuy_mesh_2_33_MorphTarget": "morphTarget41",
//             "glassesGuy_mesh_2_34_MorphTarget": "morphTarget42",
//             "glassesGuy_mesh_2_35_MorphTarget": "morphTarget43",
//             "glassesGuy_mesh_2_36_MorphTarget": "morphTarget44",
//             "glassesGuy_mesh_2_37_MorphTarget": "morphTarget45",
//             "glassesGuy_mesh_2_38_MorphTarget": "morphTarget46",
//             "glassesGuy_mesh_2_39_MorphTarget": "morphTarget47",
//             "glassesGuy_mesh_2_40_MorphTarget": "morphTarget48",
//             "glassesGuy_mesh_2_41_MorphTarget": "morphTarget49",
//             "glassesGuy_mesh_2_42_MorphTarget": "morphTarget50",
//             "glassesGuy_mesh_2_43_MorphTarget": "morphTarget51",
//             "glassesGuy_mesh_2_44_MorphTarget": "morphTarget52",
//             "glassesGuy_mesh_2_45_MorphTarget": "morphTarget53",
//             "glassesGuy_mesh_2_46_MorphTarget": "morphTarget54",
//             "glassesGuy_mesh_2_47_MorphTarget": "morphTarget55",
//             "glassesGuy_mesh_2_48_MorphTarget": "morphTarget56",
//             "glassesGuy_mesh_2_50_MorphTarget": "morphTarget57",
//             "glassesGuy_mesh_2_51_MorphTarget": "morphTarget58",
//             "glassesGuy_mesh_3_9_MorphTarget": "morphTarget59",
//             "glassesGuy_mesh_3_10_MorphTarget": "morphTarget60",
//             "glassesGuy_mesh_3_11_MorphTarget": "morphTarget61",
//             "glassesGuy_mesh_3_34_MorphTarget": "morphTarget62",
//             "glassesGuy_mesh_3_49_MorphTarget": "morphTarget63",
//             "glassesGuy_mesh_5_0_MorphTarget": "morphTarget64",
//             "glassesGuy_mesh_5_1_MorphTarget": "morphTarget65",
//             "glassesGuy_mesh_6_0_MorphTarget": "morphTarget66",
//             "glassesGuy_mesh_6_1_MorphTarget": "morphTarget67",
//             "glassesGuy_mesh_7_0_MorphTarget": "morphTarget68",
//             "glassesGuy_mesh_7_1_MorphTarget": "morphTarget69"
//         };
//     }

//module.exports = { retargetAnimWithBlendshapes, getMorphTargetIndex };
