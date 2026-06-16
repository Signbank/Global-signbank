
var busy_editing = false;

// bloodhounds for field choices

// Define all typeahead configurations in one place
const typeaheadConfigs = [
    { name: 'handedness', endpoint: 'fieldchoice/Handedness' },
    { name: 'domhndsh', endpoint: 'handshape' },
    { name: 'subhndsh', endpoint: 'handshape' },
    { name: 'handCh', endpoint: 'fieldchoice/HandshapeChange' },
    { name: 'relatArtic', endpoint: 'fieldchoice/RelatArtic' },
    { name: 'locprim', endpoint: 'fieldchoice/Location' },
    { name: 'contType', endpoint: 'fieldchoice/ContactType' },
    { name: 'movSh', endpoint: 'fieldchoice/MovementShape' },
    { name: 'movDir', endpoint: 'fieldchoice/MovementDir' },
    { name: 'relOriMov', endpoint: 'fieldchoice/RelOriMov' },
    { name: 'relOriLoc', endpoint: 'fieldchoice/RelOriLoc' },
    { name: 'oriCh', endpoint: 'fieldchoice/OriChange' },
    { name: 'namEnt', endpoint: 'fieldchoice/NamedEntity' },
    { name: 'valence', endpoint: 'fieldchoice/Valence' },
    { name: 'wordClass', endpoint: 'fieldchoice/WordClass' },
    { name: 'semField', endpoint: 'semField' },
    { name: 'derivHist', endpoint: 'derivHist' },
    { name: 'dialect', endpoint: 'dialect/'+gloss_dataset_id }
];

// Factory function to create bloodhounds
function createTypeahead(config) {
    const bloodhound = new Bloodhound({
        datumTokenizer: function(d) { return d.tokens; },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: `${url}/dictionary/ajax/${config.endpoint}/%QUERY`
    });

    bloodhound.initialize();

    return function(target) {
        $(target).typeahead({
            minLength: 0,
            hint: false
            }, {
            name: config.name,
            limit: 50,
            displayKey: 'name',
            source: bloodhound.ttAdapter(),
            autoSelect: false,
            templates: {
                suggestion: function(fc) {
                    return `<p><strong>${fc.name}</strong></p>`;
                }
            }
        });
    };
}

// Initialize all typeaheads
typeaheadConfigs.forEach(config => {
    window[config.name + 'typeahead'] = createTypeahead(config);
});

// last of the field choice bloodhounds

// multiselect fields

var initial_dialect = initial_dialects; // constant for resetting

var selected_dialect = selected_dialects;  // variable

var initial_semField = initial_semFields;

var selected_semField = selected_semFields;

var initial_derivHist = initial_derivHists;

var selected_derivHist = selected_derivHists;

function selectionIncludes(selected_fields, new_selection) {
    for (i=0; i<selected_fields.length;i++) {
        if (selected_fields[i].name === new_selection.name) { return true; }
    }
    return false;
}

// dynamically sets up the editable buttons in the left column during edit mode
function renderMultiSelected(field, selected_field) {
    var container = $('#multiselect_value_'+field);
    container.empty();
    var values_input = $('#'+field+'_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#'+field+'_multiselect');
    selected_field.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="'+field+'" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            busy_editing = true;
            selected_field = selected_field.filter(i => i !== item);
            renderMultiSelected(field, selected_field);
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_field.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
    placeholder_lookahead.css("color", "red");
}

// dynamically sets up the non-editable buttons in the left column for when not in edit mode
function initialise_multiselect(field) {
    var this_multiselect = $("#multiselect_value_"+field);
    var initial_selection = window["initial_"+field];
    this_multiselect.empty();
    var values_input = $('#'+field+'_hidden_input_values');
    values_input.empty();
    initial_selection.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        this_multiselect.append(tag);
    });
    var placeholder_lookahead = $('#'+field+'_multiselect');
    var new_placeholder = initial_selection.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
}

function initialise_multiselects() {
    busy_editing = false;
    $('[id^="multiselect_value_"]').each(function() {
        var field = $(this).attr('data-name');
        initialise_multiselect(field);
    });
}

