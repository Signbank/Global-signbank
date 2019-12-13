gloss_dataset_id = null;
gloss_dataset_languages = null;
languages = [];
gloss_dataset_language_code_2char = null;

var lemma_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+language_code+'/%QUERY'
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

lemmatypeahead($('.lemmatypeahead'));
$('.lemmatypeahead').bind('typeahead:selected', function(ev, suggestion) {
      $(this).parent().next().val(suggestion.pk)
    });
$('.lemmatypeahead').on("input", function() {
      $(this).parent().next().val("")
    });

$(document).ready(function() {
    gloss_dataset_id = $('#id_dataset').find(":selected").attr('value');

    if (gloss_dataset_id == null)
    {
        $('.lemmatypeahead').prop("disabled", true);
        return;
    }
    gloss_dataset_languages = $('#id_dataset').find(":selected").attr('dataset_languages');
    languages = gloss_dataset_languages.split(",");

    lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+language_code+'/%QUERY'
    if($("#id_dataset").val() == "") {  // No dataset selected
        $('.lemmatypeahead').prop("disabled", true);
    }
    $("#id_dataset").change(function() {
        if(this.value) {
            $('.lemmatypeahead').prop("disabled", false);
            gloss_dataset_id = this.value;
            gloss_dataset_languages = $(this).find(":selected").attr('dataset_languages');
            languages = gloss_dataset_languages.split(",");
            if (languages.length > 1) {
                lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+languages[0]+'/%QUERY'
            } else {
                lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+languages+'/%QUERY'
            }
        } else {
            $('.lemmatypeahead').prop("disabled", true);
            gloss_dataset_id = null;
        }
    });
});

function set_lemma_language() {
    var selected_language = $("input[type=radio]").filter(':checked').attr('value');
//    console.log('set lemma language, lemma typeahead: '+selected_language);
    lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+selected_language+'/%QUERY'
}
