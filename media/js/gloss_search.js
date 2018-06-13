/*
 *  Mimic the 'gloss' typeahead facility for 'morpheme', which is a subset of the glosses
 *  (as defined by the 'Morpheme' model, which takes Gloss as basis)
 */

$(document).ready(function() {
    morphtypeahead($('.morphtypeahead'));
    $('.morphtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk)
        });
    $('.morphtypeahead').on("input", function() {
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