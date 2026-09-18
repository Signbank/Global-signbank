
// relies on javascript variables: busy_editing, gloss_dataset_id, gloss_default_language_code

// language fields typeaheads
const languageConfigs = [
    { name: 'lemma', endpoint: 'lemma/'+gloss_dataset_id+'/'+gloss_default_language_code, displayKey: 'lemma' },
    { name: 'gloss', endpoint: 'gloss/'+gloss_dataset_id, displayKey: 'annotation_idgloss' },
    { name: 'morphemeblend', endpoint: 'gloss/'+gloss_dataset_id, displayKey: 'annotation_idgloss' },
    { name: 'relatedgloss', endpoint: 'gloss/'+gloss_dataset_id, displayKey: 'annotation_idgloss' },
    { name: 'morph', endpoint: 'morph', displayKey: 'annotation_idgloss' }
];

// Factory function to create bloodhounds
function createLanguageTypeahead(config) {
    const bloodhound = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: `${url}/dictionary/ajax/${config.endpoint}/%QUERY`,
            wildcard: '%QUERY',
            ajax: {
                type: 'GET',
                beforeSend: function(xhr, settings) {
                    if (!csrfSafeMethod(settings.type)) {
                        xhr.setRequestHeader("X-CSRFToken", csrf_token);
                    }
                }
            }
        }
    });

    bloodhound.initialize();

    return function(target) {
        $(target).typeahead({
            minLength: 0,
            hint: false
            }, {
            name: config.name,
            limit: 50,
            displayKey: config.displayKey,
            source: bloodhound.ttAdapter(),
            autoSelect: false,
            templates: {
                suggestion: function(fc) {
                    return `<p><strong>${fc[config.displayKey]}</strong></p>`;
                }
            }
        });
    };
}

// Initialize all typeaheads
languageConfigs.forEach(config => {
    window[config.name + 'typeahead'] = createLanguageTypeahead(config);
});

const lookaheadLanguageConfig = [
    { name: 'lemma', lookup: '.lemmatypeahead', target: '#new_lemma_pk', element: '#new_lemma', displayKey: 'lemma' },
    { name: 'gloss', lookup: '.glosstypeahead', target: '#morpheme_target_id', element: '#morpheme_target', displayKey: 'annotation_idgloss' },
    { name: 'morphemeblend', lookup: '.morphemeblendtypeahead', target: '#morpheme_blend_id', element: '#morpheme_blend', displayKey: 'annotation_idgloss' },
    { name: 'relatedgloss', lookup: '.relatedglosstypeahead', target: '#relation_target_id', element: '#relation_target', displayKey: 'annotation_idgloss' },
    { name: 'morph', lookup: '.morphtypeahead', target: '#morpheme_gloss_id', element: '#morpheme_gloss', displayKey: 'annotation_idgloss' }
    ]

function readyLanguageLookahead(config) {
    let typeahead = window[config.name+'typeahead'];
    typeahead($(config.lookup));
    $(config.lookup).bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          busy_editing = true;
          var width_of_new_value = suggestion[config.displayKey].length * 8 + 20;
          $(this).css("width", width_of_new_value + "px");
          $(config.target).attr('value', suggestion.pk);
    });
    $(config.element).on("input", function() {
          $(this).parent().next().val("");
    });
}
