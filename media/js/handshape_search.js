/*
 *  Mimic the 'gloss' typeahead facility for 'morpheme', which is a subset of the glosses
 *  (as defined by the 'Morpheme' model, which takes Gloss as basis)
 */

 $(document).ready(function() {

//    handshapetypeahead($('.handshapetypeahead'));

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

var handshape_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape/%QUERY'
    });

handshape_bloodhound.initialize();

function handshapetypeahead(target) {

     $(target).typeahead(null, {
          name: 'handshapetarget',
          displayKey: current_language_code+'_name',
          source: handshape_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(hs) {
                  return("<p><strong>" + hs[current_language_code + '_name'] + "</strong></p>");
              }
          }
      });
};

handshapetypeahead($('.handshapetypeahead'));


$.editable.addInputType('handshapetypeahead', {

   element: function(settings, original) {
      var input = $('<input type="text" class="handshapetypeahead">');
      $(this).append(input);

      handshapetypeahead(input);

      return (input);
   },
});
