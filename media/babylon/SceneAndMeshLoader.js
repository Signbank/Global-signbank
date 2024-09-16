async function createScene(canvas) {
    console.log("Loading Scene!");

    var options = {
        antialias: true, // Enable or disable antialiasing
        powerPreference: "high-performance",
        stencil: true,
    };

    var engine = new BABYLON.Engine(canvas, options);
    engine.disableManifestCheck = true //disable manifest checking for

    BABYLON.Animation.AllowMatricesInterpolation = true;

    // This creates a basic Babylon Scene object (non-mesh)
    var scene = new BABYLON.Scene(engine);

    // This creates a light, aiming 0,1,0 - to the sky (non-mesh)
    var light = new BABYLON.HemisphericLight("light", new BABYLON.Vector3(0, 1, 0), scene);
	// light.diffuse = new BABYLON.Color3(1, 0.98, 0.82);
	// light.specular = new BABYLON.Color3(0.23, 0.23, 0.23);
	// light.groundColor = new BABYLON.Color3(0, 0, 0);

    console.log("Scene and mesh loaded successfully.");
    return [scene, engine];
};

var loadAssetMesh = async function (scene, path = basePathMesh + "Nemu/", fileName = "Nemu.glb", bugger = false) {
    console.log("Loading mesh from: " + path + fileName + "...");

    // TODO: When clicking the button twice, the animation first frame loads
    BABYLON.SceneLoader.OnPluginActivatedObservable.add(function (loader) {
        if (loader.name == "gltf" || loader.name == "glb") {
            loader.animationStartMode = BABYLON.GLTFLoaderAnimationStartMode.NONE;
        }
    });

    if (bugger) {
        scene.debugLayer.show({
            embedMode: true
        });
    }

    const asset = {
        fetched: await BABYLON.SceneLoader.ImportMeshAsync(null, path, fileName, scene),
        root: null,
        faceMesh: null,
        teethMesh: null,
        hips: null,
        eyeMesh: null,
        morphTargetManagers: [],
        skeletons: [],
        animationGroups: [],
        papa: null,
        opa: null,
        god: null,
        resetMorphs: function resetMorphTargets() {
            // Loop through all the meshes in the scene
            this.fetched.meshes.forEach(mesh => {
                // Check if the mesh has a MorphTargetManager
                if (mesh.morphTargetManager) {
                    // Get the MorphTargetManager
                    let morphTargetManager = mesh.morphTargetManager;
        
                    // Loop through each morph target in the MorphTargetManager
                    for (let i = 0; i < morphTargetManager.numTargets; i++) {
                        let morphTarget = morphTargetManager.getTarget(i);
        
                        // Set the influence (value) of the morph target to 0
                        morphTarget.influence = 0;
                    }
                }
            });
        },
    };

    // Find all animation groups
    for (animGroup of scene.animationGroups) {
        asset.animationGroups.push(animGroup);
    }

    // Find the root mesh and the face mesh for its morph target manager
    for (mesh of asset.fetched.meshes) {
        mesh.position = new BABYLON.Vector3(0, 0, 0);

        if (mesh.name === "__root__") {
            asset.root = mesh;
        } else if (mesh.name === "newNeutral_primitive0") {
            asset.eyeMesh = mesh;
        } else if (mesh.name === "newNeutral_primitive1") {
            asset.faceMesh = mesh;
        } else if (mesh.name === "newNeutral_primitive2") {
            asset.teethMesh = mesh;
        }

        if (mesh.morphTargetManager) {
            asset.morphTargetManagers.push(mesh.morphTargetManager);
        }
    }

    // Put the root mesh node in an empty transform node
    var rootTransformNode = new BABYLON.TransformNode("papa");
    asset.root.parent = rootTransformNode;
    asset.papa = rootTransformNode;
    var papaTransformNode = new BABYLON.TransformNode("opa");
    asset.papa.parent = papaTransformNode;
    asset.opa = papaTransformNode;
    var opaTransformNode = new BABYLON.TransformNode("god");
    asset.opa.parent = opaTransformNode;
    asset.god = opaTransformNode;

    // Find all skeletons
    for (skeleton of asset.fetched.skeletons) {
        asset.skeletons.push(skeleton);
    }

    // Find the hips transform node
    for (transformNode of asset.fetched.transformNodes) {
        if (transformNode.name === "Hips" || transformNode.name === "hips" || transformNode.name === "pelvis" || transformNode.name === "Pelvis") {
            asset.hips = transformNode;
        }
    }

    return asset;
};