// language fields typeaheads

var lemma_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+gloss_default_language_code+'/%QUERY'
    });

lemma_bloodhound.initialize();

function lemmatypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'lemmatarget',
          displayKey: 'lemma',
          limit: 10,
          source: lemma_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(lemma) {
                  return("<p><strong>" + lemma.lemma + "</strong></p>");
              }
          }
      });
}

var gloss_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/gloss/'+gloss_dataset_id+'/%QUERY'
    });

gloss_bloodhound.initialize();

function glosstypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'glosstarget',
          displayKey: 'annotation_idgloss',
          source: gloss_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  return("<p><strong>" + gloss.annotation_idgloss +  "</strong></p>");
              }
          }
      });
}

var morph_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/morph/%QUERY'
    });

morph_bloodhound.initialize();

function morphtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'morphtarget',
          displayKey: 'annotation_idgloss',
          source: morph_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  return("<p><strong>" + gloss.annotation_idgloss + "</strong></p>");
              }
          }
      });
}

$("#show_set_lemma_form").on('click', function() {
    $('#lemma_forms_row').show();
    $("#set_lemma_form").show();
    $('#lemma_buttons').hide();
    $('#add_lemma_form').hide();
});

$("#show_create_lemma_form").on('click', function() {
    $('#lemma_forms_row').show();
    $('#add_lemma_form').show();
    $('#lemma_buttons').hide();
    $("#set_lemma_form").hide();
});

$(".lemma-form-dismiss").on('click', function() {
    var this_form = $(this).parent().attr('id');
    if (this_form === 'set_lemma_form') {
        $('#lemma_forms_row').hide();
    } else {
        $('#add_lemma_form').hide();
    }
    $('#lemma_buttons').show();
});

const morphology_kinds = ['morphologydefinition', 'morphemedefinition', 'blenddefinition'];

function disable_edit_rows_panel(category) {
    if (category === 'morphology') {
        $.each(morphology_kinds, function (_, kind) {
            $('#add_'+kind+'_form').hide();
        });
    } else {
        $('#add_'+category+'_form').hide();
    }
    $('.'+category+'_delete_edit_only').hide();
    $('.empty_row_'+category).hide();
}

function enable_edit_rows_panel(category) {
    if (category === 'morphology') {
        $.each(morphology_kinds, function (_, kind) {
            $('#add_'+kind+'_form').show();
        });
    } else {
        $('#add_'+category+'_form').show();
    }
    $('.'+category+'_delete_edit_only').show();
    $('.empty_row_'+category).show();
}

function disable_edit_morphology() {
    disable_edit_rows_panel('morphology');
    $('.morphology-edit-dismiss').hide();
    $('#enable_edit_morphology').show();
}

$(".morphology-edit-dismiss").on('click', function() {
    disable_edit_rows_panel('morphology');
    $(this).hide();
    $('#enable_edit_morphology').show();
});

$("#enable_edit_morphology").on('click', function() {
    enable_edit_rows_panel('morphology');
    $('.morphology-edit-dismiss').show();
    $(this).hide();
});

function disable_edit_relations() {
    disable_edit_rows_panel('relations');
    $('.relations-edit-dismiss').hide();
    $('#enable_edit_relations').show();
}

$(".relations-edit-dismiss").on('click', function() {
    disable_edit_rows_panel('relations');
    $(this).hide();
    $('#enable_edit_relations').show();
});

$("#enable_edit_relations").on('click', function() {
    enable_edit_rows_panel('relations');
    $('.relations-edit-dismiss').show();
    $(this).hide();
});

function disable_edit_foreignrelations() {
    disable_edit_rows_panel('foreignrelations');
    $('.foreignrelations-edit-dismiss').hide();
    disable_editing('foreignrelations');
    $('#enable_edit_foreignrelations').show();
}

$(".foreignrelations-edit-dismiss").on('click', function() {
    disable_edit_rows_panel('foreignrelations');
    disable_editing('foreignrelations');
    $(this).hide();
    $('#enable_edit_foreignrelations').show();
});

