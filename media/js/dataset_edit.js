
$(document).ready(function() {
    usertypeahead($('.usertypeahead'));
    $('.usertypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.username)
        });
    $('.usertypeahead').on("input", function() {
          $(this).parent().next().val("")
        });

    // setup requried for Ajax POST
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
});

var user_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/user/%QUERY'
});

user_bloodhound.initialize();

function usertypeahead(target) {

     $(target).typeahead(null, {
          name: 'username',
          displayKey: 'username',
          source: user_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(user) {
                  return("<p>" + user.first_name + " " + user.last_name + " (<strong>" + user.username + "</strong>)</p>");
              }
          }
      });
};
