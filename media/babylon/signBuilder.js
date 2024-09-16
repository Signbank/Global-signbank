function signBuilder(){
    ParamsManager.animations = [];
    removeAnims(scene, loadedMesh);
    AnimationSequencer.stop();

    $("#signBuilder").modal("show")
}

document.addEventListener('DOMContentLoaded', function () {
    var glosArray = [];

    // Simulate loading glosses
    async function loadGlos() {
        // This should be replaced with your actual data fetching method
        var sCArray = await signCollectLoader("Motion Capture", "statusFilter", 1000); //if you want to know thema names, go to signcollect website and ask Gomer for login
        var glos = []; // Define the 'glos' variable as an empty array

        for (let i = 0; i < sCArray.length; i++) {
            glos[i] = sCArray[i].glos;
        }
        return glos; // Return the 'glos' array
    }

    // Function to handle input for search and display results
    window.searchGlos = async function () {
        const searchInput = document.getElementById('searchInput').value.toLowerCase();
        const allGlos = await loadGlos();  // Load or filter glos based on input
        const glosContainer = document.getElementById('glosContainer');
        glosContainer.innerHTML = '';  // Clear previous results

        allGlos.filter(glos => glos.toLowerCase().includes(searchInput)).forEach(glos => {
            console.log(glos)
            const label = document.createElement('span');
            label.classList.add('badge', 'bg-secondary', 'me-2');
            label.textContent = glos;
            label.onclick = function () { addGlos(glos); };
            glosContainer.appendChild(label);
        });
    };

    // Function to add selected glos to the array
    window.addGlos = function (glosName) {
         zinArray.push(glosName);
            updateGlosDisplay();
        
    };

    // Function to update the display of selected glosses
    function updateGlosDisplay() {
        const selectedGlosContainer = document.getElementById('selectedGlos');
        selectedGlosContainer.innerHTML = '';  // Clear current glosses
        zinArray.forEach(glos => {
            const label = document.createElement('span');
            label.classList.add('badge', 'bg-primary', 'me-2');
            label.textContent = glos;
            selectedGlosContainer.appendChild(label);
        });
    }

    window.cleanSentence = function(){
        zinArray = []
        updateGlosDisplay()

    }

    // Function to handle the final array of glosses
    window.handleGlosses = function () {
        ParamsManager.animations = zinArray;



        $('#signBuilder').modal('hide');
        console.log('Handling glosses:', glosArray);
        continueLoop = true;

        if(recordingMethod == "zin")
        {
            animationSequencing(recording=true, keepPlaying=true, frame="blend");

        }
        else
        {
            animationSequencing(recording=false, keepPlaying=true, frame="blend");

        }
    };

    window.toggleRecording = function(){
        //check if the checkbox is checked
        if (document.getElementById('recordCheckbox').checked) {
            recordingMethod = "zin"
        } else {
            recordingMethod = ""
        }
    }
        
});





