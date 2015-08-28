/*
 * jQuery Timer Plugin
 * http://www.evanbot.com/article/jquery-timer-plugin/23
 *
 * @version      1.0
 * @copyright    2009 Evan Byrne (http://www.evanbot.com)
 */ 

jQuery.timer = function(time,func,callback){
        var a = {timer:setTimeout(func,time),callback:null}
        if(typeof(callback) == 'function'){a.callback = callback;}
        return a;
};

jQuery.clearTimer = function(a){
        clearTimeout(a.timer);
        if(typeof(a.callback) == 'function'){a.callback();};
        return this;
};

var twohanded = Object()
twohanded["A"] =  "twohanded/th_a.jpg";
twohanded["B"] =  "twohanded/th_b.jpg";
twohanded["C"] =  "twohanded/th_c.jpg";
twohanded["D"] =  "twohanded/th_d.jpg";
twohanded["E"] =  "twohanded/th_e.jpg";
twohanded["F"] =  "twohanded/th_f.jpg";
twohanded["G"] =  "twohanded/th_g.jpg";
twohanded["H"] =  ["twohanded/th_h0.jpg", "twohanded/th_h1.jpg",  "twohanded/th_h2.jpg", "twohanded/th_h3.jpg", "twohanded/th_h4.jpg"];
twohanded["I"] =  "twohanded/th_i.jpg";
twohanded["J"] =  ["twohanded/th_j0.jpg", "twohanded/th_j1.jpg", "twohanded/th_j2.jpg"];
twohanded["K"] =  "twohanded/th_k.jpg";
twohanded["L"] =  "twohanded/th_l.jpg";
twohanded["M"] =  "twohanded/th_m.jpg";
twohanded["N"] =  "twohanded/th_n.jpg";
twohanded["O"] =  "twohanded/th_o.jpg";
twohanded["P"] =  "twohanded/th_p.jpg";
twohanded["Q"] =  "twohanded/th_q.jpg";
twohanded["R"] =  "twohanded/th_r.jpg";
twohanded["S"] =  "twohanded/th_s.jpg";
twohanded["T"] =  "twohanded/th_t.jpg";
twohanded["U"] =  "twohanded/th_u.jpg";
twohanded["V"] =  "twohanded/th_v.jpg";
twohanded["W"] =  "twohanded/th_w.jpg";
twohanded["X"] =  "twohanded/th_x.jpg";
twohanded["Y"] =  "twohanded/th_y.jpg";
twohanded["Z"] =  "twohanded/th_z.jpg";
twohanded["transition"] = "twohanded/transition.jpg";  

var onehanded = Object()
onehanded["A"] = "onehanded/oh_a.jpg";
onehanded["B"] = "onehanded/oh_b.jpg";
onehanded["C"] = "onehanded/oh_c.jpg";
onehanded["D"] = "onehanded/oh_d.jpg";
onehanded["E"] = "onehanded/oh_e.jpg";
onehanded["F"] = "onehanded/oh_f.jpg";
onehanded["G"] = "onehanded/oh_g.jpg";
onehanded["H"] = "onehanded/oh_h.jpg";
onehanded["I"] = "onehanded/oh_i.jpg";
onehanded["J"] = ["onehanded/oh_j0.jpg","onehanded/oh_j1.jpg","onehanded/oh_j2.jpg","onehanded/oh_j3.jpg"];
onehanded["K"] = "onehanded/oh_k.jpg";
onehanded["L"] = "onehanded/oh_l.jpg";
onehanded["M"] = "onehanded/oh_m.jpg";
onehanded["N"] = "onehanded/oh_n.jpg";
onehanded["O"] = "onehanded/oh_o.jpg";
onehanded["P"] = "onehanded/oh_p.jpg";
onehanded["Q"] = "onehanded/oh_q.jpg";
onehanded["R"] = "onehanded/oh_r.jpg";
onehanded["S"] = "onehanded/oh_s.jpg";
onehanded["T"] = "onehanded/oh_t.jpg";
onehanded["U"] = "onehanded/oh_u.jpg";
onehanded["V"] = "onehanded/oh_v.jpg";
onehanded["W"] = "onehanded/oh_w.jpg";
onehanded["X"] = "onehanded/oh_x.jpg";
onehanded["Y"] = "onehanded/oh_y.jpg";
onehanded["Z"] = ["onehanded/oh_z0.jpg", "onehanded/oh_z1.jpg", "onehanded/oh_z2.jpg", "onehanded/oh_z3.jpg"];
onehanded["transition"] = "onehanded/transition.jpg";   


