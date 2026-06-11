
var busy_editing = false;

// bloodhounds for field choices

var handedness_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Handedness'+'/%QUERY'
    });

handedness_bloodhound.initialize();

function handednesstypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'handedness',
          displayKey: 'name',
          source: handedness_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var domhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

domhndsh_bloodhound.initialize();

function domhndshtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'domhndsh',
          displayKey: 'name',
          limit: 20,
          source: domhndsh_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var subhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

subhndsh_bloodhound.initialize();

function subhndshtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'subhndsh',
          displayKey: 'name',
          limit: 20,
          source: subhndsh_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var handCh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/HandshapeChange'+'/%QUERY'
    });

handCh_bloodhound.initialize();

function handChtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'handCh',
          displayKey: 'name',
          source: handCh_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relatArtic_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelatArtic'+'/%QUERY'
    });

relatArtic_bloodhound.initialize();

function relatArtictypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'relatArtic',
          displayKey: 'name',
          source: relatArtic_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var locprim_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Location'+'/%QUERY'
    });

locprim_bloodhound.initialize();

function locprimtypeahead(target) {

     $(target).typeahead({
         minLength: 0,
         hint: false
     }, {
          name: 'locprim',
          displayKey: 'name',
          limit: 50,
          source: locprim_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var contType_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/ContactType'+'/%QUERY'
    });

contType_bloodhound.initialize();

function contTypetypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'contType',
          displayKey: 'name',
          source: contType_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var movSh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementShape'+'/%QUERY'
    });

movSh_bloodhound.initialize();

function movShtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'movSh',
          displayKey: 'name',
          source: movSh_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var movDir_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementDir'+'/%QUERY'
    });

movDir_bloodhound.initialize();

function movDirtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'movDir',
          displayKey: 'name',
          source: movDir_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relOriMov_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelOriMov'+'/%QUERY'
    });

relOriMov_bloodhound.initialize();

function relOriMovtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'relOriMov',
          displayKey: 'name',
          source: relOriMov_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relOriLoc_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelOriLoc'+'/%QUERY'
    });

relOriLoc_bloodhound.initialize();

function relOriLoctypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'relOriLoc',
          displayKey: 'name',
          source: relOriLoc_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var oriCh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/OriChange'+'/%QUERY'
    });

oriCh_bloodhound.initialize();

function oriChtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'oriCh',
          displayKey: 'name',
          source: oriCh_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var namEnt_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/NamedEntity'+'/%QUERY'
    });

namEnt_bloodhound.initialize();

function namEnttypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'namEnt',
          displayKey: 'name',
          source: namEnt_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var valence_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Valence'+'/%QUERY'
    });

valence_bloodhound.initialize();

function valencetypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'valence',
          displayKey: 'name',
          source: valence_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var wordClass_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/WordClass'+'/%QUERY'
    });

wordClass_bloodhound.initialize();

function wordClasstypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'wordClass',
          displayKey: 'name',
          source: wordClass_bloodhound.ttAdapter(),
          autoSelect: false,
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
// last of the field choice bloodhounds

var selected_semField = selected_semField;

var semField_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/semField'+'/%QUERY'
    });

semField_bloodhound.initialize();

function semFieldtypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'semField',
          displayKey: 'name',
          source: semField_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

function renderSelectedSemField() {
    var container = $('#semField_value');
    container.empty();
    var values_input = $('#semField_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#semField_multiselect');
    selected_semField.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="semField" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_semField = selected_semField.filter(i => i !== item);
            renderSelectedSemField();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_semField.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
    placeholder_lookahead.css("color", "red");
}

var selected_derivHist = selected_derivHist;

var derivHist_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/derivHist'+'/%QUERY'
    });

derivHist_bloodhound.initialize();

function derivHisttypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'derivHist',
          displayKey: 'name',
          source: derivHist_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

function renderSelectedDerivHist() {
    var container = $('#derivHist_value');
    container.empty();
    var values_input = $('#derivHist_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#derivHist_multiselect');
    selected_derivHist.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="derivHist" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_derivHist = selected_derivHist.filter(i => i !== item);
            renderSelectedDerivHist();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_derivHist.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
}

var selected_dialect = selected_dialect;

var dialect_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/dialect/'+gloss_dataset_id+'/%QUERY'
    });

dialect_bloodhound.initialize();

