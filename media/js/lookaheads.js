
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


// last of the field choice bloodhounds

 $(document).ready(function() {
    handednesstypeahead($('.handednesstypeahead'));
    $('.handednesstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          console.log('inside typeahead selection: '+ ev + " " + JSON.stringify(suggestion));
          $('#handedness_value').text(suggestion.name);
          $('#handedness_machine_value').attr('value', suggestion.machine_value);
    });
//    $('.handednesstypeahead').on("input", function() {
//          console.log('bound to input');
//          $('#handedness_value').val("");
//        });
});
