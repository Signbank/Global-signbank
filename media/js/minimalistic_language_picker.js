"use strict";

jQuery.fn.minimalistic_language_picker = function(language_codes,language_names,chosen_language,callback)
{
    //Basic values
    $(this).attr('languages',language_codes);
    $(this).attr('chosen_language',chosen_language);
    $(this).attr('language_names',language_names);

    //Set the image
    $(this).show_chosen_language();

    //Add the hover behavior
    $(this).mouseenter(function()
    {
	if (!$(this).hasClass('active_language_picker'))
	{
		$(this).show_all_languages(callback);
	}
    });

    $(this).mouseleave(function()
    {
    	$(this).show_chosen_language();
    });
};

jQuery.fn.show_chosen_language = function()
{
    $(this).removeClass('active_language_picker'); //Changes layout

    //The layout below is Signbank specific
    $(this).css('margin-right',0);
    $(this).css('margin-top',0);
    $(this).css('margin-bottom',4);

    var all_languages = $(this).attr('languages').split(',');
    var language_names = $(this).attr('language_names').split(',');
    var chosen_language = $(this).attr('chosen_language');
	
    $(this).html('<div>'+language_names[all_languages.indexOf(chosen_language)]+'</div>');
}

jQuery.fn.show_all_languages = function(callback)
{
    //Preparatory work
    var SPACE_BETWEEN_ITEMS = 4;
    var HEIGHT_OF_ITEMS = 11;
    $(this).addClass('active_language_picker'); //Changes layout

    //The layout below is Signbank specific
    $(this).css('margin-right',0);
    $(this).css('margin-top',-30);
    $(this).css('margin-bottom',4);

    //Take data from the element
    var all_languages = $(this).attr('languages').split(',');
    var language_names = $(this).attr('language_names').split(',');
    var chosen_language = $(this).attr('chosen_language');

    //Define vars needed later
    var html_content = '<div style="margin-bottom:'+SPACE_BETWEEN_ITEMS+'px;" >'+language_names[all_languages.indexOf(chosen_language)]+'</div>';
    var current_language_code;
	var current_language_name;
    var current_amount_of_pixels_down = 0;
    var nr_of_languages_processed = 1;

    //Show all languages
    for (var language_index in all_languages)
    {
        //Skip the chosen language, we already showed that one
        if (all_languages[language_index] == chosen_language)
        {
            continue;
        }

        current_language_code = all_languages[language_index];
		current_language_name = language_names[language_index];
        current_amount_of_pixels_down = nr_of_languages_processed * (HEIGHT_OF_ITEMS + SPACE_BETWEEN_ITEMS);

        //Give a bottom margin to all languages but the last
        var margin_bottom = 'margin-bottom:'+SPACE_BETWEEN_ITEMS+'px';

        //Add the language
        html_content += '<div class="language_button" id="language_'+current_language_code+'"  language_code="'+current_language_code+'" style="'+margin_bottom+'">'+current_language_name+'</div>';
        nr_of_languages_processed += 1;
    }

    //Show the created html
    $(this).html(html_content);

    //Move a language to the top when clicked
    $('.language_button').click(function()
    {
        $(this).css('z-index',2);
        $(this).animate({top: $(this).attr('start-top')}, 200, function()
        {
            //When done moving the language up, change the selected language and show this
            $(this).parent().attr('chosen_language',$(this).attr('language_code'));
            $(this).parent().show_chosen_language();
            callback($(this).attr('language_code'));
        });
    });
}