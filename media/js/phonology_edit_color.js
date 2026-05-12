

function toggle_save(data) {
    if ($.isEmptyObject(data)) {
        var feedbackElt ='#feedback';
        $(feedbackElt).empty();
        var feedback = "<span class='item'>"+phonology_saved_str+"&nbsp; &nbsp; <span class='delete-btn'>&times;</span></span>";
        $(feedbackElt).html(feedback);
        return;
    }
    var variationid = data.variationid;
    var feedbackElt ='#feedback_'+variationid;
    $(feedbackElt).empty();
    var feedback = "<span class='item'>"+phonology_saved_str+"&nbsp; &nbsp;  <span class='delete-btn' data-value='"+variationid+"'>&times;</span></span>";
    $(feedbackElt).html(feedback);
}

 $(document).ready(function() {

    // setup required for Ajax POST
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false,
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

    $(".feedback").on("click", ".delete-btn", function() {
        $(this).parent(".item").remove();
    });

     $('.quick_save').click(function(e)
	 {
        e.preventDefault();
	    var objectid = $(this).attr('value');
	    var datatype = $(this).attr('data-type');
	    if (datatype == 'variant') {
	        var update_url = url + "/dictionary/update/phonological_variation/" + objectid;
	    } else {
	        var update_url = url + "/dictionary/update/update_gloss_phonology/" + objectid;
	    }
        var update = { 'csrfmiddlewaretoken': csrf_token };
        for (var i=0; i < gloss_phonology.length; i++) {
            var field = gloss_phonology[i];
            var field_lookup = '#'+field+'_'+objectid;
            var field_key = $(field_lookup).attr("name");
            var field_value = $(field_lookup).val();
            update[field_key] = field_value;
         }
         $.ajax({
            url : update_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : toggle_save
         });
     });
 });
