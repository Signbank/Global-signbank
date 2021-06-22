/**
 * @author Steve Cassidy
 */

function swap(json){
  var ret = {};
  for(var key in json){
    ret[json[key]] = key;
  }
  return ret;
};

//Keep track of the original values of the changes made, so we can rewind it later if needed
//Keep track of the new values in order to generate hyperlinks for Handshapes
var original_values_for_changes_made = new Array();
var new_values_for_changes_made = new Array();
var busy_editing = 0;

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
    $('.glosstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk)
        });
    $('.glosstypeahead').on("input", function() {
          $(this).parent().next().val("")
        });
    morphtypeahead($('.morphtypeahead'));
    $('.morphtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk)
        });
    $('.morphtypeahead').on("input", function() {
          $(this).parent().next().val("")
        });
    lemmatypeahead($('.lemmatypeahead'));
    $('.lemmatypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk)
        });
    $('.lemmatypeahead').on("input", function() {
          $(this).parent().next().val("")
        });


    // a lot of console logging has been added to show events the user presses
    // this is needed to help check different browsers
    for (var i = 0; i < morpheme_phonology.length; i++) {
        var field = morpheme_phonology[i];
        var field_ref = '#' + morpheme_phonology[i];

        $(field_ref).on("customEvent", function(e) {
            var target = $(e.target);
            var this_field_name = $(target).attr("id");
            var classname = $(target).attr("class");
            $(target).clearQueue();
//            console.log('customEvent on '+this_field_name+' type '+e.type+' triggers select on '+this_field_name);
            if (phonology_list_kinds.includes(this_field_name)) {
                // for phonology pulldown lists do this to get list open
                $(target).focus().click().click();
            } else {
                $(target).preventDefault();
                $(target).click();
            };
        });
        var this_field_node = document.getElementById(field);

        this_field_node.addEventListener("keyup", function(e) {
            var target = $(e.target);
            var field_value = $(target).parent().parent().attr("value");
            var field = $(target).parent().parent().attr("id");
            var targetNodeName = e.target.nodeName;
            var this_element = $(this);
            var this_value = $(this_element).attr("value");

//            console.log('field '+field+' key pressed '+e.keyCode+' nodeName '+targetNodeName+' value '+field_value+' option value '+this_value);
            if (e.keyCode === 13) { // 'return'
                e.preventDefault();
                if (targetNodeName != 'INPUT') {
                    $(target).submit();
                };
            }
        });
    };


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
    //$('#affix-bar').show(); // The affix bar appears on top of the Delete modal popup window, so it is hidden during editting
    $('.edit').editable('disable');
    $('.edit').css('color', 'black');
    $('#edit_message').text('');
    if (busy_editing) {
//        console.log('stop editing');
        new_lemma_group = $('#idgloss').text();
        new_lemma_group_value = new_values_for_changes_made['idgloss'];
        original_lemma_group_value = original_values_for_changes_made['idgloss'];
        if (new_lemma_group_value == undefined) {
            if (original_lemma_group_url) {
                $('#idgloss').html('<a href="' + original_lemma_group_url + '">' + original_lemma_group_value + '</a>')
            }
        } else {
            if (lemma_group == 'True') {
                new_lemma_group_url = url + 'signs/search/?search_type=sign&view_type=lemma_groups&lemmaGloss=%5E' + new_lemma_group + '%24'
                $('#idgloss').html('<a href="' + new_lemma_group_url + '">' + new_lemma_group + '</a>')
            }
        }
    };
    $('.editform').hide();
    $('.button-to-appear-in-edit-mode').hide();
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');
    $('#add_definition').hide();
    $('#add_relation_form').hide();
    $('#add_relationtoforeignsign_form').hide();
    $('#add_morphologydefinition_form').hide();
    $('#add_blenddefinition_form').hide();
    $('#add_other_media').hide();
    $('#add_component').hide();
    $('#add_morphemedefinition_form').hide();
    $('.definition_delete').hide();
    $('.relation_delete').hide();
    $('.other-video-delete').hide();
    $('.relationtoforeignsign_delete').hide();
    $('.morphology-definition-delete').hide();
    $('.morpheme-definition-delete').hide();
    $('.blend-definition-delete').hide();

    $('.empty_row').hide();

    hideLemmaForm($("#lemma"));
    $("#lemma a").show();

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

    check_phonology_modified();

    busy_editing = false;
};