(function( $ ){

	  $.fn.fingerspellimage = function(baseurl, images) {
		    /* add a fingerspelling image and setup the binding */

		  	return this.each(function() {
				if ($(this).attr("class") != 'blank') { 
	
			    	letter = $(this).attr("id");
					
					if (typeof(images[letter]) == 'object') {
					  imagesrc = images[letter][0];
					} else {
					  imagesrc = images[letter];
					} 
					
					/* make a new image */
					var image = new Image();
					$(image).attr('src', baseurl+imagesrc);
					$(this).append(image); 
					$(this).append("<div>"+letter+"</div>");
					$(this).click(function() {
						display_letter("#mainimg", $(this).attr("id"), 1500,  baseurl, images);
					});
				}
		  	});
		}
	  
	  
	})( jQuery );

function update_image(imageid, image) {

    $(imageid).attr('src', image); 
}

/* an animation plan is a sequence of objects
   with properties:
   'src' - image source url
   'time' -- time in milliseconds to display
   
    we have two procedures, one to build a plan given
    a word, another to animate a plan
*/

function plan_string(str, speed, baseurl, images) {
    plan = [plan_transition(speed, baseurl)];
    for(var i=0; i<str.length; i++) {
        plan = plan.concat(plan_letter(str[i], speed, baseurl, images));
        /* insert a transition between letters */
        if (i<str.length-1) {
            plan = plan.concat(plan_transition(speed, baseurl));
        }
    } 
    return plan;
}

function plan_transition(speed, baseurl) {
    return( [{src: baseurl+"twohanded/transition.jpg", time: speed/5}]);
}

function plan_letter(letter, speed, baseurl, images) { 
    
    letter = letter.toUpperCase();
    
    if (images[letter] == undefined) {
        return plan_transition(speed, baseurl);
    }
    /* check if we have one or multiple images */ 
    if (typeof(images[letter]) == 'object') {
        /* a sequence, we animate them */
        imglist = images[letter];
        result = [];
        brieftime = speed/4;  /* ms time between images */
        
        for(var i=0; i<imglist.length; i++) {
            result.push({src: baseurl+imglist[i], time: brieftime});
        }
        
        return(result);
        
    } else {
        return([{src: baseurl+images[letter], time: speed}]);
    }
}

/* animate a plan
   show the first image,
   schedule animation of the remainder after the given delay
*/
function animate_plan(imageid, plan) { 
    if (plan.length == 0) {
        return
    }
    step = plan.shift();
    update_image(imageid, step['src']);
    /* define a callback function to do the rest */
    var newfun = function () {
        animate_plan(imageid, plan);
    }
    /* schedule newfn in a bit */
    $.timer(step['time'], newfun);
}


function display_letter(imageid, letter, speed, baseurl, images) {
    plan = plan_letter(letter, speed, baseurl, images);
    animate_plan(imageid, plan);
}


function display_string(imageid, letter, speed, baseurl, images) {
    /* TODO: interrupt any playing animations before starting */
    plan = plan_string(letter, speed, baseurl, images); 
    animate_plan(imageid, plan);
}

function fingerspell_play(baseurl, images) {
	 if ($.mobile != undefined) {
		$.mobile.silentScroll(0);
	}
    $('#text').blur();  /* remove focus from the text box to force closing keyboard on iphone */
    speed = $('input:radio[name=speed]:checked').val();
    display_string("#mainimg", $('#text').val(), speed, baseurl, images); 
    return false;
}


