/**
 * @author Steve Cassidy
 */
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
         
     }  
          
     $('#enable_edit').click(toggle_edit);
     
     glosstypeahead($('.glosstypeahead'));


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
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');
    $('#add_definition').hide();
    $('#add_relation_form').hide();
    $('#add_relationtoforeignsign_form').hide();
    $('#add_morphologydefinition_form').hide();
    $('.definition_delete').hide();
    $('.relation_delete').hide();
    $('.relationtoforeignsign_delete').hide();
    $('.morphology-definition-delete').hide();
};

function enable_edit() {
    $('.edit').editable('enable');
    $('.edit').css('color', 'red');
    $('#edit_message').text('Click on red text to edit  '); 
    $('.editform').show();
    $('#delete_gloss_btn').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');
    $('#add_definition').show();
    $('#add_relation_form').show();
    $('#add_relationtoforeignsign_form').show();
    $('#add_morphologydefinition_form').show();
    $('.definition_delete').show();
    $('.relation_delete').show();
    $('.relationtoforeignsign_delete').show();
    $('.morphology-definition-delete').show();
};

function toggle_edit() {
    if ($('#enable_edit').hasClass('edit_enabled')) {
        disable_edit();
        $('#enable_edit').removeClass('edit_enabled');
        $('#enable_edit').text('Edit');
    } else {
        enable_edit();
        $('#enable_edit').addClass('edit_enabled');
        $('#enable_edit').text('Save');
    }
}


function delete_gloss() {
    alert("Delete this gloss?");
}

$.editable.addInputType('positiveinteger', {
    element : function(settings, original) {
        var input = $('<input type="number" min="0">');
        $(this).append(input);
        return(input);
    }
});


function configure_edit() {
    
    $.fn.editable.defaults['indicator'] = 'Saving...';
    $.fn.editable.defaults['tooltip'] = 'Click to edit...';
    $.fn.editable.defaults['placeholder'] = '-';
    $.fn.editable.defaults['submit'] = '<button class="btn btn-primary" type="submit">Ok</button>';
    $.fn.editable.defaults['cancel'] = '<button class="btn btn-default" type="cancel">Cancel</button>';
    $.fn.editable.defaults['width'] = 'none';
    $.fn.editable.defaults['height'] = 'none';
    $.fn.editable.defaults['submitdata'] = {'csrfmiddlewaretoken': csrf_token};
    $.fn.editable.defaults['onerror']  = function(settings, original, xhr){
                          alert("There was an error processing this change: " + xhr.responseText );
                          original.reset();
                        };
     
    
     $('.edit_text').editable(edit_post_url);    
     $('.edit_int').editable(edit_post_url, {
         type      : 'positiveinteger',
         onerror : function(settings, original, xhr){
                          alert(xhr.responseText);
                          original.reset();
                    },
     });
     $('.edit_area').editable(edit_post_url, { 
         type      : 'textarea'
     });
     $('.edit_role').editable(edit_post_url, { 
         type      : 'select',
         data      : definition_role_choices
     });
     $('.edit_language').editable(edit_post_url, {
         type      : 'multiselect',
         data      : languages
     });
     $('.edit_dialect').editable(edit_post_url, {
         type      : 'multiselect',
         data      : dialects
     });     
     $('.edit_check').editable(edit_post_url, {
         type      : 'checkbox',
         checkbox: { trueValue: 'Yes', falseValue: 'No' }
     });
     $('.edit_handshape').editable(edit_post_url, {
         type      : 'select',
         data      : handshape_choices
     });
     $('.edit_location').editable(edit_post_url, {
         type      : 'select',
         data      : location_choices
     });
     $('.edit_palm').editable(edit_post_url, {
         type      : 'select',
         data      : palm_orientation_choices
     });
     $('.edit_relori').editable(edit_post_url, {
         type      : 'select',
         data      : relative_orientation_choices
     }); 
     $('.edit_sec_location').editable(edit_post_url, {
         type      : 'select',
         data      : secondary_location_choices
     });                  
     $('.edit_relation_role').editable(edit_post_url, {
         type      : 'select',
         data      : relation_role_choices
     }); 
     $('.edit_relation_target').editable(edit_post_url, {
         type      : 'glosstypeahead'
     });
     $('.edit_morpheme').editable(edit_post_url, {
         type      : 'glosstypeahead'
     });
     $('.edit_morphology_role').editable(edit_post_url, {
         type      : 'select',
         data      : choice_lists['morphology_role']
     });
     $('.edit_list').click(function() 
	 {
		 $(this).editable(edit_post_url, {
		     type      : 'select',
		     data    : choice_lists[$(this).attr('id')] 
		 });


     });

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
                  return("<p><strong>" + gloss.idgloss + "</strong> (SN: " + gloss.sn + ")</p>");
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
    
    
     


      
      
