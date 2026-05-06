
var busy_editing = 0;

function toggle_save(data) {
    if ($.isEmptyObject(data)) {
        return;
    }
    return;
    // var glossid = data.glossid;
    // var handedness = data.handedness;
    // var hCell = $("#handedness_cell_"+glossid);
    // $(hCell).empty();
    // var cell = "<span class='handedness'>"+handedness+"</span>";
    // hCell.html(cell);
    //
    // var button_lookup = '#button_' + glossid + '_handedness';
    // var buttonCell = $(button_lookup);
    // var button_contents = similar_gloss_fields_labels['handedness'] + ': ' + handedness;
    // buttonCell.attr('value', button_contents);
}

 $(document).ready(function() {

     disable_edit();

     if (window.location.search.match('edit')) {
         toggle_edit();
     }

     $('#enable_edit').click(function()
	{
		toggle_edit(false);
	});

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
	    var variantid = $(this).attr('value');
        var update = { 'csrfmiddlewaretoken': csrf_token };
        for (var i=0; i < gloss_phonology.length; i++) {
            var field = gloss_phonology[i];
            var field_lookup = '#'+field+'_'+variantid;
            var field_key = $(field_lookup).attr("name");
            var field_value = $(field_lookup).val();
            update[field_key] = field_value;
         }
         console.log(JSON.stringify(update));
         $.ajax({
            url : url + "/dictionary/update/phonological_variation/" + variantid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : toggle_save
         });
     });
 });

function disable_edit() {
    $('.edit').css('color', 'inherit');
    $('#edit_message').text('');

    $('.editform').hide();
    $('.button-to-appear-in-edit-mode').hide();
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');

    $('input').each(function()
    {
        $(this).html('-')
    });

    busy_editing = 0;
}

function enable_edit() {

    $('.edit').css('color', 'red');
    $('.edit_list').css('color', 'red');
    $('.edit_check').css('color', 'red');

    $('#edit_message').text('Click on red text to edit  ');
    $('#edit_message').css('color', 'inherit');

    $('.editform').show();
    $('.button-to-appear-in-edit-mode').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');

    busy_editing = 1;
};

function toggle_edit(redirect_to_next) {
    if ($('#enable_edit').hasClass('edit_enabled'))
    {
        disable_edit();

        $('#enable_edit').removeClass('edit_enabled');
        $('#enable_edit').text(edit_mode_str);

    } else {
        enable_edit();
        $('#enable_edit').addClass('edit_enabled');
        $('#enable_edit').text(turn_off_edit_mode_str);
    }

}