function enable_edit() {
    $('.edit').editable('enable');
    $('.edit').css('color', 'red');
    $('#edit_message').text('Click on red text to edit  ');
    $('#edit_message').css('color', 'black');
    lemma_group_text = $('#idgloss').text();
    $('#idgloss').children().remove();
    $('#idgloss').html(lemma_group_text);
    $('.editform').show();
    $('.button-to-appear-in-edit-mode').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');
    $('#add_definition').show();
    $('#add_relation_form').show();
    $('#add_relationtoforeignsign_form').show();
    $('#add_morphologydefinition_form').show();
    $('#add_blenddefinition_form').show();
    $('#add_other_media').show();
    $('#add_component').show();
    $('#add_morphemedefinition_form').show();
    $('.definition_delete').show();
    $('.relation_delete').show();
    $('.relation_delete').css('color', 'black');
    $('.other-video-delete').show();
    $('.relationtoforeignsign_delete').show();
    $('.relationtoforeignsign_delete').css('color', 'black');
    $('.morphology-definition-delete').show();
    $('.morpheme-definition-delete').show();
    $('.blend-definition-delete').show();

    $('.empty_row').show();

    //To prevent RSI
    $('.edit').each(function()
    {
        if ($(this).html() == '-' || $(this).html() == '&nbsp;')
        {
            $(this).html('------')
        }
    });
    busy_editing = 1;
//    console.log('start editing');
    $('#lemma a').hide();
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
			    window.location.href = url + '/dictionary/morpheme/'+next_morpheme_id;
		    } else {
			    window.location.href = url + '/dictionary/gloss/'+next_gloss_id;
		    }
		}

    } else {
        enable_edit();
        $('#enable_edit').addClass('edit_enabled');
        $('#enable_edit').text(turn_off_edit_mode_str);
    }

    $('#lemma').css('color', $('.edit').css('color'));
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
    $.fn.editable.defaults['cssclass'] = 'preview';
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
		 callback : update_view_and_remember_original_value
	 });
     $('.edit_int').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'positiveinteger',
         onerror : function(settings, original, xhr){
                          alert(xhr.responseText);
                          original.reset();
                    },
		 callback : update_view_and_remember_original_value
     });
     $('.edit_area').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'textarea',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_role').editable(edit_post_url, {
         params : { a: swap(definition_role_choices)[$(this).attr('value')] },
         type      : 'select',
         data      : definition_role_choices,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_dialect').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'multiselect',
         data      : dialects,
		 callback : update_view_and_remember_original_value
     });
     $('.edit_check').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'checkbox',
         checkbox: { trueValue: yes_str, falseValue: no_str },
		 callback : update_view_and_remember_original_value
     });
     $('.edit_relation_target').editable(edit_post_url, {
         params : { a: 0 },
         type      : 'glosstypeahead',
		 callback : update_view_and_remember_original_value
     });
     $('.edit_relation_delete').editable(edit_post_url, {
        params : { a: "delete",
                   field: $(this).attr('id'),
                   choices: relation_delete_choices,
                   colors: relation_delete_choices_colors },
        type    : 'select',
        data    : relation_delete_choices,
        callback : update_relation_delete
     });
     $('.edit_foreign_delete').editable(edit_post_url, {
        params : { a: "delete",
                   field: $(this).attr('id'),
                   choices: relation_delete_choices,
                   colors: relation_delete_choices_colors },
        type    : 'select',
        data    : relation_delete_choices,
        callback : update_foreign_delete
     });
     $('.edit_mrptype').editable(edit_post_url, {
         params : { a: swap(morph_type)[$(this).attr('value')],
                    field: 'mrpType',
                    choices: morph_type,
                    colors: morph_type_colors },
         type      : 'select',
         data      : morph_type,
		 callback : update_view_and_remember_original_value
     });

     $('.edit_list').click(function()
	 {
	     var this_data = $(this).attr('value');
	     var edit_list_choices = static_choice_lists[$(this).attr('id')];
	     var edit_list_choice_colors = static_choice_list_colors[$(this).attr('id')];

	     var index_of_modified_field = '_0';
         for (var key in edit_list_choices) {
            var value = edit_list_choices[key];
            if (value == this_data) {
                index_of_modified_field = key;
                break;
            }
         };
		 $(this).editable(edit_post_url, {
		     params : { a: index_of_modified_field,
		                field: $(this).attr('id'),
		                display: $(this).attr('value'),
		                colors: edit_list_choice_colors,
		                choices: edit_list_choices },
		     type      : 'select',
		     data    : choice_lists[$(this).attr('id')],
			 callback : update_view_and_remember_original_value
		 });
     });
}


