
var busy_editing = 0;
var original_values_for_changes_made = new Array();

$(document).ready(function() {

    if (window.location.search.match('manage')) {

        target_manage = '#' + window.location.search.split("?")[1];

        if (window.location.search.match('manage_view')) {
            $(target_manage).addClass('in');
        }

        if (window.location.search.match('manage_change')) {
            $(target_manage).addClass('in');
        }
    }

    configure_edit();

    disable_edit();

    if (window.location.search.match('edit')) {
        toggle_edit();

    }

    $('#enable_edit').click(function()
    {
        toggle_edit();
    });

    usertypeahead($('.usertypeahead'));
    $('.usertypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.username)
        });
    $('.usertypeahead').on("input", function() {
          $(this).parent().next().val("")
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
    //$('#affix-bar').show(); // The affix bar appears on top of the Delete modal popup window, so it is hidden during editting
    $('.edit').editable('disable');
    $('.edit').css('color', 'black');
    $('#edit_message').text('');
    if (busy_editing) {

    };

    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');

    $('.empty_row').hide();

    //To prevent RSI
    $('.edit').each(function()
    {
        if ($(this).html() == '------')
        {
            id = $(this).attr('id');

            $(this).html('-');
        }
    });

    $('input').each(function()
    {
        $(this).html('-')
    });
};


function enable_edit() {
    //$('#affix-bar').hide(); // The affix bar appears on top of the Delete modal popup window, so it is hidden during editting
    $('.edit').editable('enable');
    $('.edit').css('color', 'red');
    $('#edit_message').text('Click on red text to edit  ');
    $('#edit_message').css('color', 'black');

    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');

    $('.empty_row').show();

    //To prevent RSI
    $('.edit').each(function()
    {
        if ($(this).html() == '-' || $(this).html() == '&nbsp;')
        {
            $(this).html('')
        }
    });
    busy_editing = 1;
};


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


function configure_edit() {

    $.fn.editable.defaults['indicator'] = saving_str;
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" type="submit">Save</button>';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default" type="cancel">Cancel</button>';
    $.fn.editable.defaults['cols'] = '80';
    $.fn.editable.defaults['rows'] = '5';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr)
                        {

                            alert("There was an error processing this change: " + xhr.responseText );
                            original.reset();
                        };


     $('.edit_text').editable(edit_post_url, {
		 callback : update_view_and_remember_original_value
	 });
     $('.edit_area').editable(edit_post_url, {
         type      : 'textarea',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_check').editable(edit_post_url, {
         type      : 'checkbox',
         checkbox: { falseValue: 'False', trueValue: 'True'  },
		 callback : update_view_and_remember_original_value
     });
}

function update_view_and_remember_original_value(change_summary)
{
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];

        id = $(this).attr('id');
        $(this).html(new_value);

        if (original_values_for_changes_made[id] == undefined)
        {
            original_values_for_changes_made[id] = original_value;
            $(this).parent().removeClass('empty_row');
            $(this).parent().attr("value", new_value);
        }
        if (new_value == '-' || new_value == ' ' || new_value == '' || new_value == 'None' || new_value == 0 )
        {
            console.log("new value is empty, new value is: ", new_value);
            $(this).parent().attr("value", original_value);
            $(this).html(original_value);
        }
    }
}

var user_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/user/%QUERY'
});

user_bloodhound.initialize();

function usertypeahead(target) {

     $(target).typeahead(null, {
          name: 'username',
          displayKey: 'username',
          source: user_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(user) {
                  return("<p>" + user.first_name + " " + user.last_name + " (<strong>" + user.username + "</strong>)</p>");
              }
          }
      });
};
