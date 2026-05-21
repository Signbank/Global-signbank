
var busy_editing = false;

// bloodhounds for field choices

var handedness_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Handedness'+'/%QUERY'
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

var subhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

subhndsh_bloodhound.initialize();

function subhndshtypeahead(target) {

     $(target).typeahead(null, {
          name: 'subhndsh',
          displayKey: 'name',
          source: subhndsh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

var handCh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/HandshapeChange'+'/%QUERY'
    });

handCh_bloodhound.initialize();

function handChtypeahead(target) {

     $(target).typeahead(null, {
          name: 'handCh',
          displayKey: 'name',
          source: handCh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

var relatArtic_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelatArtic'+'/%QUERY'
    });

relatArtic_bloodhound.initialize();

function relatArtictypeahead(target) {

     $(target).typeahead(null, {
          name: 'relatArtic',
          displayKey: 'name',
          source: relatArtic_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

var locprim_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Location'+'/%QUERY'
    });

locprim_bloodhound.initialize();

function locprimtypeahead(target) {

     $(target).typeahead(null, {
          name: 'locprim',
          displayKey: 'name',
          source: locprim_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

var contType_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/ContactType'+'/%QUERY'
    });

contType_bloodhound.initialize();

function contTypetypeahead(target) {

     $(target).typeahead(null, {
          name: 'contType',
          displayKey: 'name',
          source: contType_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};
var movSh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementShape'+'/%QUERY'
    });

movSh_bloodhound.initialize();

function movShtypeahead(target) {

     $(target).typeahead(null, {
          name: 'movSh',
          displayKey: 'name',
          source: movSh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};
var movDir_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementDir'+'/%QUERY'
    });

movDir_bloodhound.initialize();

function movDirtypeahead(target) {

     $(target).typeahead(null, {
          name: 'movDir',
          displayKey: 'name',
          source: movDir_bloodhound.ttAdapter(),
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
    $('.empty_row').show();
    $('.button-to-appear-in-edit-mode').show();
    $('#enable_edit').removeClass('btn-primary').addClass('btn-danger');
}

function disable_edit() {
    if (busy_editing) {
        // the user was busy editing but did not save the data, just reload the page
        location.reload(true);
    }
    $('.editform').hide();
    $('.empty_row').hide();
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
    subhndshtypeahead($('.subhndshtypeahead'));
    $('.subhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#subhndsh_value').text(suggestion.name);
          $('#subhndsh_machine_value').attr('value', suggestion.machine_value);
    });
    handChtypeahead($('.handChtypeahead'));
    $('.handChtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#handCh_value').text(suggestion.name);
          $('#handCh_machine_value').attr('value', suggestion.machine_value);
    });
    relatArtictypeahead($('.relatArtictypeahead'));
    $('.relatArtictypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#relatArtic_value').text(suggestion.name);
          $('#relatArtic_machine_value').attr('value', suggestion.machine_value);
    });
    locprimtypeahead($('.locprimtypeahead'));
    $('.locprimtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#locprim_value').text(suggestion.name);
          $('#locprim_machine_value').attr('value', suggestion.machine_value);
    });
    contTypetypeahead($('.contTypetypeahead'));
    $('.contTypetypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#contType_value').text(suggestion.name);
          $('#contType_machine_value').attr('value', suggestion.machine_value);
    });
    movShtypeahead($('.movShtypeahead'));
    $('.movShtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#movSh_value').text(suggestion.name);
          $('#movSh_machine_value').attr('value', suggestion.machine_value);
    });
    movDirtypeahead($('.movDirtypeahead'));
    $('.movDirtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $('#movDir_value').text(suggestion.name);
          $('#movDir_machine_value').attr('value', suggestion.machine_value);
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

    $('.select_weakdrop').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakdrop_value').text(selected_text);
    });

    $('.select_weakprop').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakprop_value').text(selected_text);
    });

    $('.select_domhndsh_letter').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#domhndsh_letter_value').text(selected_text);
    });

    $('.select_domhndsh_number').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#domhndsh_number_value').text(selected_text);
    });
    $('.select_subhndsh_letter').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#subhndsh_letter_value').text(selected_text);
    });

    $('.select_subhndsh_number').on('change', function() {
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#subhndsh_number_value').text(selected_text);
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
            } else if (field == 'weakdrop') {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (field == 'weakprop') {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (field == 'domhndsh_letter') {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (field == 'domhndsh_number') {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
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
