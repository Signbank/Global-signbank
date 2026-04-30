
function swap(json){
  var ret = {};
  for(var key in json){
    ret[json[key]] = key;
  }
  return ret;
}

//Keep track of the original values of the changes made, so we can rewind it later if needed
//Keep track of the new values in order to generate hyperlinks for Handshapes
var original_values_for_changes_made = new Array();
var new_values_for_changes_made = new Array();
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
     configure_edit();

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
         console.log(update);
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
    $('.edit').editable('disable');
    $('.edit').css('color', 'inherit');
    $('#edit_message').text('');

    $('.editform').hide();
    $('.button-to-appear-in-edit-mode').hide();
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');

    //To prevent RSI
    $('.edit').each(function()
    {
        console.log('inside for each edit');
        if ($(this).html() == '------')
        {
            id = $(this).attr('id');
            if (id == 'weakdrop' || id == 'weakprop' || id == 'domhndsh_letter' || id == 'domhndsh_number' || id == 'subhndsh_letter' || id == 'subhndsh_number') {
                $(this).html('&nbsp;');
            } else {
                $(this).html('-');
            }
        }
    });

    $('input').each(function()
    {
        console.log('inside input each');
        $(this).html('-')
    });

    busy_editing = 0;
}

function enable_edit() {

    $('.edit').editable('enable');
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


function configure_edit() {

    $.fn.editable.defaults['indicator'] = saving_str;
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default btn-default-light" style="" type="cancel">Cancel</button>';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" style="" type="submit">OK</button>';
    $.fn.editable.defaults['cssclass'] = 'preview';
    $.fn.editable.defaults['cancelleft'] = '100px';
    $.fn.editable.defaults['submitleft'] = '200px';
    $.fn.editable.defaults['width'] = 'auto';
    $.fn.editable.defaults['height'] = 'auto';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr)
                        {
                            if (xhr.responseText.indexOf('UNIQUE constraint failed') > -1)
                            {
                                alert(idgloss_already_exists_str);
                            }
                            else
                            {
                                alert("There was an error processing this change: " + xhr.responseText );
                            }
                              original.reset();
                        };


     $('.edit_text').editable(edit_post_url, {
         params : { a: 0, field: $(this).attr('id') },
         type      : 'text',
		 callback : update_text_area
	 });
     $('.edit_area').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'textarea',
		 callback : update_text_area,
         onerror : function(settings, original, xhr){
               alert(xhr.responseText);
               original.reset();
         },
     });

     $('.edit_check').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'checkbox',
         checkbox: { trueValue: yes_str, falseValue: no_str },
		 callback : update_checkbox_tabbed
     });
     $('.edit_WD').click(function()
	 {
	     var this_data = $(this).attr('value');
	     var index_of_modified_field = '1';
         for (var key in handedness_weak_choices) {
            var value = handedness_weak_choices[key];
            if (value === this_data) {
                index_of_modified_field = key;
                break;
            }
         };
         $(this).attr('data-value', index_of_modified_field);
		 $(this).editable(edit_post_url, {
		     params : { a: index_of_modified_field,
		                field: 'weakdrop',
		                display: $(this).attr('value'),
		                colors: handedness_weak_choices_colors,
		                choices: handedness_weak_choices },
		     type      : 'select',
		     data    : handedness_weak_choices,
			 callback : update_articulation
		 });
     });
     $('.edit_WP').click(function()
	 {
	     var this_data = $(this).attr('value');
	     var index_of_modified_field = '1';
         for (var key in handedness_weak_choices) {
            var value = handedness_weak_choices[key];
            if (value === this_data) {
                index_of_modified_field = key;
                break;
            }
         };
         $(this).attr('data-value', index_of_modified_field);
		 $(this).editable(edit_post_url, {
		     params : { a: index_of_modified_field,
		                field: 'weakprop',
		                display: $(this).attr('value'),
		                colors: handedness_weak_choices_colors,
		                choices: handedness_weak_choices },
		     type      : 'select',
		     data    : handedness_weak_choices,
			 callback : update_articulation
		 });
     });
     $('.edit_letter').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'checkbox',
         checkbox: { trueValue: 'letter', falseValue: '&nbsp;' },
		 callback : update_checkbox_tabbed
     });
     $('.edit_number').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'checkbox',
         checkbox: { trueValue: 'number', falseValue: '&nbsp;' },
		 callback : update_checkbox_tabbed
     });

     $('.edit_list').click(function()
	 {
	     var this_value = $(this).attr('value');
         var this_edit_post_url = $(this).attr('data-edit_post_url');
         var this_field = $(this).attr('data-field');
	     var edit_list_choices = static_choice_lists[this_field];
	     var edit_list_choice_colors = static_choice_list_colors[this_field];
         var dynamic_choices = choice_lists[this_field];
	     var index_of_modified_field = '_0';
         for (var key in edit_list_choices) {
            var value = edit_list_choices[key];
            if (value === this_value) {
                index_of_modified_field = key;
                break;
            }
         }
         $(this).attr('data-value', index_of_modified_field);
		 $(this).editable(this_edit_post_url, {
		     params : { a: index_of_modified_field,
		                field: this_field,
		                display: this_value,
		                colors: edit_list_choice_colors,
		                choices: edit_list_choices },
		     type      : 'select',
		     data    : dynamic_choices,
			 callback : update_view_and_remember_original_value
		 });
     });
}