$("#enable_edit_foreignrelations").on('click', function() {
    enable_edit_rows_panel('foreignrelations');
    $('.foreignrelations-edit-dismiss').show();
    $(this).hide();
    enable_editing('foreignrelations');
});

function disable_edit_nme() {
    $('.edit_only_nme').hide();
    $('.read_only_nme').show();
    $('#nme_edit_dismiss').hide();
    $('#enable_edit_nme').show();
}

$(".nme-edit-dismiss").on('click', function() {
    $('.edit_only_nme').hide();
    $('.read_only_nme').show();
    $(this).hide();
    $('#enable_edit_nme').show();
});

$("#enable_edit_nme").on('click', function() {
    $('.edit_only_nme').show();
    $('.read_only_nme').hide();
    $('#nme_edit_dismiss').show();
    $(this).hide();
});

function disable_edit_notes() {
    $('.edit_only_notes').hide();
    $('.read_only_notes').show();
    disable_editing('notes');
    $('#notes_edit_dismiss').hide();
    $('#enable_edit_notes').show();
}

$(".notes-edit-dismiss").on('click', function() {
    $('.edit_only_notes').hide();
    disable_editing('notes');
    $('.read_only_notes').show();
    $(this).hide();
    $('#enable_edit_notes').show();
});

$("#enable_edit_notes").on('click', function() {
    $('.edit_only_notes').show();
    $('.read_only_notes').hide();
    $('#notes_edit_dismiss').show();
    $(this).hide();
    enable_editing('notes');
});

function disable_edit_provenance() {
    $('.edit_only_provenance').hide();
    $('.read_only_provenance').show();
    disable_editing('provenance');
    $('#provenance_edit_dismiss').hide();
    $('#enable_edit_provenance').show();
}

$(".provenance-edit-dismiss").on('click', function() {
    $('.edit_only_provenance').hide();
    disable_editing('provenance');
    $('.read_only_provenance').show();
    $(this).hide();
    $('#enable_edit_provenance').show();
});

$("#enable_edit_provenance").on('click', function() {
    $('.edit_only_provenance').show();
    $('.read_only_provenance').hide();
    $('#provenance_edit_dismiss').show();
    $(this).hide();
    enable_editing('provenance');
});

function disable_edit_annotated_sentences() {
    $('.edit_only_annotated_sentences').hide();
    $("#annotated_sentences_edit_dismiss").hide();
}

$("#annotated_sentences_edit_dismiss").on('click', function() {
    $('.edit_only_annotated_sentences').hide();
    $('#enable_edit_annotated_sentences').show();
    $(this).hide();
});

$("#enable_edit_annotated_sentences").on('click', function() {
    $('.edit_only_annotated_sentences').show();
    $(".annotated_sentences_edit_dismiss").show();
    $(this).hide();
});

function disable_edit_othermedia() {
    $('.edit_only_othermedia').hide();
    $('.read_only_othermedia').show();
    disable_editing('othermedia');
    $('#othermedia_edit_dismiss').hide();
    $('#enable_edit_othermedia').show();
}

$(".othermedia-edit-dismiss").on('click', function() {
    $('.edit_only_othermedia').hide();
    disable_editing('othermedia');
    $('.read_only_othermedia').show();
    $(this).hide();
    $('#enable_edit_othermedia').show();
});

$("#enable_edit_othermedia").on('click', function() {
    $('.edit_only_othermedia').show();
    $('.read_only_othermedia').hide();
    $('#othermedia_edit_dismiss').show();
    $(this).hide();
    enable_editing('othermedia');
});

function ajaxifyTagForm() {
    // ajax form submission for tag addition and deletion
    $('.tagdelete').click(function() {
        var action = $(this).attr('href');
        var tagid = $(this).attr('id');
        var tagelement = $(this).parents('.tagli');

        $.post(action,
              {tag: tagid, 'delete': "True" },
               function(data) {
                    if (data === 'deleted') {
                        // remove the tag from the page
                       tagelement.remove();
                    }
               });
        return false;
    });
    $('#tagaddform').submit(function(){

        var newtag = $('#tagaddform select').val();

        if (newtag !== "") {
            $.post($(this).attr('action'), $(this).serialize(),
                    function(data) {
                       // response is a new tag list
                       $('#tags').replaceWith(data);
                       ajaxifyTagForm();
                   });
        } else {
            alert("Please select a tag value.");
        }
        return false;
    });
}

