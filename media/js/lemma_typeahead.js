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


function set_lemma_language() {
    var selected_language = $("input[type=radio]").filter(':checked').attr('value');
}

