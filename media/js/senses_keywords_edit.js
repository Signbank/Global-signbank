// javascript for template admin_keyword_list.html

var original_values_for_changes_made = new Array();

function hide_other_forms(focus_field) {
    // this function does nothing but is required to exist for the editable js code
};

function update_view_and_remember_original_value(change_summary)
{
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];

	    var glossid = $(this).attr("data-glossid");
	    var keywordsSensesTable = $("#keywordsSenses");
        var table_cell = '.senses_' + glossid;
        var cell = keywordsSensesTable.find(table_cell);
        cell.html(new_value);
    }
}

function configure_edit() {

    $.fn.editable.defaults['indicator'] = saving_str;
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" type="submit">Save</button>';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default" type="cancel">Cancel</button>';
    // the cols and rows are set for the queryName Field
    // because of the implementation and use of editable in "single object" templates in the rest of the code
    // this is modified here to decrease the size of the textarea type, used in the edit_query editable
    // the text type of editable is used for other fields in other templates
    $.fn.editable.defaults['cols'] = '40';
    $.fn.editable.defaults['rows'] = '1';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr)
                        {

                            alert("There was an error processing this change: " + xhr.responseText );
                            original.reset();
                        };
     $('.edit_sense').click(function()
	 {
	     var this_data = $(this).attr('value');
	     // construct the url dynamically
	     var edit_post_url = $(this).attr("data-editposturl");

		 $(this).editable(edit_post_url, {
		     params : { a: 0 },
		     type      : 'textarea',
		     data    : this_data,
			 callback : update_view_and_remember_original_value
		 });
     });

}

function update_gloss_senses(data) {
    var glossid = data.glossid;
    var language = data.language;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
    var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
    var sensesCell = $(senses_glossid);
    var modalSensesCell = $(modal_senses_glossid);
    $(sensesCell).empty();
    $(modalSensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
            }
        };
        row.append("</td>");
        modalSensesCell.append(row);
    }
    modalSensesCell.append("</tr>");
    for (var key in senses_groups) {
        var row = $("<tr/>");
                row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");
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

     $('.regroup_keywords').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var language = $(this).attr("data-language");
         var form_id = '#form_regroup_keywords_' + glossid + '_' + language;
         var regroup = [];
         $(form_id).find('input[name="regroup"]').each(function() {
            regroup.push(this.value);
         });
         var group_index = [];
         $(form_id).find('input[name="group_index"]').each(function() {
            group_index.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/group_keywords/" + glossid,
            type: 'POST',
            data: { 'language': language,
                    'regroup': JSON.stringify(regroup),
                    'group_index': JSON.stringify(group_index),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : update_gloss_senses
         });
     });
//    configure_edit();
});