// the enable and disable rely on nesting and combinations of classes and ids, making use the panel category
function disable_editing(category) {
     // this makes use of specific element identifiers for the lookahead fields, etc
     $('.form-control').each(function() {
         var this_id = $(this).attr('id');
         if (!this_id) {return;}
         var data_category = $(this).attr('data-category');
         if (!data_category) {return;}
         if (data_category !== category) {return;}
         if (this_id.endsWith("_lookahead")) {
             $(this).attr('disabled', true);
             return;
         }
         if (this_id.endsWith("_value")) {
             $(this).attr('disabled', true);
         }
         if (this_id.endsWith("_text")) {
             $(this).attr('disabled', true);
         }
         if (this_id.endsWith("_textarea")) {
             $(this).attr('disabled', true);
         }
         if (this_id.startsWith("definition")) {
             $(this).attr('disabled', true);
         }
         if (this_id.startsWith("provenance")) {
             $(this).attr('disabled', true);
         }
         if (this_id.startsWith("othermedia")) {
             $(this).attr('disabled', true);
         }
         if (this_id.endsWith("_multiselect")) {
             $(this).attr('disabled', true);
         }
         if (this_id.startsWith("nmevideo")) {
            $(this).attr('disabled', true);
         }
     });
}

function enable_editing(category) {
     // this makes use of specific element identifiers for the lookahead fields, etc
     $('.form-control').each(function() {
         var this_id = $(this).attr('id');
         if (!this_id) {return;}
         var data_category = $(this).attr('data-category');
         if (!data_category) {return;}
         if (data_category !== category) {return;}
         if (this_id.endsWith("_lookahead")) {
             $(this).removeAttr('disabled');
             return;
         }
         if (this_id.endsWith("_value")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.endsWith("_text")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.endsWith("_textarea")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.startsWith("definition")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.startsWith("provenance")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.startsWith("othermedia")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.endsWith("_multiselect")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.startsWith("nmevideo")) {
            $(this).removeAttr('disabled');
         }
     });
}

function show_edit_panel(category) {
    if (category === 'semantics') {
        $('.read_only_semantics').hide();
        $('.edit_only_semantics').show();
        $('.editsemanticsform').show();
        $('#multiselect_value_semField').trigger('editSemField');
        $('#multiselect_value_derivHist').trigger('editDerivHistField');
    }
    if (category === 'general') {
        $('.read_only').hide();
        $('.edit_only').show();
        $('.edit_only_general').show();
        $('.editdialectform').show();
        $('.editform').show();  // appears in gloss tags and affiliations
        $('#multiselect_value_dialect').trigger('editDialectField');
        $('#lemma_buttons_group').show();
    }
    if (category === 'publication') {
        $('.read_only_publication').hide();
        $('.edit_only_publication').show();
    }
    $('.empty_row_'+category).show();
    $('#enable_edit_'+category).addClass('edit_enabled').hide();
    $('.button-'+category+'-to-appear-in-edit-mode').show();
    enable_editing(category);
}

function hide_edit_panel(category) {
    if (category === 'semantics') {
        $('.editsemanticsform').hide();
        $('.read_only_semantics').show();
        $('.edit_only_semantics').hide();
    }
    if (category === 'general') {
        $('.editdialectform').hide();
        $('#lemma_buttons_group').hide();
        $('#lemma_forms_row').hide();
        $('.editform').hide();  // appears in gloss tags and affiliations
        $('.read_only').show();
        $('.edit_only').hide();
        $('.edit_only_general').hide();
    }
    if (category === 'publication') {
        $('.read_only_publication').show();
        $('.edit_only_publication').hide();
    }
    $('.empty_row_'+category).hide();
    $('.button-'+category+'-to-appear-in-edit-mode').hide();
    $('#enable_edit_'+category).removeClass('edit_enabled').show();
    disable_editing(category);
    busy_editing = false;
}