function hide_other_forms(focus_field) {

}


function update_text_area(newtext)
{
    $(this).html(newtext);
    $(this).attr("value", newtext);
    if (newtext === '') {
        $(this).parent().addClass('empty_row');
    } else {
        $(this).parent().removeClass('empty_row');
    }
}

function update_checkbox_tabbed(change_summary) {
    var id = $(this).attr('id');
    var split_values = change_summary.split('\t');
    var boolean_value = split_values[0];
    var display_value = split_values[1];
    var category_value = split_values[2];
    $(this).attr("value", boolean_value);
    $(this).html(display_value);
    if (boolean_value === 'True') {
        $(this).parent().removeClass('empty_row');
    } else {
        $(this).parent().addClass('empty_row');
    }
}

function update_checkbox(data)
{
    var id = $(this).attr('id');
    if ($.isEmptyObject(data)) {
        $(this).html("");
        return;
    }
    var boolean_value = data.boolean_value;
    $(this).attr("value", boolean_value);
    var display_value = data.display_value;
    $(this).html(display_value);
    if (boolean_value) {
        $(this).parent().removeClass('empty_row');
    } else {
        $(this).parent().addClass('empty_row');
    }
}

function update_view_and_remember_original_value(change_summary)
{
    console.log('update_view_and_remember_original_value method');
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];
        machine_value = split_values[2];
        category_value = split_values[3];
//        save the original value because the next line intentionally overwrites the variable in the template
        original_lemma_group = lemma_group;
        if (split_values_count > 3) {
//        only the main update_gloss and update_morpheme functions return this extra information, their sub-functions do not
            lemma_group = split_values[4];
            input_value = split_values[5];
            $(this).attr('data-value', input_value);
        }
        var id = $(this).attr('id');
        $(this).html(new_value);

        new_values_for_changes_made[id] = machine_value;

        if ($.isEmptyObject(original_values_for_changes_made[id]))
        {
            original_values_for_changes_made[id] = original_value;
            $(this).parent().removeClass('empty_row');
            $(this).attr("value", new_value);
        }
        if (new_value === '-' || new_value === ' ' || new_value === '' || new_value === 'None' ||
                        new_value === 'False' || new_value === 0 || new_value === '&nbsp;')
        {
            $(this).parent().addClass('empty_row');
            $(this).attr("value", machine_value);
            $(this).html("------");
        }
    }
}

