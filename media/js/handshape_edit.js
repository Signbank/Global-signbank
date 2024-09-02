/**
 * @author Steve Cassidy, modified by Susan Even
 */

//Keep track of the original values of the changes made, so we can rewind it later if needed
var original_values_for_changes_made = new Array();

function update_view_and_remember_original_value(change_summary)
{
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
	    if (split_values_count < 3) {
	        console.log("update_view_and_remember_original_value: not enough returned values")
	        return
	    }
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];
        category_value = split_values[2];
        new_pattern = split_values[3];

        id = $(this).attr('id');
        $(this).html(new_value);

        if (original_values_for_changes_made[id] == undefined)
        {
            original_values_for_changes_made[id] = original_value;
            if (id != 'fsT' && id != 'fsI' && id != 'fsM' && id != 'fsR' && id != 'fsP'
                && id != 'fs2T' && id != 'fs2I' && id != 'fs2M' && id != 'fs2R' && id != 'fs2P'
                && id != 'ufT' && id != 'ufI' && id != 'ufM' && id != 'ufR' && id != 'ufP') {
                $(this).parent().removeClass('empty_row');
                $(this).parent().attr("value", new_value);
            }
        }
        if (new_value == '-' || new_value == ' ' || new_value == '' || new_value == 'None')
        {
            $(this).parent().addClass('empty_row');
            $(this).parent().attr("value", new_value);
            $(this).html("------");
        }
        if (category_value == 'fingerSelection1') {
            var fs = document.getElementById('#fingerSelection1');
            fs.innerHTML = new_pattern;
        }
        else if (category_value == 'fingerSelection2') {
            var fs2 = document.getElementById('#otherFingerSection');
            fs2.innerHTML = new_pattern;
        }
        else if (category_value == 'unselectedFingers') {
            var uf = document.getElementById('#unselectedFingers');
            uf.innerHTML = new_pattern;
        }
    }
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

    $('#rewind').click(function()
	{
		rewind();
	});

    // setup requried for Ajax POST
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

function disable_edit() {
    $('.edit').editable('disable');
    $('.edit').css('color', 'black');
    $('#edit_message').text('');
    $('.editform').hide();
    $('.button-to-appear-in-edit-mode').hide();
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');

    $('.empty_row').hide();

    //To prevent RSI
    $('.edit').each(function()
    {
        if ($(this).html() == '------')
        {
            $(this).html('-');
        }
    });

    $('input').each(function()
    {
        $(this).html('-')
    });
};

function enable_edit() {
    $('.edit').editable('enable');
    $('.edit').css('color', 'red');
    $('#edit_message').text('Click on red text to edit  ');
    $('#edit_message').css('color', 'black');
    $('.editform').show();
    $('.button-to-appear-in-edit-mode').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');

    $('.empty_row').show();

    //To prevent RSI
    $('.edit').each(function()
    {
        if ($(this).html() == '-')
        {
            $(this).html('------')
        }
    });
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


$.editable.addInputType('positiveinteger', {
    element : function(settings, original) {
        var input = $('<input type="number" min="0">');
        $(this).append(input);
        return(input);
    }
});


function configure_edit() {

    $.fn.editable.defaults['indicator'] = saving_str;
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" type="submit">Ok</button>';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default btn-default-light" style="" type="cancel">Cancel</button>';
    $.fn.editable.defaults['width'] = 'none';
    $.fn.editable.defaults['height'] = 'none';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr)
                        {
                            if (xhr.responseText.indexOf('UNIQUE constraint failed') > -1)
                            {
                                alert("UNIQUE constraint failed");
                            }
                            else
                            {
                                alert("There was an error processing this change: " + xhr.responseText );
                            }
                              original.reset();
                        };


     $('.edit_text').editable(edit_post_url, {
		 callback : update_view_and_remember_original_value
	 });
     $('.edit_int').editable(edit_post_url, {
         type      : 'positiveinteger',
         onerror : function(settings, original, xhr){
                          alert(xhr.responseText);
                          original.reset();
                    },
		 callback : update_view_and_remember_original_value
     });
     $('.edit_area').editable(edit_post_url, {
         type      : 'textarea',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_check').editable(edit_post_url, {
         type      : 'checkbox',
         checkbox: { trueValue: 'True', falseValue: 'False' },
		 callback : update_view_and_remember_original_value
     });
     $('.edit_list').click(function()
	 {
	     var this_data = $(this).attr('value');
	     var edit_list_choices = choice_lists[$(this).attr('id')];
	     var index_of_modified_field = '_0';
         for (var key in edit_list_choices) {
            var value = edit_list_choices[key];
            if (value == this_data) {
                index_of_modified_field = key;
                break;
            }
         };
		 $(this).editable(edit_post_url, {
		     params : { a: index_of_modified_field },
		     type      : 'select',
		     data    : choice_lists[$(this).attr('id')],
			 callback : update_view_and_remember_original_value
		 });
     });
}