function toggle_edit_panel(category) {
    if ($('#enable_edit_'+category).hasClass('edit_enabled'))
    {
        hide_edit_panel(category);
    } else {
        show_edit_panel(category);
    }
}

const lookaheadConfig = [
    { name: 'handedness', element: '#handedness_lookahead', lookup: '.handednesstypeahead' },
    { name: 'domhndsh', element: '#domhndsh_lookahead', lookup: '.domhndshtypeahead' },
    { name: 'subhndsh', element: '#subhndsh_lookahead', lookup: '.subhndshtypeahead' },
    { name: 'handCh', element: '#handCh_lookahead', lookup: '.handChtypeahead' },
    { name: 'relatArtic', element: '#relatArtic_lookahead', lookup: '.relatArtictypeahead' },
    { name: 'locprim', element: '#locprim_lookahead', lookup: '.locprimtypeahead' },
    { name: 'contType', element: '#contType_lookahead', lookup: '.contTypetypeahead' },
    { name: 'movSh', element: '#movSh_lookahead', lookup: '.movShtypeahead' },
    { name: 'movDir', element: '#movDir_lookahead', lookup: '.movDirtypeahead' },
    { name: 'relOriMov', element: '#relOriMov_lookahead', lookup: '.relOriMovtypeahead' },
    { name: 'relOriLoc', element: '#relOriLoc_lookahead', lookup: '.relOriLoctypeahead' },
    { name: 'oriCh', element: '#oriCh_lookahead', lookup: '.oriChtypeahead' },
    { name: 'namEnt', element: '#namEnt_lookahead', lookup: '.namEnttypeahead' },
    { name: 'valence', element: '#valence_lookahead', lookup: '.valencetypeahead' },
    { name: 'wordClass', element: '#wordClass_lookahead', lookup: '.wordClasstypeahead' }
];

