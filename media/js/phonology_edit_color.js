
var busy_editing = 0;

function toggle_save(data) {
    if ($.isEmptyObject(data)) {
        return;
    }
    return;
}

 $(document).ready(function() {

    // setup required for Ajax POST
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
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
         console.log(JSON.stringify(update));
         $.ajax({
            url : update_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : toggle_save
         });
     });
 });