function dialecttypeahead(target) {

     $(target).typeahead({
         minLength: 0
     }, {
          name: 'dialect',
          displayKey: 'name',
          source: dialect_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

function renderSelectedDialect() {
    var container = $('#dialect_value');
    container.empty();
    var values_input = $('#dialect_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#dialect_multiselect');
    selected_dialect.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="dialect" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_dialect = selected_dialect.filter(i => i !== item);
            renderSelectedDialect();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_dialect.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
    placeholder_lookahead.css("color", "red");
}

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

function disable_edit_morphology() {
    $('#add_morphologydefinition_form').hide();
    $('#add_morphemedefinition_form').hide();
    $('#add_blenddefinition_form').hide();
    $('.morphology_delete_edit_only').each(function() {
        $(this).hide();
    });
    $('.button-morphology-to-appear-in-edit-mode').hide();
    $('.empty_row_morphology').each(function() {
        $(this).hide();
    });
}

$(".morphology-edit-dismiss").on('click', function() {
    $('#add_morphologydefinition_form').hide();
    $('#add_morphemedefinition_form').hide();
    $('#add_blenddefinition_form').hide();
    $('.morphology_delete_edit_only').each(function() {
        $(this).hide();
    });
    $(this).hide();
    $('#enable_edit_morphology').show();
    $('.empty_row_morphology').each(function() {
        $(this).hide();
    });
});

$("#enable_edit_morphology").on('click', function() {
    $('#add_morphologydefinition_form').show();
    $('#add_morphemedefinition_form').show();
    $('#add_blenddefinition_form').show();
    $('.morphology_delete_edit_only').each(function() {
        $(this).show();
    });
    $('.empty_row_morphology').each(function() {
        $(this).show();
    });
    $('.button-morphology-to-appear-in-edit-mode').show();
    $(this).hide();
});

function disable_edit_relations() {
    $('#add_relation_form').hide();
    $('.relation_delete_edit_only').each(function() {
        $(this).hide();
    });
    $('.button-relations-to-appear-in-edit-mode').hide();
}

$(".relation-edit-dismiss").on('click', function() {
    $('#add_relation_form').hide();
    $('.relation_delete_edit_only').each(function() {
        $(this).hide();
    });
    $(this).hide();
    $('#enable_edit_relations').show();
});

$("#enable_edit_relations").on('click', function() {
    $('#add_relation_form').show();
    $('.relation_delete_edit_only').each(function() {
        $(this).show();
    });
    $('.button-relations-to-appear-in-edit-mode').show();
    $(this).hide();
});

function disable_edit_foreignrelations() {
    $('#add_relationtoforeignsign_form').hide();
    $('.edit_only_foreignrelations').each(function() {
        $(this).hide();
    });
    $('.button-foreignrelations-to-appear-in-edit-mode').hide();
    disable_lookaheads('foreignrelations');
    $('#enable_edit_foreignrelations').show();
}

$(".foreignrelations-edit-dismiss").on('click', function() {
    $('#add_relationtoforeignsign_form').hide();
    $('.edit_only_foreignrelations').each(function() {
        $(this).hide();
    });
    disable_lookaheads('foreignrelations');
    $(this).hide();
    $('#enable_edit_foreignrelations').show();
});

$("#enable_edit_foreignrelations").on('click', function() {
    $('#add_relationtoforeignsign_form').show();
    $('.edit_only_foreignrelations').each(function() {
        $(this).show();
    });
    $('.button-foreignrelations-to-appear-in-edit-mode').show();
    $(this).hide();
    enable_lookaheads('foreignrelations');
});

$(".publication-edit-dismiss").on('click', function() {
    $('.edit_only_publication').each(function() {
        $(this).hide();
    });
    $('.read_only_publication').each(function() {
        $(this).show();
    });
    $('#enable_edit_publication').removeClass('edit_enabled').show();
    $('.button-publication-to-appear-in-edit-mode').hide();
});

function disable_edit_nme() {
    $('.edit_only_nme').each(function() {
        $(this).hide();
    });
    $('.read_only_nme').each(function() {
        $(this).show();
    });
    $('#nme_edit_dismiss').hide();
    $('#enable_edit_nme').show();
}

$(".nme-edit-dismiss").on('click', function() {
    $('.edit_only_nme').each(function() {
        $(this).hide();
    });
    $('.read_only_nme').each(function() {
        $(this).show();
    });
    $(this).hide();
    $('#enable_edit_nme').show();
});

$("#enable_edit_nme").on('click', function() {
    $('.edit_only_nme').each(function() {
        $(this).show();
    });
    $('.read_only_nme').each(function() {
        $(this).hide();
    });
    $('#nme_edit_dismiss').show();
    $(this).hide();
});

function disable_edit_notes() {
    $('.edit_only_notes').each(function() {
        $(this).hide();
    });
    $('.read_only_notes').each(function() {
        $(this).show();
    });
    disable_lookaheads('notes');
    $('#notes_edit_dismiss').hide();
    $('#enable_edit_notes').show();
}

$(".notes-edit-dismiss").on('click', function() {
    $('.edit_only_notes').each(function() {
        $(this).hide();
    });
    disable_lookaheads('notes');
    $('.read_only_notes').each(function() {
        $(this).show();
    });
    $(this).hide();
    $('#enable_edit_notes').show();
});

$("#enable_edit_notes").on('click', function() {
    $('.edit_only_notes').each(function() {
        $(this).show();
    });
    $('.read_only_notes').each(function() {
        $(this).hide();
    });
    $('#notes_edit_dismiss').show();
    $(this).hide();
    enable_lookaheads('notes');
});

function disable_edit_provenance() {
    $('.edit_only_provenance').each(function() {
        $(this).hide();
    });
    $('.read_only_provenance').each(function() {
        $(this).show();
    });
    disable_lookaheads('provenance');
    $('#provenance_edit_dismiss').hide();
    $('#enable_edit_provenance').show();
}

$(".provenance-edit-dismiss").on('click', function() {
    $('.edit_only_provenance').each(function() {
        $(this).hide();
    });
    disable_lookaheads('provenance');
    $('.read_only_provenance').each(function() {
        $(this).show();
    });
    $(this).hide();
    $('#enable_edit_provenance').show();
});

$("#enable_edit_provenance").on('click', function() {
    $('.edit_only_provenance').each(function() {
        $(this).show();
    });
    $('.read_only_provenance').each(function() {
        $(this).hide();
    });
    $('#provenance_edit_dismiss').show();
    $(this).hide();
    enable_lookaheads('provenance');
});

function disable_edit_annotated_sentences() {
    $('.edit_only_annotated_sentences').each(function() {
        $(this).hide();
    });
    $("#annotated_sentences_edit_dismiss").hide();
}

$("#annotated_sentences_edit_dismiss").on('click', function() {
    $('.edit_only_annotated_sentences').each(function() {
        $(this).hide();
    });
    $('#enable_edit_annotated_sentences').show();
    $(this).hide();
});

$("#enable_edit_annotated_sentences").on('click', function() {
    $('.edit_only_annotated_sentences').each(function() {
        $(this).show();
    });
    $(".annotated_sentences_edit_dismiss").each(function() {
        $(this).show();
    });
    $(this).hide();
});

function disable_edit_othermedia() {
    $('.edit_only_othermedia').each(function() {
        $(this).hide();
    });
    $('.read_only_othermedia').each(function() {
        $(this).show();
    });
    disable_lookaheads('othermedia');
    $('#othermedia_edit_dismiss').hide();
    $('#enable_edit_othermedia').show();
}

$(".othermedia-edit-dismiss").on('click', function() {
    $('.edit_only_othermedia').each(function() {
        $(this).hide();
    });
    disable_lookaheads('othermedia');
    $('.read_only_othermedia').each(function() {
        $(this).show();
    });
    $(this).hide();
    $('#enable_edit_othermedia').show();
});

$("#enable_edit_othermedia").on('click', function() {
    $('.edit_only_othermedia').each(function() {
        $(this).show();
    });
    $('.read_only_othermedia').each(function() {
        $(this).hide();
    });
    $('#othermedia_edit_dismiss').show();
    $(this).hide();
    enable_lookaheads('othermedia');
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

function disable_lookaheads(category) {
     // this makes use of specific element identifiers for the lookahead fields
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

function enable_lookaheads(category) {
     // this makes use of specific element identifiers for the lookahead fields
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

function enable_edit_panel(category) {
    if (category === 'semantics') {
        $('.editsemanticsform').show();
        $('#semField_value').trigger('editSemField');
        $('#derivHist_value').trigger('editDerivHistField');
    }
    if (category === 'general') {
        $('.read_only').hide();
        $('.edit_only').show();
        $('.editdialectform').show();
        $('.editform').show();  // appears in gloss tags and affiliations
        $('#dialect_value').trigger('editDialectField');
        $('#lemma_buttons_group').show();
    }
    if (category === 'publication') {
        $('.read_only_publication').hide();
        $('.edit_only_publication').show();
    }
    $('.empty_row_'+category).show();
    $('#enable_edit_'+category).addClass('edit_enabled').hide();
    $('.button-'+category+'-to-appear-in-edit-mode').show();
    enable_lookaheads(category);
}

function disable_edit_panel(category) {
    if (category === 'semantics') {
        $('.editsemanticsform').hide();
    }
    if (category === 'general') {
        $('.editdialectform').hide();
        $('#lemma_buttons_group').hide();
        $('#lemma_forms_row').hide();
        $('.editform').hide();  // appears in gloss tags and affiliations
        $('.read_only').show();
        $('.edit_only').hide();
    }
    if (category === 'publication') {
        $('.read_only_publication').show();
        $('.edit_only_publication').hide();
    }
    $('.empty_row_'+category).hide();
    $('.button-'+category+'-to-appear-in-edit-mode').hide();
    $('#enable_edit_'+category).removeClass('edit_enabled').show();
    disable_lookaheads(category);
    busy_editing = false;
}

function toggle_edit_general() {
    if ($('#enable_edit_general').hasClass('edit_enabled'))
    {
        disable_edit_panel('general');
    } else {
        enable_edit_panel('general');
    }
}

function toggle_edit_phonology() {
    if ($('#enable_edit_phonology').hasClass('edit_enabled'))
    {
        disable_edit_panel('phonology');
    } else {
        enable_edit_panel('phonology');
    }
}

function toggle_edit_semantics() {
    if ($('#enable_edit_semantics').hasClass('edit_enabled'))
    {
        disable_edit_panel('semantics');
    } else {
        enable_edit_panel('semantics');
    }
}

function toggle_edit_publication() {
    if ($('#enable_edit_publication').hasClass('edit_enabled'))
    {
        disable_edit_panel('publication');
    } else {
        enable_edit_panel('publication');
    }
}

function get_width_of_selection(text) {
    let $span = $('<span>')
        .text(text)
        .css({
            position: 'absolute',
            visibility: 'hidden',
            whiteSpace: 'nowrap',
        })
        .appendTo('body');
    let width = $span.width();
    $span.remove();
    return width;
}

$(document).ready(function() {

    handednesstypeahead($('.handednesstypeahead'));
    $('.handednesstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          $('#handedness_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#handedness_lookahead').on("click", function() {
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
    domhndshtypeahead($('.domhndshtypeahead'));
    $('.domhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#domhndsh_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#domhndsh_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    subhndshtypeahead($('.subhndshtypeahead'));
    $('.subhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#subhndsh_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#subhndsh_lookahead').on("click", function() {
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
    handChtypeahead($('.handChtypeahead'));
    $('.handChtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#handCh_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#handCh_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    relatArtictypeahead($('.relatArtictypeahead'));
    $('.relatArtictypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#relatArtic_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#relatArtic_lookahead').on("click", function() {
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
    locprimtypeahead($('.locprimtypeahead'));
    $('.locprimtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#locprim_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#locprim_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    contTypetypeahead($('.contTypetypeahead'));
    $('.contTypetypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#contType_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#contType_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    movShtypeahead($('.movShtypeahead'));
    $('.movShtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#movSh_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#movSh_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    movDirtypeahead($('.movDirtypeahead'));
    $('.movDirtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#movDir_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#movDir_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    relOriMovtypeahead($('.relOriMovtypeahead'));
    $('.relOriMovtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#relOriMov_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#relOriMov_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    relOriLoctypeahead($('.relOriLoctypeahead'));
    $('.relOriLoctypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#relOriLoc_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#relOriLoc_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    oriChtypeahead($('.oriChtypeahead'));
    $('.oriChtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#oriCh_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#oriCh_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    namEnttypeahead($('.namEnttypeahead'));
    $('.namEnttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#namEnt_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#namEnt_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    valencetypeahead($('.valencetypeahead'));
    $('.valencetypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#valence_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#valence_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    wordClasstypeahead($('.wordClasstypeahead'));
    $('.wordClasstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $(this).attr('placeholder', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#wordClass_machine_value').attr('value', suggestion.machine_value);
          $(this).attr('data-preselect', suggestion.machine_value);
    });
    $('#wordClass_lookahead').on("click", function() {
      var preselect_machine_value = $(this).attr('data-preselect');
      if (!preselect_machine_value) {
        $(this).val('').trigger('input').typeahead('open');
        return;
      }
      var preselect_name = $(this).attr('placeholder');
      if (!preselect_name) {return;}
      $(this).attr("val", preselect_name);
      $(this).trigger('typeahead:selected', [{'name': preselect_name, 'machine_value': preselect_machine_value}]);
    });
    semFieldtypeahead($('.semFieldtypeahead'));
    $('.semFieldtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_semField.includes(suggestion)) {
                busy_editing = true;
                selected_semField.push(suggestion);
                renderSelectedSemField();
          }
          $(this).typeahead('val', '');
    });
    $('#semField_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#semField_value').on("editSemField", function() {
        renderSelectedSemField();
    });
    derivHisttypeahead($('.derivHisttypeahead'));
    $('.derivHisttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_derivHist.includes(suggestion)) {
                busy_editing = true;
                selected_derivHist.push(suggestion);
                renderSelectedDerivHist();
          }
          $(this).typeahead('val', '');
    });
    $('#derivHist_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#derivHist_value').on("editDerivHistField", function() {
        renderSelectedDerivHist();
    });
    dialecttypeahead($('.dialecttypeahead'));
    $('.dialecttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_dialect.includes(suggestion)) {
                busy_editing = true;
                selected_dialect.push(suggestion);
                renderSelectedDialect();
          }
          $(this).typeahead('val', '');
    });
    $('#dialect_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#dialect_value').on("editDialectField", function() {
        renderSelectedDialect();
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
    $('.select_weakdrop').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakdrop_value').text(selected_text);
    });

    $('.select_weakprop').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakprop_value').text(selected_text);
    });

    $('.select_domhndsh_letter_or_number_field').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#domhndsh_letter_or_number_field_value').text(selected_text);
    });

    $('.select_subhndsh_letter_or_number').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#subhndsh_letter_or_number_value').text(selected_text);
    });

    $('.select_repeat').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#repeat_value').text(selected_text);
    });
    $('.select_altern').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#altern_value').text(selected_text);
    });
    $('.select_inWeb').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#inWeb_value').text(selected_text);
    });
    $('.select_isNew').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#isNew_value').text(selected_text);
    });
    $('.select_excludeFromEcv').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#excludeFromEcv_value').text(selected_text);
    });
     $('.quick_save').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < gloss_fields.length; i++) {
            var field = gloss_fields[i];
            if (['semField', 'derivHist', 'dialect'].includes(field)) {
                var field_values = [];
                var field_lookup = '#'+field+'_hidden_input_values';
                $(field_lookup).find('input[name="'+field+'"]').each(function() {
                    var this_value = $(this).val();
                    field_values.push(this_value);
                });
                update[field] = field_values;
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
                var field_lookup = '#'+field+'_machine_value';
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
         var placeholder_text = $(this).attr("placeholder");
         if (!placeholder_text) {return;}
         var width_of_new_value = placeholder_text.length * 10 + 30;
         $(cell_lookup).attr('data-width', width_of_new_value);
    });
    var cell_elements = $('[id*="_cell"]');
    cell_elements.each(function() {
        var data_width = $(this).attr("data-width");
        if (!data_width) {return;}
        var this_width = data_width + "px";
        $(this).css('width', this_width);
    });
    busy_editing = false;
    $('#enable_edit_general').on("click", function() {
        toggle_edit_general();
    });
    $('#enable_edit_phonology').on("click", function() {
        toggle_edit_phonology();
    });
    $('#enable_edit_semantics').on("click", function() {
        toggle_edit_semantics();
    });
    $('#enable_edit_publication').on("click", function() {
        toggle_edit_publication();
    });
    $('#enable_edit_nme').on("click", function() {
        toggle_edit_publication();
    });
    disable_edit_panel('general');
    disable_edit_panel('phonology');
    disable_edit_panel('semantics');
    disable_edit_panel('publication');
    disable_edit_relations();
    disable_edit_foreignrelations();
    disable_edit_morphology();
    disable_edit_nme();
    disable_edit_notes();
    disable_edit_provenance();
    disable_edit_annotated_sentences();
    disable_edit_othermedia();
    ajaxifyTagForm();
});
