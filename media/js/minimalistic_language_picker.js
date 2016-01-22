"use strict";

jQuery.fn.minimalistic_language_picker = function(languages,chosen_language,image_root,callback)
{
    //Basic values
    $(this).attr('languages',languages);
    $(this).attr('chosen_language',chosen_language);
    $(this).attr('image_root',image_root);

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
    $(this).css('height','15px'); //Needed because the flag will stay invisibly long

    //The layout below is Signbank specific
    $(this).css('margin-right',9);
    $(this).css('margin-top',-53);

    var image_root = $(this).attr('image_root');
    var chosen_language = $(this).attr('chosen_language');
    $(this).html('<img class="flagbutton" src="'+image_root+chosen_language+'.png">');
}

jQuery.fn.show_all_languages = function(callback)
{
    //Preparatory work
    var SPACE_BETWEEN_FLAGS = 4;
    var HEIGHT_OF_FLAGS = 11;
    $(this).addClass('active_language_picker'); //Changes layout

    //The layout below is Signbank specific
    $(this).css('margin-right',2);
    $(this).css('margin-top',-60);

    //Take data from the element
    var image_root = $(this).attr('image_root');
    var all_languages = $(this).attr('languages').split(',');
    var chosen_language = $(this).attr('chosen_language');

    //Define vars needed later
    var html_content = '<img style="margin-bottom:'+SPACE_BETWEEN_FLAGS+'px;" class="flagbutton flag_of_chosen_language" src="'+image_root+chosen_language+'.png">';
    var current_language_code;
    var current_amount_of_pixels_down = 0;
    var nr_of_flags_processed = 1;

    //Show all flags
    for (var language_index in all_languages)
    {
        //Skip the chosen language, we already showed that one
        if (all_languages[language_index] == chosen_language)
        {
            continue;
        }

        current_language_code = all_languages[language_index];
        current_amount_of_pixels_down = nr_of_flags_processed * (HEIGHT_OF_FLAGS + SPACE_BETWEEN_FLAGS);

        //Give a bottom margin to all flags but the last
        var margin_bottom = 'margin-bottom:'+SPACE_BETWEEN_FLAGS+'px';

        if (language_index == all_languages.length-1)
        {
	    margin_bottom = '';
        }

        //Add the flag, below the highest flag (will be animated down)
        html_content += '<img class="flagbutton" id="flag_'+current_language_code+'"  language_code="'+current_language_code+'" style="top:-'+current_amount_of_pixels_down+'px;'+margin_bottom+'" start-top="-'+current_amount_of_pixels_down+'" src="'+image_root+current_language_code+'.png">';
        nr_of_flags_processed += 1;
    }

    //Show the created html
    $(this).html(html_content);

    //Animate all flags to their real position
    for (var language_index in all_languages)
    {
        current_language_code = all_languages[language_index];
	$("#flag_"+current_language_code).animate({'top':0},400);
    }

    //Also grow the height of the picker
    var picker_height = ((SPACE_BETWEEN_FLAGS+HEIGHT_OF_FLAGS) * all_languages.length) + 10;
    $(this).animate({'height':picker_height},400);

    //Move a flag up when clicked flag is clicked
    $('.flagbutton').click(function()
    {
        $(this).css('z-index',2);
        $(this).animate({top: $(this).attr('start-top')}, 200, function()
        {
            //When done moving the flag up, change the selected language and show this
            $(this).parent().attr('chosen_language',$(this).attr('language_code'));
            $(this).parent().show_chosen_language();
            callback($(this).attr('language_code'));
        });
    });
}