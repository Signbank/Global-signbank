var languages = [];
var lemma_create_field_prefix = "";  // To be set in the template

function set_annotationidglosslanguages() {
    console.log("set_annotationidglosslanguages called");
    var languages_str = $('#id_dataset').find(":selected").attr('dataset_languages');
    languages = languages_str.split(",");

    // Toggle annotationidglosstranslation fields
    $("[id*='add_gloss_dataset_']").each(function(){
        $(this).hide();
    });
    $("[id*='glosscreate_']").each(function(){
        $(this).prop('required', false);
    });
    for(var id in languages) {
        $("[id*='add_gloss_dataset_header_" + languages[id] + "']").show();
        $("[id*='add_gloss_dataset_value_" + languages[id] + "']").show();
        $("[id*='glosscreate_" + languages[id] + "']").prop('required', true);
    }

    // Toggle lemmaidglosstranslation fields
    $("[id*='"+lemma_create_field_prefix+"']").each(function(){
        $(this).hide();
        $(this).prop('required', false);
    });
    for(var id in languages) {
        $("[id*='" + lemma_create_field_prefix + "_header_" + languages[id] + "']").show();
        $("[id*='" + lemma_create_field_prefix + languages[id] + "']").show();
        if(select_or_new_lemma_value === "new") {
            $("[id*='" + lemma_create_field_prefix + languages[id] + "']").prop('required', true);
        }
    }
}

// Initialize the select vs add lemma form part
$("#lemma_add").hide();
var select_or_new_lemma_value = $("#select_or_new_lemma").val();

// Toggle select/add lemma
function toggleAddLemma() {
    $("#lemma_select").toggle();
    $("#lemma_add").toggle();

    // Register whether the user is selecting a lemma idgloss or creating a new one
    select_or_new_lemma_value = $("#select_or_new_lemma").val();
    select_or_new_lemma_value = select_or_new_lemma_value === "select" ? "new" : "select";
    $("#select_or_new_lemma").val(select_or_new_lemma_value);

    // Deal with required fields
    if(select_or_new_lemma_value === "select") {
        $("[id*='" + lemma_create_field_prefix + "']").each(function(){
            $(this).prop('required', false);
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