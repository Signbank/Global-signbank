$(document).ready(function() {
    var player = projekktor('#projekktor',
                 {
                    autoplay: false, 
                    iframe: false,
                    width: 320,
                    height: 240,
                    addplugins: ['controlbar'],
                    plugin_controlbar: {
                     controlsTemplate: '<ul class="left"><li><div %{play}></div><div %{pause}></div></li><li><div %{title}></div></li></ul><ul class="bottom"><li><div %{scrubber}><div %{loaded}></div><div %{playhead}></div><div %{scrubberdrag}></div></div></li></ul>'                 
                    },
                    playlist: [{0: {src: base_url+"numbersigns/ns_010.mp4", type: "video/mp4"}}]
                });
});

var clips = ['ns_010', 'ns_011-019', 'ns_020-090', 'ns_022-099', 'ns_200-900', 'ns_100', 'ns_1k', 'ns_1m', 'ns_1g'];
 
function make_playlist(item) {
     return [{0: {src: base_url+"numbersigns/"+clips[item]+".mp4",
                  poster: base_url+"numbersigns/"+clips[item]+".jpg",
                  type: "video/mp4"}}];
}

var currentNS = -1;

function playNS(n) { 

        // reset the currentNS image to unselected
        if (currentNS>=0) {
            img = document.getElementById(clips[currentNS]);
            img.src = base_url+"numbersigns/"+clips[currentNS]+".jpg";
        }
        // remember what we're playing and replace the image with selected
        currentNS = n;
        img = document.getElementById(clips[n]);
        img.src = base_url+"numbersigns/"+clips[n]+"_select.jpg";

        var player = projekktor('#projekktor', {height: 1, minheight: 1});
        player.setFile(make_playlist(n)); 
        player.setPlay();
}

function replay() {
   var player = projekktor('#projekktor');
   player.setPlay();
}