function openDropdown(elementId) {
    function down() {
//        console.log('inside down');
        var pos = $(this).offset();
        var len = $(this).find("option").length;
            if(len > 20) {
                len = 20;
            }
        $(this).css("position", "absolute");
        $(this).css("zIndex", 9999);
        $(this).offset(pos);
        $(this).attr("size", len);
        $(this).unbind("focus", down);
        $(this).focus();
    }
    function up() {
//        console.log('inside up');
        $(this).css("position", "static");
        $(this).attr("size", "1");
        $(this).unbind("change", up);
        $(this).focus();
    }
//    console.log('inside openDropdown: ' + elementId);
    $("#" + elementId).focus(down).blur(up).focus();
//    $(elementId).focus(down).blur(up).focus();
}

function hide_other_forms(focus_field) {
    for (var i = 0; i < morpheme_phonology.length; i++) {
        var field = morpheme_phonology[i];
        var field_ref = '#' + morpheme_phonology[i];
        if (field != focus_field) {
            var other_field = document.getElementById(field);
            var forms = other_field.getElementsByTagName('form');
            for (let form of forms) {
                var buttons = form.getElementsByTagName('button');
                for (let button of buttons) {
                    buttonType = button.getAttribute('type');
                    if (buttonType == 'cancel') {
                        button.click();
                    }
                };
            };
        };
    };
};

function update_view_and_remember_original_value(change_summary)
{
//    console.log('update_view_and_remember_original_value change_summary: '+change_summary);
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
	    if (split_values_count < 3) {
//	        # updates to Sign Language or Dialect returns two values
            split_values = change_summary.split('\t');
            language = split_values[0];
            dialect = split_values[1];
            if (language) {
                $('#signlanguage').html(language);
            } else {
                $('#signlanguage').html("------");
            }
            if (dialect) {
                $('#dialect').html(dialect);
            } else {
                $('#dialect').html("------");
            }
	        return
	    }
        split_values = change_summary.split('\t');
        original_value = split_values[0];
        new_value = split_values[1];
        machine_value = split_values[2];
        category_value = split_values[3];
//        console.log('original_value: '+original_value);
//        console.log('new_value: '+new_value);
//        console.log('machine_value: '+machine_value);
//        console.log('category_value: '+category_value);

//        save the original value because the next line intentionally overwrites the variable in the template
        original_lemma_group = lemma_group;
        if (split_values_count > 3) {
//        only the main update_gloss and update_morpheme functions return this extra information, their sub-functions do not
            lemma_group = split_values[4];
        }

        id = $(this).attr('id');

//        if (category_value != 'phonology') {
        $(this).html(new_value);
//        } else {
//            var display_value = new_value.toString("utf8");
////            console.log('display value: '+display_value);
//            $(this).html(display_value);
//        }

        new_values_for_changes_made[id] = machine_value;
        if (new_value == '&nbsp;') {
            new_value = 'False';
        }

        if (original_values_for_changes_made[id] == undefined)
        {
            original_values_for_changes_made[id] = original_value;
            $(this).parent().removeClass('empty_row');
            $(this).attr("value", new_value);
        }
        if (new_value == '-' || new_value == ' ' || new_value == '' || new_value == 'None' ||
                        new_value == 'False' || new_value == 0 || new_value == '&nbsp;')
        {
//            console.log('new value is empty or False')
            if (id == 'idgloss') {
//                the user tried to erase the Lemma ID Gloss field, reset it in the template to what it was
                $(this).html(original_value);
                lemma_group = original_lemma_group;
            } else {
                $(this).parent().addClass('empty_row');
                $(this).html("------");
            }
        }
        if (category_value == 'phonology') {
//            console.log('phonology modified '+id);
           // $(this).change();
            $(this).attr("value", new_value);
            var index_of_modified_field = morpheme_phonology.indexOf(id);
            var next_field_index = index_of_modified_field+1;
            if (next_field_index < morpheme_phonology.length) {
                var next_field = morpheme_phonology[next_field_index];
                var next_field_ref = '#'+next_field;
                $(next_field_ref).clearQueue();
                if (phonology_list_kinds.includes(next_field)) {
                    // for lists, do custom event instead of click
//                    console.log('customEvent on '+next_field_ref);
                    $(next_field_ref).triggerHandler("customEvent"); //.focus().click().click();
                } else {
//                    console.log('click event on '+next_field_ref);
                    $(next_field_ref).click();
                };
            }
        }
    }
}

