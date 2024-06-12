$(document).ready(function () {

    $('#eaffile').change(function () {
        var formData = new FormData();
        formData.append('eaffile', $('#eaffile')[0].files[0]); // Add the file input to the FormData object
        formData.append('check_gloss_label', [$('#check_gloss_label').val()]); // Add the gloss label to check in checkbox
        formData.append('csrfmiddlewaretoken', $('input[name=csrfmiddlewaretoken]').val()); // Include the CSRF token in the FormData object
        formData.append('dataset', $('#dataset').val()); // add the dataset to the formdata

        $.ajax({
            url: '/video/process_eaffile/',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                
                // Check if the response contains an error
                if ('error' in response) {
                    $('#feedback').html(response.error);
                    $('#eaffile').wrap('<form>').closest('form').get(0).reset();
                    $('#eaffile').unwrap();
                    return;
                }

                // Iterate over the JSON data and create rows in the table dynamically
                $('#feedback').html(response.annotations_table_html);

                // Add the sentence data to the input field where name = translation_nld
                var sentenceData = JSON.parse(response.sentences);
                var sentenceText = ""
                for (var key in sentenceData) {
                    sentenceText += sentenceData[key];
                }
                // hardcoded to translation_nld because ATM this is only used for Dutch translations
                if ($('#translation_nld').length) {
                    $('#translation_nld').val(sentenceText);
                    $('.translation-input').trigger('input');
                }
            },
            error: function (xhr, status, error) {
                console.error(xhr.responseText);
            }
        });
    });
    

    $('#annotatedSentenceForm').submit(function (event) {
        // Get all table rows except the header row
        var rows = $('#feedback table tbody tr');
        var feedbackData = '';

        // Iterate over each table row
        rows.each(function() {
            var row = $(this);
            var gloss = row.find('td:eq(0)').text(); // Get the gloss value
            var representative = row.find('td:eq(1) input[type="checkbox"]').prop('checked') ? '1' : '0'; // Check if checkbox is checked or not
            var starttime = row.find('td:eq(2)').text(); // Get the starttime value
            var endtime = row.find('td:eq(3)').text(); // Get the endtime value

            // Concatenate gloss and its attributes with a separator
            feedbackData += gloss + ':' + representative + ':' + starttime + ':' + endtime + ';';
        });

        // Append the feedback data to a hidden input field in the form
        $('<input>').attr({
            type: 'hidden',
            name: 'feedbackdata',
            value: feedbackData
        }).appendTo('#annotatedSentenceForm');
        
        // Continue with form submission
        return true;
    });

    // jQuery script to update the hidden translations field as text fields are filled
    $('.translation-input').on('input', function() {
        var translations = {};

        // Populate translations object with language code and value
        $('.translation-input').each(function() {
            var langCode = $(this).attr('name').replace('translation_', '');
            var translationValue = $(this).val();
            translations[langCode] = translationValue;
        });

        // Update value of hidden translations input field
        $('#translations-hidden').val(JSON.stringify(translations));
    });

    // jQuery script to update the hidden context field as text fields are filled
    $('.context-input').on('input', function() {
        var contexts = {};

        // Populate context object with language code and value
        $('.context-input').each(function() {
            var langCode = $(this).attr('name').replace('context_', '');
            var contextValue = $(this).val();
            contexts[langCode] = contextValue;
        });

        // Update value of hidden contexts input field
        $('#contexts-hidden').val(JSON.stringify(contexts));
    });
});