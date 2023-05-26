// javascript for template semanticfield_detail.html

var original_values_for_changes_made = new Array();
var busy_editing = 0;

function hide_other_forms(focus_field) {
    // this function does nothing but is required to exist for the editable js code
};

function enable_edit() {
    $('.edit').editable('enable');
};

function update_view_and_remember_original_value(change_summary)
{
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];

	    var semfieldid = $(this).attr("id");
	    if (semfieldid == 'description') {
	        $(this).html(new_value)
	    } else {
            var searchHistoryTable = $("#semanticFieldTranslations");
            var table_cell = '.semfieldtranslang_' + semfieldid;
            var cell = searchHistoryTable.find(table_cell);
            cell.html(new_value);
        }
    }
}

function configure_edit() {

    $.fn.editable.defaults['indicator'] = saving_str;
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" type="submit">Save</button>';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default" type="cancel">Cancel</button>';
    $.fn.editable.defaults['cols'] = '40';
    $.fn.editable.defaults['rows'] = '1';
    $.fn.editable.defaults['width'] = '400';
    $.fn.editable.defaults['height'] = 'auto';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr)
                        {

                            alert("There was an error processing this change: " + xhr.responseText );
                            original.reset();
                        };

     $('.edit_text').editable(edit_post_url, {
		 callback : update_view_and_remember_original_value
	 });

}

function disable_edit() {
    $('.edit').editable('disable');
    $('.edit').css('color', 'black');
    $('#edit_message').text('');
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');

    if (busy_editing) {
        busy_editing = false;
    }
}

function enable_edit() {
    $('.edit').editable('enable');
    $('.edit').css('color', 'red');
    $('#edit_message').text('Click on red text to edit  ');
    $('#edit_message').css('color', 'black');
    busy_editing = 1;
}

function toggle_edit() {
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

$(document).ready(function() {

     configure_edit();

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

});
