
var busy_editing = false;

// bloodhounds for field choices

var handedness_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handedness'+'/%QUERY'
    });

handedness_bloodhound.initialize();

function handednesstypeahead(target) {

     $(target).typeahead(null, {
          name: 'handedness',
          displayKey: 'name',
          source: handedness_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

var domhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

domhndsh_bloodhound.initialize();

function domhndshtypeahead(target) {

     $(target).typeahead(null, {
          name: 'domhndsh',
          displayKey: 'name',
          source: domhndsh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};


// last of the field choice bloodhounds

var selected_semField = [];

var semField_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/semField'+'/%QUERY'
    });

semField_bloodhound.initialize();

function semFieldtypeahead(target) {

     $(target).typeahead(null, {
          name: 'semField',
          displayKey: 'name',
          source: semField_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

function renderSelected() {
    var container = $('#semField_value');
    container.empty();
    var values_input = $('#semField_hidden_input_values');
    values_input.empty();
    selected_semField.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="semField" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp; &nbsp;&times;</span>').click(function() {
            selected_semField = selected_semField.filter(i => i !== item);
            renderSelected();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
}

function enable_edit() {
    $('.editform').show();
    $('.button-to-appear-in-edit-mode').show().addClass('btn-danger');
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');
}

function disable_edit() {
    if (busy_editing) {
        // the user was busy editing but did not save the data, just reload the page
        location.reload(true);
    }
    $('.editform').hide();
    $('.button-to-appear-in-edit-mode').hide();
    busy_editing = false;
    $('#enable_edit').addClass('btn-primary').removeClass('btn-danger');
}

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

$('#enable_edit').click(function()
{
    toggle_edit(false);
});

$(document).ready(function() {

    disable_edit();

    handednesstypeahead($('.handednesstypeahead'));
    $('.handednesstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#handedness_value').text(suggestion.name);
          $('#handedness_machine_value').attr('value', suggestion.machine_value);
    });
    domhndshtypeahead($('.domhndshtypeahead'));
    $('.domhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#domhndsh_value').text(suggestion.name);
          $('#domhndsh_machine_value').attr('value', suggestion.machine_value);
    });
    semFieldtypeahead($('.semFieldtypeahead'));
    $('.semFieldtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_semField.includes(suggestion)) {
                busy_editing = true;
                selected_semField.push(suggestion);
                renderSelected();
          }
          $(this).typeahead('val', '');
    });

     $('.quick_save').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < gloss_phonology.length; i++) {
            var field = gloss_phonology[i];
            if (field == 'semField') {
                var field_values = [];
                var field_lookup = '#'+field+'_hidden_input_values';
                $(field_lookup).find('input[name="semField"]').each(function() {
                    var this_value = $(this).val();
                    field_values.push(this_value);
                });
                update['semField'] = field_values;
            } else {
                var field_lookup = '#'+field+'_machine_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            }
         }
         $.ajax({
            url : url + "/dictionary/update/edit_gloss_save/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            }
         });
     });
});
