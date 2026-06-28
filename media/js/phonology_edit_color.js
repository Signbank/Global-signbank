
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

     $('.quick_save_phonology').click(function(e)
	 {
        e.preventDefault();
	    var objectid = $(this).attr('value');
	    var datatype = $(this).attr('data-type');
        var panel = $(this).attr('data-category');
        var update_url = url + "/dictionary/update/update_gloss_phonology/" + objectid + "/";
        var update = { 'csrfmiddlewaretoken': csrf_token };
        for (var i=0; i < gloss_phonology.length; i++) {
            var field = gloss_phonology[i];
            var select_key = '#'+field;
            if (['weakdrop', 'weakprop', 'domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'repeat', 'altern'].includes(field)) {
                select_key += '_select_value';
            } else if (['locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar'].includes(field)) {
                select_key += '_text';
            } else if (use_lookaheads === 'lookaheads') {
                select_key += '_machine_value';  // field choice selections
            } else {
                select_key += '_value';  // field choice selections
            }
            update[field] = $(select_key).val();
            for (const variationid of phonological_variations_ids) {
                var field_key = field+'_'+variationid;
                var select_key = '#'+field_key;
                if (['weakdrop', 'weakprop', 'domhndsh_letter_or_number', 'subhndsh_letter_or_number', 'repeat', 'altern'].includes(field)) {
                    select_key += '_select_value';
                } else if (['locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar'].includes(field)) {
                    select_key += '_text';
                } else if (use_lookaheads === 'lookaheads') {
                    select_key += '_machine_value';  // field choice selections
                } else {
                    select_key += '_value';  // field choice selections
                }
                update[field_key] = $(select_key).val();
            }
         }
         $.ajax({
            url : update_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    sessionStorage.setItem('panel', panel);
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
 });
