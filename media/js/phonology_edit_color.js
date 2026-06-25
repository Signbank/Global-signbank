
function reset_fields(variationid) {
    for (var i=0; i < gloss_phonology.length; i++) {
        var field = gloss_phonology[i];
        var field_lookup = '#'+field+'_'+variationid;
        if (['weakdrop', 'weakprop', 'domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'repeat', 'altern'].includes(field)) {
            field_lookup += '_select_value';
        } else if (['locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar'].includes(field)) {
            field_lookup += '_text';
        } else {
            field_lookup += '_value';
        }
        var field_input = $(field_lookup);
        if (!field_input) {return;}
        var field_value = $(field_lookup).val();
        $(field_lookup).attr("data-initial", field_value);
     }
}

function toggle_save(data) {
    if ($.isEmptyObject(data)) {
        var feedbackElt ='#feedback';
        $(feedbackElt).empty();
        var feedback = "<span class='item'>"+phonology_saved_str+"&nbsp; &nbsp; <span class='delete-btn'>&times;</span></span>";
        $(feedbackElt).html(feedback);
        return;
    }
    var variationid = data.variationid;
    reset_fields(variationid);
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

     $('.quick_save_phonology').click(function(e)
	 {
        e.preventDefault();
	    var objectid = $(this).attr('value');
	    var datatype = $(this).attr('data-type');
	    if (datatype === 'variant') {
	        var update_url = url + "/dictionary/update/phonological_variation/" + objectid + "/";
	    } else {
	        var update_url = url + "/dictionary/update/update_gloss_phonology/" + objectid + "/";
	    }
        var update = { 'csrfmiddlewaretoken': csrf_token };
        for (var i=0; i < gloss_phonology.length; i++) {
            var field = gloss_phonology[i];
            var field_lookup = '#'+field+'_'+objectid;
            if (['weakdrop', 'weakprop', 'domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'repeat', 'altern'].includes(field)) {
                field_lookup += '_select_value';
            } else if (['locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar'].includes(field)) {
                field_lookup += '_text';
            } else {
                field_lookup += '_value';
            }
            var field_key = $(field_lookup).attr("name");
            update[field_key] = $(field_lookup).val();
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
