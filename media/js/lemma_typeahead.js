gloss_dataset_id = null;

var lemma_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/%QUERY'
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
    lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/%QUERY'
    if($("#id_dataset").val() == "") {  // No dataset selected
        $('.lemmatypeahead').prop("disabled", true);
    }
    $("#id_dataset").change(function() {
        if(this.value) {
            $('.lemmatypeahead').prop("disabled", false);
            gloss_dataset_id = this.value;
            lemma_bloodhound.remote.url = url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/%QUERY'
        } else {
            $('.lemmatypeahead').prop("disabled", true);
            gloss_dataset_id = null;
        }
    });
});

