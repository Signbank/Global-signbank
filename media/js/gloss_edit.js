/**
 * @author Steve Cassidy
 */

//Keep track of the original values of the changes made, so we can rewind it later if needed
var original_values_for_changes_made = new Array();

 $(document).ready(function() {
     configure_edit();
     
     disable_edit();
    

     if (window.location.search.match('edit')) {
         toggle_edit();

         if (window.location.search.match('editrelforeign')) {
             $('#relationsforeign').addClass('in');
         }         
         else if (window.location.search.match('editrel')) {
             $('#relations').addClass('in');
         }

         if (window.location.search.match('editdef')) {
             $('#definitions').addClass('in');
         }      

         if (window.location.search.match('editmorphdef')) {
             $('#morphology').addClass('in');
         }      

         if (window.location.search.match('editothermedia')) {
             $('#othermedia').addClass('in');
         }
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

    glosstypeahead($('.glosstypeahead'));
    morphtypeahead($('.morphtypeahead'));


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

    ajaxifyTagForm();
     
 });

function disable_edit() {
    $('.edit').editable('disable');
    $('.edit').css('color', 'black');
    $('#edit_message').text(''); 
    $('.editform').hide();
    $('#delete_gloss_btn').hide();
    $('#delete_morpheme_btn').hide();
    $('.button-to-appear-in-edit-mode').hide();
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');
    $('#add_definition').hide();
    $('#add_relation_form').hide();
    $('#add_relationtoforeignsign_form').hide();
    $('#add_morphologydefinition_form').hide();
    $('#add_other_media').hide();
    $('#add_component').hide();
    $('#add_morphemedefinition_form').hide();
    $('.definition_delete').hide();
    $('.relation_delete').hide();
    $('.other-video-delete').hide();
    $('.relationtoforeignsign_delete').hide();
    $('.morphology-definition-delete').hide();
    $('.morpheme-definition-delete').hide();

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
    $('.editform').show();
    $('#delete_gloss_btn').show().addClass('btn-danger');
    $('#delete_morpheme_btn').show().addClass('btn-danger');
    $('.button-to-appear-in-edit-mode').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');
    $('#add_definition').show();
    $('#add_relation_form').show();
    $('#add_relationtoforeignsign_form').show();
    $('#add_morphologydefinition_form').show();
    $('#add_other_media').show();
    $('#add_component').show();
    $('#add_morphemedefinition_form').show();
    $('.definition_delete').show();
    $('.relation_delete').show();
    $('.other-video-delete').show();
    $('.relationtoforeignsign_delete').show();
    $('.morphology-definition-delete').show();
    $('.morpheme-definition-delete').show();

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

		if (redirect_to_next)
		{
		    // Check if this is a gloss or a morpheme
		    if (!next_gloss_id || next_gloss_id === undefined)
		    {
			    window.location.href = '/dictionary/morpheme/'+next_morpheme_id;
		    } else {
			    window.location.href = '/dictionary/gloss/'+next_gloss_id;
		    }
		}

    } else {
        enable_edit();
        $('#enable_edit').addClass('edit_enabled');
        $('#enable_edit').text(turn_off_edit_mode_str);
    }
}


function delete_gloss() {
    alert(delete_this_gloss_str);
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
                                alert(idgloss_already_exists_str);
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
     $('.edit_role').editable(edit_post_url, { 
         type      : 'select',
         data      : definition_role_choices,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_language').editable(edit_post_url, {
         type      : 'multiselect',
         data      : languages,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_dialect').editable(edit_post_url, {
         type      : 'multiselect',
         data      : dialects,
		 callback : update_view_and_remember_original_value
     });     
     $('.edit_check').editable(edit_post_url, {
         type      : 'checkbox',
         checkbox: { trueValue: 'Yes', falseValue: 'No' },
		 callback : update_view_and_remember_original_value
     });
     $('.edit_relation_role').editable(edit_post_url, {
         type      : 'select',
         data      : relation_role_choices,
		 callback : update_view_and_remember_original_value
     }); 
     $('.edit_relation_target').editable(edit_post_url, {
         type      : 'glosstypeahead',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_compoundpart').editable(edit_post_url, {
         type      : 'glosstypeahead',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_morpheme').editable(edit_post_url, {
         type      : 'morphtypeahead',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_mrptype').editable(edit_post_url, {
         type      : 'select',
         data      : mrptype_choices,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_wordclass').editable(edit_post_url, {
         type      : 'select',
         data      : wordclass_choices,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_morphology_role').editable(edit_post_url, {
         type      : 'select',
         data      : choice_lists['morphology_role'],
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
	split_values = change_summary.split('\t');
	original_value = split_values[0];
  	new_value = split_values[1];
	id = $(this).attr('id');
  	$(this).html(new_value);

	if (original_values_for_changes_made[id] == undefined)
  	{
    	original_values_for_changes_made[id] = original_value;                          
		console.log(original_values_for_changes_made); 
	}
}

var gloss_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: '/dictionary/ajax/gloss/%QUERY'
    });

gloss_bloodhound.initialize();

function glosstypeahead(target) {

     $(target).typeahead(null, {
          name: 'glosstarget',
          displayKey: 'pk',
          source: gloss_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  // Issue #121: remove  (SN: " + gloss.sn + ")
                  return("<p><strong>" + gloss.idgloss +  "</strong></p>");
              }
          }
      });
};


$.editable.addInputType('glosstypeahead', {
    
   element: function(settings, original) {
      var input = $('<input type="text" class="glosstypeahead">');
      $(this).append(input);
     
      glosstypeahead(input); 

      return (input);
   }, 
});

/*
 *  Mimic the 'gloss' typeahead facility for 'morpheme', which is a subset of the glosses
 *  (as defined by the 'Morpheme' model, which takes Gloss as basis)
 */

var morph_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: '/dictionary/ajax/morph/%QUERY'
    });

morph_bloodhound.initialize();

function morphtypeahead(target) {

     $(target).typeahead(null, {
          name: 'morphtarget',
          displayKey: 'pk',
          source: morph_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  // Issue #121: remove (SN: " + gloss.sn + ")
                  return("<p><strong>" + gloss.idgloss + "</strong></p>");
              }
          }
      });
};


$.editable.addInputType('morphtypeahead', {

   element: function(settings, original) {
      var input = $('<input type="text" class="morphtypeahead">');
      $(this).append(input);

      morphtypeahead(input);

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

    
function ajaxifyTagForm() {
    // ajax form submission for tag addition and deletion
    $('.tagdelete').click(function() {
        var action = $(this).attr('href');
        var tagid = $(this).attr('id');
        var tagelement = $(this).parents('.tagli');
        
        $.post(action, 
              {tag: tagid, 'delete': "True" }, 
               function(data) {
                    if (data == 'deleted') {
                        // remove the tag from the page 
                       tagelement.remove();
                    }
               });
        
        return false;
    });
    
    $('#tagaddform').submit(function(){
        
        var newtag = $('#tagaddform select').val();
        
        if (newtag != "") {
            $.post($(this).attr('action'), $(this).serialize(),
                    function(data) {
                       // response is a new tag list
                       $('#tags').replaceWith(data);
                       ajaxifyTagForm();
                   });
        } else {
            alert("Please select a tag value.");
        }
        
        return false;
    });
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