var rotateMesh180 = function (mesh) {
    mesh.rotation = new BABYLON.Vector3(BABYLON.Tools.ToRadians(0), BABYLON.Tools.ToRadians(180), BABYLON.Tools.ToRadians(0));

    // WE SHOULD ROT LIKE THIS:
    // loadedMesh.fetched.meshes.forEach(mesh => {
    //     mesh.rotate(BABYLON.Axis.X, Math.PI/4, BABYLON.Space.WORLD);
    //     console.log("rotted");
    // });
};


var setLightOnMesh = function (scene, mesh) {
    var topLight = new BABYLON.PointLight("topLight", mesh.getAbsolutePosition().add(new BABYLON.Vector3(0, 4, 0)), scene);
    topLight.diffuse = new BABYLON.Color3(1, 1, 1); // Set light color
    topLight.intensity = 1; // Set light intensity
}

// Local Axes function, made for debugging purposes. We can view the local axes of a mesh.
function localAxes(size, mesh, scene) {
    var pilot_local_axisX = BABYLON.Mesh.CreateLines("pilot_local_axisX", [
        new BABYLON.Vector3.Zero(), new BABYLON.Vector3(size, 0, 0), new BABYLON.Vector3(size * 0.95, 0.05 * size, 0),
        new BABYLON.Vector3(size, 0, 0), new BABYLON.Vector3(size * 0.95, -0.05 * size, 0)
    ], scene);
    pilot_local_axisX.color = new BABYLON.Color3(1, 0, 0);

    pilot_local_axisY = BABYLON.Mesh.CreateLines("pilot_local_axisY", [
        new BABYLON.Vector3.Zero(), new BABYLON.Vector3(0, size, 0), new BABYLON.Vector3(-0.05 * size, size * 0.95, 0),
        new BABYLON.Vector3(0, size, 0), new BABYLON.Vector3(0.05 * size, size * 0.95, 0)
    ], scene);
    pilot_local_axisY.color = new BABYLON.Color3(0, 1, 0);

    var pilot_local_axisZ = BABYLON.Mesh.CreateLines("pilot_local_axisZ", [
        new BABYLON.Vector3.Zero(), new BABYLON.Vector3(0, 0, size), new BABYLON.Vector3(0, -0.05 * size, size * 0.95),
        new BABYLON.Vector3(0, 0, size), new BABYLON.Vector3(0, 0.05 * size, size * 0.95)
    ], scene);
    pilot_local_axisZ.color = new BABYLON.Color3(0, 0, 1);

    var local_origin = BABYLON.MeshBuilder.CreateBox("local_origin", { size: 1 }, scene);
    local_origin.isVisible = false;

    pilot_local_axisX.parent = mesh;
    pilot_local_axisY.parent = mesh;
    pilot_local_axisZ.parent = mesh;
}

function hipsFrontAxes(size, mesh, scene) {
    var localHipsAxis = BABYLON.Mesh.CreateLines("localHipsAxis", [
        new BABYLON.Vector3.Zero(), new BABYLON.Vector3(0, -size, 0), new BABYLON.Vector3(-0.05 * size, -size * 0.95, 0),
        new BABYLON.Vector3(0, -size, 0), new BABYLON.Vector3(0.05 * size, -size * 0.95, 0)
    ], scene);
    localHipsAxis.color = new BABYLON.Color3(0, 1, 1);

    localHipsAxis.parent = mesh;
}

