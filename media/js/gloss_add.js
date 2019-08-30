var languages = [];
var lemma_create_field_prefix = "";  // To be set in the template

function set_annotationidglosslanguages() {
//    console.log('set_annotationidglosslanguages gloss_add.js');
    var languages_str = $('#id_dataset').find(":selected").attr('dataset_languages');
    languages = languages_str.split(",");
    // Toggle annotationidglosstranslation fields
    $("[id*='add_gloss_dataset_']").each(function(){
        $(this).hide();
    });
    $("[id*='glosscreate_']").each(function(){
        $(this).prop('required', false);
    });
    // the add_morpheme template uses a different id for creation
    // either the glosscreate or the morphemecreate won't match anything and has no effect
    $("[id*='morphemecreate_']").each(function(){
        $(this).prop('required', false);
    });
    for(var id in languages) {
        $("[id*='add_gloss_dataset_header_" + languages[id] + "']").show();
        $("[id*='add_gloss_dataset_value_" + languages[id] + "']").show();
        $("[id*='glosscreate_" + languages[id] + "']").prop('required', true);
        // the add_morpheme template uses a different id for creation
        // either the glosscreate or the morphemecreate won't match anything and has no effect
        $("[id*='morphemecreate_" + languages[id] + "']").prop('required', true);
    };

    // Toggle lemmaidglosstranslation fields
    $("[id*='lemmacreate_']").each(function(){
        if ($(this).is("input")) {
            $(this).prop('required', false);
        };
        $(this).hide();
    });

    $("[id*='lemma_language_']").each(function(){
        $(this).hide();
        $(this).prop('checked', false);
    });
    var number_of_languages = languages.length;
    if (number_of_languages > 1) {
        for(var id in languages) {
            var this_language_code = languages[id];
            $("[id*='lemma_language_" + this_language_code + "']").show();
            $("[id*='lemma_language_label_" + this_language_code + "']").show();
            $("[id*='lemmacreate_" + this_language_code + "']").show();
            $("[id*='lemmacreate__header_" + this_language_code + "']").show();
        }
    } else {
        // there is only one language available (either for the Signbank or for the Dataset)
        // make this language be checked, although not visible in the template
        $("[id*='lemma_language_" + languages + "']").prop('checked', true);
    };
    var selected_language = $("#id_dataset").val();
    if (selected_language) {
        if (number_of_languages > 1) {
            var first_language = languages[0];
            $("[id*='lemma_language_" + first_language + "']").prop('checked',true);
        } else {
            $("[id*='lemma_language_" + languages + "']").prop('checked',true);
            $("[id*='lemmacreate_" + languages + "']").show();
        }
    };
}

// Initialize the select vs add lemma form part
$("#lemma_add").hide();
var select_or_new_lemma_value = $("#select_or_new_lemma").val();

// Toggle select/add lemma
function toggleAddLemma() {
//    console.log('toggleAddLemma gloss_add.js');

    $("#lemma_select").toggle();
    $("#lemma_add").toggle();
    // Register whether the user is selecting a lemma idgloss or creating a new one
    select_or_new_lemma_value = $("#select_or_new_lemma").val();
    select_or_new_lemma_value = select_or_new_lemma_value === "select" ? "new" : "select";
    $("#select_or_new_lemma").val(select_or_new_lemma_value);

    // Deal with required fields
    if(select_or_new_lemma_value === "select") {
        $("[id*='lemmacreate_']").each(function(){
            if ($(this).is("input")) {
                $(this).prop('required', false);
            };
            $(this).hide();
        });
    } else {
        var number_of_languages = languages.length;
        if (number_of_languages > 1) {
            for(var id in languages) {
                var this_language_code = languages[id];
                $("[id*='lemmacreate__header_" + this_language_code + "']").show();
                $("[id*='lemmacreate_" + this_language_code + "']").show();
                $("[id*='lemmacreate_" + this_language_code + "']").prop('required', true);
            }
        } else {
            // there is only one language available (either for the Signbank or for the Dataset)
            // make this language be checked, although not visible in the template
            $("[id*='lemmacreate_" + languages + "']").show();
            $("[id*='lemmacreate_" + languages + "']").prop('required', true);
        };
    };
    return false;
}