var gloss_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/gloss/%QUERY'
    });

gloss_bloodhound.initialize();

function glosstypeahead(target) {

     $(target).typeahead(null, {
          name: 'glosstarget',
          displayKey: 'annotation_idgloss',
          source: gloss_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  // Issue #121: remove  (SN: " + gloss.sn + ")
                  return("<p><strong>" + gloss.annotation_idgloss +  "</strong></p>");
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
      remote: url+'/dictionary/ajax/morph/%QUERY'
    });

morph_bloodhound.initialize();

function morphtypeahead(target) {

     $(target).typeahead(null, {
          name: 'morphtarget',
          displayKey: 'annotation_idgloss',
          source: morph_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  // Issue #121: remove (SN: " + gloss.sn + ")
                  return("<p><strong>" + gloss.annotation_idgloss + "</strong></p>");
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

var lemma_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+gloss_default_language_code+'/%QUERY'
    });

lemma_bloodhound.initialize();

function lemmatypeahead(target) {

     $(target).typeahead(null, {
          name: 'lemmatarget',
          displayKey: 'lemma',
          source: lemma_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(lemma) {
                  return("<p><strong>" + lemma.lemma + "</strong></p>");
              }
          }
      });
};


$.editable.addInputType('lemmatypeahead', {

   element: function(settings, original) {
      var input = $('<input type="text" class="lemmatypeahead">');
      $(this).append(input);

      lemmatypeahead(input);

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

function update_foreign_delete(change_summary)
{
    var deleted_relation_for_gloss = $(this).attr('id');
    var deleted_relation = deleted_relation_for_gloss.split('_');
    var deleted_relation_id = deleted_relation[1];
    $(this).css("color", "black");
    console.log("Delete foreign relation: ", deleted_relation_id);
    var search_id = 'foreign_' + deleted_relation_id;
    $(document.getElementById(search_id)).replaceWith("<tr id='" + search_id + "' class='empty_row' style='display: none;'>" + "</tr>");
  	$(this).html('');
    $('#relationsforeign').addClass('in');
}

function update_relation_delete(change_summary)
{
    var deleted_relation_for_gloss = $(this).attr('id');
    var deleted_relation = deleted_relation_for_gloss.split('_');
    var deleted_relation_id = deleted_relation[1];
    $(this).css("color", "black");
    console.log("Delete relation: ", deleted_relation_id);
    var search_id = 'row_' + deleted_relation_id;
    $(document.getElementById(search_id)).replaceWith("<tr id='" + search_id + "' class='empty_row' style='display: none;'>" + "</tr>");
  	$(this).html('');
  	$('#relations').addClass('in');
}

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

function check_phonology_modified()
{
    var phonology_keys = morpheme_phonology;
    for (key in original_values_for_changes_made)
    {
        for (var i = 0; i < phonology_keys.length; i++) {
            if (phonology_keys[i] == key)
            {
	            $(document.getElementById('edit_message')).text('The phonology has been changed, please remember to reload the page when finished editing!');
	            $(document.getElementById('edit_message')).css('color', 'red');
            }
        }
    }
}

// Lemma toggle stuff
function showLemmaForm(lemma_element) {
    lemma_element.hide();
    lemma_element.parent().find("[name='add_lemma_form']").hide();
    lemma_element.parent().find("[name='set_lemma_form']").show();
    lemma_element.parent().find("[name='add_lemma_form']").find(".lemmatypeahead.tt-input").focus();
}

function hideLemmaForm(lemma_element) {
    lemma_element.parent().find("[name='set_lemma_form']").hide();
    lemma_element.parent().find("[name='add_lemma_form']").hide();
    lemma_element.show();
}

$("#lemma").on('click', function() {
    if(busy_editing) {
        showLemmaForm($(this));
    }
});

$(".lemma-form-dismiss").on('click', function() {
    hideLemmaForm($("#lemma"));
});

function showAddLemma() {
    $("#lemma").hide();
    $("#lemma").parent().find("[name='set_lemma_form']").hide();
    $("#lemma").parent().find("[name='add_lemma_form']").show();
    return false;
}