function generateKey(frame, value) {
    return {
        frame: frame,
        value: value
    };
};
var pineappleResult = "";
var createPineapple = async function (scene, basePathMesh, targetMesh) {
    console.log("Creating pineapple...");
    //🍍
    pineappleResult = await BABYLON.SceneLoader.ImportMeshAsync(null, basePathMesh, "pineapple.glb", scene);

    if (pineappleResult.meshes.length > 0) {
        const pineappleMesh = pineappleResult.meshes[0]; // Get the first mesh from the imported meshes
        pineappleMesh.rotation = new BABYLON.Vector3(BABYLON.Tools.ToRadians(0), BABYLON.Tools.ToRadians(0), BABYLON.Tools.ToRadians(0));
        pineappleMesh.name = "Pineapple"; // Give the mesh a name "Pineapple"
        //give pineapple a position

        //explain the position of the mesh
        //x,y,z? 
        //x: left to right
        //y: up and down
        //z: forward and backward


        pineappleMesh.position = new BABYLON.Vector3(0, 0, 10);

        // Function to generate key items


        // Generate keys using sine wave
        var keys = [];
        for (var frame = 0; frame <= 200; frame++) {
            if (frame < 40) {
                var value = Math.max(Math.sin(frame * Math.PI / 10) * 0.5, 0); // Adjust the amplitude and frequency as needed
                keys.push(generateKey(frame, value));
            } else {
                keys.push(generateKey(frame, 0.1));
            }
        }
        // console.log(keys);

        // Add bouncing animation to pineapple
        var animationBox = new BABYLON.Animation("myAnimation", "position.y", 15, BABYLON.Animation.ANIMATIONTYPE_FLOAT, BABYLON.Animation.ANIMATIONLOOPMODE_CYCLE);
        animationBox.setKeys(keys);
        pineappleMesh.animations = [];
        pineappleMesh.animations.push(animationBox);
        scene.beginAnimation(pineappleMesh, 0, 200, true);


        //what if we have enough of Pineapple? 
        //we give it a animation to bounce towards the actor and then let it disappear
        document.addEventListener('keypress', function (event) {
            if (event.key === '1') {
                var keysZ = []; // Keyframes for the z-axis
                var keysY = []; // Keyframes for the y-axis
                var originalPositionZ = pineappleMesh.position.z; // Get current Z position
                var originalPositionY = pineappleMesh.position.y; // Get current Y position
                var bounceDistanceZ = 10; // Distance to bounce towards actor on z-axis
                var bounceHeightY = 5;  // Maximum height of the bounce on y-axis

                //get z and y position of the first mesh (the actor)
                var actorMesh = pineappleResult.meshes[0];
                var actorPositionZ = actorMesh.position.z;
                var actorPositionY = actorMesh.position.y;

                //stop any animation of pineapple
                scene.stopAnimation(pineappleMesh);


                // Bounce towards position z = 0 and make it "fly" on y-axis
                for (var frame = 0; frame <= 40; frame++) {
                    var zValue = originalPositionZ - (Math.sin(frame * Math.PI / 80) * bounceDistanceZ);
                    var yValue = originalPositionY + (Math.sin(frame * Math.PI / 40) * bounceHeightY); // Sine wave for smooth up and down motion
                    keysZ.push({ frame: frame, value: zValue });
                    keysY.push({ frame: frame, value: yValue });
                }

                // Set the final position at z = 0 and y returning to original
                keysZ.push({ frame: 40, value: actorPositionZ });
                keysY.push({ frame: 40, value: actorPositionY });

                // Create the animation for z-axis
                var animationZ = new BABYLON.Animation(
                    "bounceToActorZ",
                    "position.z",
                    40,
                    BABYLON.Animation.ANIMATIONTYPE_FLOAT,
                    BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
                );

                // Create the animation for y-axis
                var animationY = new BABYLON.Animation(
                    "bounceToActorY",
                    "position.y",
                    40,
                    BABYLON.Animation.ANIMATIONTYPE_FLOAT,
                    BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT
                );

                animationZ.setKeys(keysZ);
                animationY.setKeys(keysY);

                pineappleMesh.animations = [animationZ, animationY]; // Set the new animations
                scene.beginAnimation(pineappleMesh, 0, 40, false); // Start animation with no looping

                // Make the pineapple disappear after the animation
                // Observable to detect when the frame 40 is reached
                var observer = scene.onBeforeRenderObservable.add(() => {
                    if (scene.getAnimationRatio() * 40 >= 40) {
                        //change pineapple in another mesh


                        scene.onBeforeRenderObservable.remove(observer); // Remove observer to avoid repeated execution
                        pineappleMesh.dispose(); // Remove the mesh from the scene
                        console.log("Pineapple mesh has been removed from the scene.");
                    }
                });
            }
        });
    }

    // var pineappleLight = new BABYLON.PointLight("pineappleLight", pineappleResult.meshes[0].getAbsolutePosition().add(new BABYLON.Vector3(0, 4, 0)), scene);
    // pineappleLight.diffuse = new BABYLON.Color3(1, 1, 1); // Set light color
    // pineappleLight.intensity = 1; // Set light intensity
    //🍍
};

// For testing purposes
//module.exports = { createScene, loadAssetMesh, rotateMesh180, setLightOnMesh, localAxes, hipsFrontAxes, generateKey, createPineapple };
