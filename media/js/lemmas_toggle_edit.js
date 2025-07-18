// javascript for template admin_lemma_list.html and update_lemma.html
// this code uses json ajax calls

function toggle_language_fields(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var lemmaid = data.lemmaid;
    var lemma_translations = data.lemma_translations;
    for (var inx in lemma_translations) {
        var translation = lemma_translations[inx];
        var lang2char = translation['lang2char'];
        var text = translation['text'];
        // for occurrence in Lemma List View
        var hCell = $("#lemma_text_"+lemmaid+"_"+lang2char);
        $(hCell).empty();
        hCell.html(text);
        // for occurrence in Lemma Update View
        var inputCell = $("#id_lemmaupdate_"+lang2char);
        inputCell.attr("value", text);
    }
    var spanCell = $("#lemma_wrench_"+lemmaid);
    $(spanCell).empty();
    var constraintsCell = $("#lemma_constraints_"+lemmaid);
    $(constraintsCell).empty();
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

     $('.quick_copy_missing_language_fields').click(function(e)
	 {
         e.preventDefault();
	     var lemmaid = $(this).attr('value');
         $.ajax({
            url : url + "/dictionary/lemma/copymissinglanguage/" + lemmaid + "/",
            type: 'POST',
            datatype: "json",
            success : toggle_language_fields
         });
     });
});
