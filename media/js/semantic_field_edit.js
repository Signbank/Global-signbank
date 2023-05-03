// javascript for template admin_search_history.html

var original_values_for_changes_made = new Array();

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
	    var searchHistoryTable = $("#semanticFieldTranslations");
        var table_cell = '.semfieldtranslang_' + semfieldid;
        var cell = searchHistoryTable.find(table_cell);
        cell.html(new_value);
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
    $.fn.editable.defaults['width'] = 'auto';
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

    configure_edit();
    enable_edit();
});
