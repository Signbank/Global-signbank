
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


 $(document).ready(function() {
    handednesstypeahead($('.handednesstypeahead'));
    $('.handednesstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          console.log('inside typeahead selection handedness: '+ ev + " " + JSON.stringify(suggestion));
          $('#handedness_value').text(suggestion.name);
          $('#handedness_machine_value').attr('value', suggestion.machine_value);
    });
    domhndshtypeahead($('.domhndshtypeahead'));
    $('.domhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          console.log('inside typeahead selection domhndsh: '+ ev + " " + JSON.stringify(suggestion));
          $('#domhndsh_value').text(suggestion.name);
          $('#domhndsh_machine_value').attr('value', suggestion.machine_value);
    });
    semFieldtypeahead($('.semFieldtypeahead'));
    $('.semFieldtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          console.log('inside typeahead selection semField: '+ ev + " " + JSON.stringify(suggestion));
          if (!selected_semField.includes(suggestion)) {
                selected_semField.push(suggestion);
                renderSelected();
          }
          $(this).typeahead('val', '');
    });
});
