
const typeaheadConfigs = [
    { name: 'handshape', endpoint: 'handshape' }
]

function createTypeahead(config) {
    const bloodhound = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace(['name']),
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

    bloodhound.clearPrefetchCache();
    bloodhound.initialize();

    return function(target) {
        $(target).typeahead({
            minLength: 0,
            hint: false
            }, {
            name: config.name,
            limit: 100,
            displayKey: 'name',
            source: bloodhound.ttAdapter(),
            autoSelect: false,
            templates: {
                suggestion: function(fc) {
                    return `<p class="tt-choice" style="background-color:${fc.color}"><strong>${fc.name}</strong></p>`;;
                }
            }
        });
    };
}

typeaheadConfigs.forEach(config => {
    console.log('config: '+config.name);
    window[config.name + 'typeahead'] = createTypeahead(config);
});

const lookaheadConfig = [
    { name: 'handshape', element: '#handshape_lookahead', lookup: '.handshapetypeahead' },
]

function readyLookahead(config) {
    let typeahead = window[config.name+'typeahead'];
    typeahead($(config.lookup));

    $(config.lookup).bind('typeahead:selected', function(ev, suggestion) {
          $(this).attr('value', suggestion.name);
          $(this).attr("val", suggestion.name);
          $(this).attr('placeholder', suggestion.name);
    });
    $(config.element).on("focus", function() {
        $(this).val('').trigger('input').typeahead('open');
    });
}
