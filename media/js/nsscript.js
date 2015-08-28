
// array of clip and image names
clips = [ 
 'ns_010',       // 0
 'ns_011-019',   // 1
 'ns_020-090',   // 2
 'ns_022-099',   // 3
 'ns_200-900',   // 4
 'ns_100',       // 5
 'ns_1k',        // 6
 'ns_1m',        // 7
 'ns_1g'         // 8
]

// Configuration for the flowplayer instance, we add the video 
// name to this and call setConfig to play a new video
fpconfig = { 
           autoPlay: true, 
           autoBuffering: false, 
           loop: false, 
           autoRewind: true,   
           hideControls: true} 


var currentNS = -1;

function playNS(n) { 
    if (document.getElementById) {
        
        // reset the currentNS image to unselected
        if (currentNS>=0) {
            img = document.getElementById(clips[currentNS]);
            img.src = "{% auslan_static_prefix %}img/"+clips[currentNS]+".jpg";
        }
        // remember what we're playing and replace the image with selected
        currentNS = n
        img = document.getElementById(clips[n]);
        img.src = "{% auslan_static_prefix %}img/"+clips[n]+"_select.jpg";
        
        fp = document.getElementById("FlowPlayer");
        fpconfig['videoFile']  = "{% auslan_static_prefix %}flash/" + clips[n] + ".flv";
        fp.setConfig(fpconfig);
        fp.DoPlay();
    }
}
