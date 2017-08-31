/**
 * @author Steve Cassidy, modified by Susan Even
 */

//Keep track of the original values of the changes made, so we can rewind it later if needed
var original_values_for_changes_made = new Array();

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

     $('#save_and_next_btn').click(function()
	{
		toggle_edit(true);
	});

    $('#rewind').click(function()
	{
		rewind();
	});

    handshapetypeahead($('.handshapetypeahead'));

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
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default" type="cancel">Cancel</button>';
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
		 $(this).editable(edit_post_url, {
		     type      : 'select',
		     data    : choice_lists[$(this).attr('id')],
			 callback : update_view_and_remember_original_value
		 });
     });
}

function update_view_and_remember_original_value(change_summary)
{
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
	    if (split_values_count < 2) {
	        console.log("update_view_and_remember_original_value: not enough returned values")
	        return
	    }
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];
        category_value = split_values[2];
        new_pattern = split_values[3];
        console.log('new pattern: ', new_pattern);

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

var handshape_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape/%QUERY'
    });

handshape_bloodhound.initialize();

function handshapetypeahead(target) {

     $(target).typeahead(null, {
          name: 'dutch_name',
          displayKey: 'machine_value',
          source: handshape_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(handshape) {
                  return("<p><strong>" + handshape.dutch_name +  "</strong></p>");
              }
          }
      });
};


$.editable.addInputType('handshapetypeahead', {

   element: function(settings, original) {
      var input = $('<input type="text" class="handshapetypeahead">');
      $(this).append(input);

      handshapetypeahead(input);

      return (input);
   },
});


/*
 * http://stackoverflow.com/questions/1597756/is-there-a-jquery-jeditable-multi-select-plugin
 */

$.editable.addInputType("multiselect", {
    element: function (settings, original) {
        var select = $('<select multiple="multiple" />');

        if (settings.width != 'none') { select.width(settings.width); }
        if (settings.size) { select.attr('size', settings.size); }

        $(this).append(select);
        return (select);
    },
    content: function (data, settings, original) {
        /* If it is string assume it is json. */
        if (String == data.constructor) {
            eval('var json = ' + data);
        } else {
            /* Otherwise assume it is a hash already. */
            var json = data;
        }
        for (var key in json) {
            if (!json.hasOwnProperty(key)) {
                continue;
            }
            if ('selected' == key) {
                continue;
            }
            var option = $('<option />').val(key).append(json[key]);
            $('select', this).append(option);
        }

        if ($(this).val() == json['selected'] ||
                            $(this).html() == $.trim(original.revert)) {
            $(this).attr('selected', 'selected');
        }

        /* Loop option again to set selected. IE needed this... */
        $('select', this).children().each(function () {
            if (json.selected) {
                var option = $(this);
                $.each(json.selected, function (index, value) {
                    if (option.val() == value) {
                        option.attr('selected', 'selected');
                    }
                });
            } else {
                if (original.revert.indexOf($(this).html()) != -1)
                    $(this).attr('selected', 'selected');
            }
        });
    }
});


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) { // >
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


function post_key_and_value_after_n_seconds(key_to_post,value_to_post,n_seconds)
{
	setTimeout(function()
	{
		$.ajax({
		  type: "POST",
		  url: edit_post_url,
		  data: {'id':key_to_post,'value':'_'+value_to_post},
		});

	},n_seconds)
}

function delayed_reload(n_seconds)
{
	setTimeout(function()
	{
		location.reload();
	},n_seconds);
}

function rewind()
{
	var c = 1;

	for (key in original_values_for_changes_made)
	{
		value = original_values_for_changes_made[key];
		post_key_and_value_after_n_seconds(key,value,c*100);
		c++;
	}

	delayed_reload(c*100);

}

