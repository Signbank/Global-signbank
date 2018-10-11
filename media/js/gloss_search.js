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
                  return("<p><strong>" + gloss.annotation_idgloss + "</strong></p>");
              }
          }
      });
};


function set_signlanguages_dialects() {
    this_selection_elt = $('#signlanguage_selection');
    var signlanguage_str = '';
    this_selection_elt.find(".select2-selection__choice").each(function(){
        if (signlanguage_str) {
            signlanguage_str+=','+$(this).attr('title');
        }
        else {
            signlanguage_str = $(this).attr('title');
        }
    });

    optionValues = [];

    if (signlanguage_str) {
        var signlanguages = signlanguage_str.split(",");
        this_selection_choices = $('#signlanguage_selection');

        for(i = 0; i < signlanguages.length; i++) {
            $('#id_signLanguage option').each(function(){
                if ($(this).html() == signlanguages[i]) {
                    optionValues.push($(this).html());
                };
            });
        };
    }

    $('#id_dialects').val(null).trigger('change');

    this_selection_dialect_elt = $('#dialect_selection');
    $('#id_dialects option').each(function(){
        $(this).attr('disabled','disabled');
    });
    $('#id_dialects option').each(function(){
        var this_node_str = $(this).html();
        for(k = 0; k < optionValues.length; k++) {
            if (this_node_str.startsWith(optionValues[k])) {
                $(this).removeAttr('disabled');
            }
        };
    });
    $('#id_dialects').select2({
        allowClear: true,
        dropdownAutoWidth: true,
        width: 'resolve'
     });
    $('#id_dialects').val(null).trigger('change');
};