function readyLookahead(config) {
    let typeahead = window[config.name+'typeahead'];
    typeahead($(config.lookup));

    $(config.lookup).bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr("val", suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          $('#'+config.name+'_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $(config.element).on("focus", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name || preselect_name === '-') {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
}

const multiselectConfig = [
    { name: 'dialect', element: '#dialect_multiselect', lookup: '.dialecttypeahead', target: '#multiselect_value_dialect',
      selected_fields: 'selected_dialect', signal: 'editDialectField' },
    { name: 'semField', element: '#semField_multiselect', lookup: '.semFieldtypeahead', target: '#multiselect_value_semField',
      selected_fields: 'selected_semField', signal: 'editSemField' },
    { name: 'derivHist', element: '#derivHist_multiselect', lookup: '.derivHisttypeahead', target: '#multiselect_value_derivHist',
      selected_fields: 'selected_derivHist', signal: 'editDerivHistField' }
]

function readyMultiselect(config) {
    let selected_fields = window[config.selected_fields];
    let typeahead = window[config.name+'typeahead'];
    typeahead($(config.lookup));

    $(config.lookup).bind('typeahead:selected', function(ev, suggestion) {
          if (!selectionIncludes(selected_fields, suggestion)) {
                busy_editing = true;
                selected_fields.push(suggestion);
                renderMultiSelected(config.name, selected_fields);
          }
          $(this).typeahead('val', '');
    });
    $(config.element).on("focus", function() {
      $(this).attr('value', '');
    });
}

$('[class^="multiselect_"]').each(function() {
    $(this).on('change', function() {
        busy_editing = true;
    });
});

$('[class^="select_"]').each(function() {
    $(this).on('change', function() {
        busy_editing = true;
    });
});

$('[class^="text_"]').each(function() {
    $(this).on('change', function() {
        busy_editing = true;
    });
    $(this).on('reset', function() {
        var initial_value = $(this).attr('data-initial');
        $(this).val(initial_value);
    });
});

$(document).ready(function() {

    if (use_lookaheads === 'lookaheads') {
        lookaheadConfig.forEach(config => {
            window[config.name + 'typeahead'] = readyLookahead(config);
        });
    }

    multiselectConfig.forEach(config => {
        window[config.name + 'typeahead'] = readyMultiselect(config);
    });

    multiselectConfig.forEach(config => {
        let selected_fields = window[config.selected_fields];
        $(config.target).on(config.signal, function() {
            renderMultiSelected(config.name, selected_fields);
        });
    });

    lemmatypeahead($('.lemmatypeahead'));
    $('.lemmatypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          busy_editing = true;
          $('#new_lemma_pk').attr('value', suggestion.pk);
    });
    $('.lemmatypeahead').on("click", function() {
          $(this).parent().next().val("");
    });
    glosstypeahead($('.glosstypeahead'));
    $('.glosstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          var target_gloss_lookahead = $(this).attr("id");
          busy_editing = true;
          var width_of_new_value = suggestion.annotation_idgloss.length * 8 + 20;
          $(this).css("width", width_of_new_value + "px");
          $('#'+target_gloss_lookahead+'_id').attr('value', suggestion.pk);
    });
    $('.glosstypeahead').on("input", function() {
          $(this).parent().next().val("");
    });
    morphtypeahead($('.morphtypeahead'));
    $('.morphtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          var target_morph_lookahead = $(this).attr("id");
          busy_editing = true;
          var width_of_new_value = suggestion.annotation_idgloss.length * 8 + 20;
          $(this).css("width", width_of_new_value + "px");
          $('#'+target_morph_lookahead+'_id').attr('value', suggestion.pk);
    });
    $('.morphtypeahead').on("input", function() {
          $(this).parent().next().val("")
    });

    $('.edit-cancel').on('click', function() {
        var panel_category = $(this).attr('data-category');
        if (!panel_category) { return; };
        if (!busy_editing) {
            if (panel_category === 'semantics') {
                initialise_multiselect('semField');
                initialise_multiselect('derivHist');
            }
            if (panel_category === 'general') {
                initialise_multiselect('dialect');
            }
            if (['general', 'phonology', 'semantics', 'publication'].includes(panel_category)) {
                hide_edit_panel(panel_category);
            }
            return;
        };
        $('[class^="select_"]').each(function() {
            var this_category = $(this).attr('data-category');
            if (this_category != panel_category) { return; }
            var initial_data = $(this).attr('data-initial');
            $(this).attr('value', initial_data);
            $(this).val(initial_data).trigger('change');
            busy_editing = false;
        });
        $('[class*="text_"]').each(function() {
            var this_category = $(this).attr('data-category');
            if (this_category != panel_category) { return; }
            var this_id = $(this).attr('id');
            var initial_value = $(this).attr('data-initial');
            var this_value = $(this).val();
            if (this_value != initial_value) {
                $(this).trigger('reset');
            }
        });
        $('[class*="multiselect_"]').each(function() {
            var this_category = $(this).attr('data-category');
            if (this_category != panel_category) { return; }
            var this_name = $(this).attr("name");
            if (!this_name) { return; }
            if (this_name === 'dialect') {
                selected_dialect.length = 0;
                selected_dialect = JSON.parse(JSON.stringify(initial_dialect));
                initialise_multiselect('dialect');
            } else if (this_name === 'semField') {
                selected_semField.length = 0;
                selected_semField = JSON.parse(JSON.stringify(initial_semField));
                initialise_multiselect('semField');
            } else if (this_name === 'derivHist') {
                selected_derivHist.length = 0;
                selected_derivHist = JSON.parse(JSON.stringify(initial_derivHist));
                initialise_multiselect('derivHist');
            }
        });
        if (use_lookaheads === 'lookaheads') {
            $('[id*="_lookahead"]').each(function() {
                var this_field = $(this).attr('data-field');
                var this_category = $(this).attr('data-category');
                if (this_category != panel_category) { return; }
                var initial_data = $(this).attr('data-initial');
                var machine_value = $(this).attr('data-machine_value');
                if (!machine_value) {
                    machine_value = '0';
                }
                $(this).attr('placeholder', initial_data);
                $(this).attr('data-preselect', machine_value);
                $('#'+this_field+'_machine_value').attr('value', machine_value);
                $('#'+this_field+'_hidden_input_values').empty();
                $(this).val(initial_data).trigger('input').typeahead('close');
                busy_editing = false;
            });
        }
        busy_editing = false;
        if (['general', 'phonology', 'semantics', 'publication'].includes(panel_category)) {
            hide_edit_panel(panel_category);
        }
    });

     $('.quick_save').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < gloss_fields.length; i++) {
            var field = gloss_fields[i];
            if (['semField', 'derivHist', 'dialect'].includes(field)) {
                var field_key = field;
                var field_values = [];
                var field_lookup = '#'+field+'_hidden_input_values';
                $(field_lookup).find('input[name="'+field+'"]').each(function() {
                    var this_value = $(this).val();
                    field_values.push(this_value);
                });
                if (!field_values.length) {
                    update[field_key] = 'None'
                } else {
                    update[field_key] = field_values;
                }
            } else if (['weakdrop', 'weakprop'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['domhndsh_letter_or_number', 'subhndsh_letter_or_number'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['repeat', 'altern', 'inWeb', 'isNew', 'excludeFromEcv'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['release_information', 'useInstr', 'locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg', 'concConcSet'].includes(field)) {
                var field_lookup = '#'+field+'_text';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else {
                if (use_lookaheads === 'lookaheads') {
                    var field_lookup = '#'+field+'_machine_value';
                } else {
                    var field_lookup = '#'+field+'_value';
                }
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            }
         }
         $.ajax({
            url : url + "/dictionary/update/edit_gloss_save/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_set_lemma').click(function(e)
	 {
         e.preventDefault();
	     var set_lemma_url = $('#set_lemma_form').attr("action");
	     var new_lemma_pk = $('#new_lemma_pk').attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
	     update['new_lemma_pk'] = new_lemma_pk;
         $.ajax({
            url : set_lemma_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_set_annotation').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var button_id = $(this).attr('id');
         var glossid = $(this).attr('value');
         var language_field = '#'+button_id.slice('button_'.length);
	     var value = $(language_field).val();
         var language_code_2char = $(this).attr('data-language');
         update['language_code_2char'] = language_code_2char;
	     update['value'] = value;
         $.ajax({
            url : url + "/dictionary/update/update_gloss_annotation/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_update_nmevideo').click(function(e)
	 {
         e.preventDefault();
         var nmevideoid = $(this).attr('data-value');
	     var update_nmevideo_url = $('#nmevideo_update_'+nmevideoid).attr("action");
         var update = { 'csrfmiddlewaretoken': csrf_token };
	     for (var i=0; i < language_2chars.length; i++) {
             var lang2char = language_2chars[i];
             var description_field = 'nmevideo_description_'+nmevideoid+'_'+lang2char;
             var description_value = $('#'+description_field).val();
             update[description_field] = description_value;
         }
         var offset_field = 'nmevideo_offset_'+nmevideoid;
         var offset_value = $('#'+offset_field).val();
         update[offset_field] = offset_value;
         $.ajax({
            url : update_nmevideo_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_save_foreignrelation').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var glossid = $(this).attr('data-glossid');
         var foreignrelationid = $(this).attr('data-foreignrelationid');
         update['foreignrelation-loan_'+foreignrelationid] = $('#foreignrelation_loan_'+foreignrelationid+'_select_value').val();
         update['foreignrelation-other-lang_'+foreignrelationid] = $('#foreignrelation_other_lang_'+foreignrelationid+'_text').val();
         update['foreignrelation-other-lang-gloss_'+foreignrelationid] = $('#foreignrelation_other_lang_gloss_'+foreignrelationid+'_text').val();
         $.ajax({
            url : url + "/dictionary/update/update_gloss_foreignrelation/" + glossid + "/" + foreignrelationid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_save_note').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var glossid = $(this).attr('data-glossid');
         var definitionid = $(this).attr('data-definitionid');
         update['note-definitionpub_'+definitionid] = $('#definitionpub_'+definitionid+'_select_value').val();
         update['note-definitioncount_'+definitionid] = $('#definitioncount_'+definitionid).val();
         update['note-definitionrole_'+definitionid] = $('#definitionrole_'+definitionid).val();
         update['note-definition_'+definitionid] = $('#definition_'+definitionid).val();
         $.ajax({
            url : url + "/dictionary/update/update_gloss_note/" + glossid + "/" + definitionid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_save_provenance').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var glossid = $(this).attr('data-glossid');
         var provenanceid = $(this).attr('data-provenanceid');
         update['provenancemethod_'+provenanceid] = $('#provenancemethod_'+provenanceid).val();
         update['provenancedescription_'+provenanceid] = $('#provenancedescription_'+provenanceid).val();
         $.ajax({
            url : url + "/dictionary/update/update_gloss_provenance/" + glossid + "/" + provenanceid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_save_othermedia').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var glossid = $(this).attr('data-glossid');
         var othermediaid = $(this).attr('data-othermediaid');
         // the other media id is split from the field name identifier in the Python method
         update['other-media-type_'+othermediaid] = $('#othermedia-type_'+othermediaid).val();
         update['other-media-alternative-gloss_'+othermediaid] = $('#othermedia-alternative-gloss_'+othermediaid+'_text').val();
         update['other-media-description_'+othermediaid] = $('#othermedia-description_'+othermediaid).val();
         $.ajax({
            url : url + "/dictionary/update/update_gloss_othermedia/" + glossid + "/" + othermediaid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     var lookahead_elements = $('[id*="_lookahead"]');
     lookahead_elements.each(function() {
         var this_id = $(this).attr("id");
         var cell_lookup = '#' + this_id.slice(0, -'_lookahead'.length) + '_cell';
         var placeholder_text = $(this).attr("placeholder")
         if (!placeholder_text) {return;}
         var width_of_new_value = placeholder_text.length * 10 + 30;
         $(cell_lookup).attr('data-width', width_of_new_value);
    });
    var cell_elements = $('[id*="_cell"]');
    cell_elements.each(function() {
        var this_width = $(this).attr("data-width");
        if (!this_width) {return;};
        $(this).css('width', this_width+"px");
        var tt_children = $(this).find('.tt-input');
        $(tt_children).each(function() {
            $(this).css('width', this_width);
        });
    });
    busy_editing = false;
    $('#enable_edit_general').on("click", function() {
        toggle_edit_panel('general');
    });
    $('#enable_edit_phonology').on("click", function() {
        toggle_edit_panel('phonology');
    });
    $('#enable_edit_semantics').on("click", function() {
        toggle_edit_panel('semantics');
    });
    $('#enable_edit_publication').on("click", function() {
        toggle_edit_panel('publication');
    });
    $('#data_type_lists').on('click', function() {
        $('#data_type_lookaheads').removeClass('active');
        $(this).addClass('active');
        var this_datatype = $(this).attr('data-type');
        $('#use_lookaheads').attr('value', this_datatype);
    });
    $('#data_type_lookaheads').on('click', function() {
        $('#data_type_lists').removeClass('active');
        $(this).addClass('active');
        var this_datatype = $(this).attr('data-type');
        $('#use_lookaheads').attr('value', this_datatype);
    });
    hide_edit_panel('general');
    hide_edit_panel('phonology');
    hide_edit_panel('semantics');
    hide_edit_panel('publication');
    disable_edit_relations();
    disable_edit_foreignrelations();
    disable_edit_morphology();
    disable_edit_nme();
    disable_edit_notes();
    disable_edit_provenance();
    disable_edit_annotated_sentences();
    disable_edit_othermedia();
    ajaxifyTagForm();
    // setup required for Ajax POST
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false,
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
    $('#use_lookaheads').attr('value', use_lookaheads);
    $('#data_type_'+use_lookaheads).addClass('active');
    initialise_multiselects();
    busy_editing = false;
});
