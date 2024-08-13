
function toggleClasses(selector, lightClass, darkClass) {
    $(selector).each(function () {
        if ($(this).hasClass(lightClass)) {
            $(this).removeClass(lightClass);
            $(this).addClass(darkClass);
        } else if ($(this).hasClass(darkClass)) {
            $(this).removeClass(darkClass);
            $(this).addClass(lightClass);
        }
    });
}

function toggle_dark_mode() {
  var r = document.querySelector(':root');
  $(".body").each(function () {
        if ($(this).hasClass("body-light")) {
            r.style.setProperty('--ultron', 'black');
            r.style.setProperty('--beam', 'white');
            r.style.setProperty('--typeahead-background', 'black');
            r.style.setProperty('--typeahead-color', 'white');
            $(this).removeClass("body-light");
            $(this).addClass("body-dark");
        } else if ($(this).hasClass("body-dark")) {
            r.style.setProperty('--ultron', 'white');
            r.style.setProperty('--beam', 'black');
            r.style.setProperty('--typeahead-background', 'white');
            r.style.setProperty('--typeahead-color', 'black');
            $(this).removeClass("body-dark");
            $(this).addClass("body-light");
        }
  });
  $(".modal").each(function () {
        if ($(this).hasClass("dark-mode")) {
            $(this).removeClass("dark-mode");
        } else {
            $(this).addClass("dark-mode");
        }
  });
  toggleClasses(".panel-default", "panel-light", "panel-default-dark");

  toggleClasses(".panel-heading", "panel-light", "panel-heading-dark");

  toggleClasses(".collapse", "collapse-light", "collapse-dark");

  toggleClasses(".well", "well-light", "well-dark");

  toggleClasses(".navbar", "navbar-light", "navbar-dark");

  toggleClasses(".navbar-nav", "navbar-nav-light", "navbar-nav-dark");

  toggleClasses(".navbar-form", "navbar-form-light", "navbar-form-dark");

  toggleClasses(".navbar-text", "navbar-text-light", "navbar-text-dark");

  toggleClasses(".dropdown", "dropdown-light", "dropdown-dark");

  toggleClasses(".dropdown-menu", "dropdown-menu-light", "dropdown-menu-dark");

  toggleClasses(".text-container", "text-container-light", "text-container-dark");

  toggleClasses(".interface-language", "interface-language-light", "interface-language-dark");

  toggleClasses(".input-group", "input-group-light", "input-group-dark");

  toggleClasses(".btn-default", "btn-default-light", "btn-default-dark");

  toggleClasses(".btn-action", "btn-action-light", "btn-action-dark");

  toggleClasses(".tbody", "tbody-light", "tbody-dark");

  toggleClasses(".thead", "thead-light", "thead-dark");

  toggleClasses(".tr", "tr-light", "tr-dark");

  toggleClasses(".td", "td-light", "td-dark");

  toggleClasses(".th", "th-light", "th-dark");

  toggleClasses(".table-condensed", "table-condensed-light", "table-condensed-dark");

  toggleClasses(".table-responsive", "table-responsive-light", "table-responsive-dark");

  toggleClasses(".table-bordered", "table-bordered-light", "table-bordered-dark");

  toggleClasses(".table-frequency", "table-frequency-light", "table-frequency-dark");

  toggleClasses(".frequency-table", "frequency-table-light", "frequency-table-dark");

  toggleClasses(".frequency-cell", "frequency-cell-light", "frequency-cell-dark");

  toggleClasses(".search-form", "search-form-light", "search-form-dark");

  toggleClasses(".span-text", "span-text-light", "span-text-dark");

  toggleClasses(".span-text", "span-text-light", "span-text-dark");

  toggleClasses(".morphtypeahead", "morphtypeahead-light", "morphtypeahead-dark");

  toggleClasses(".handshapetypeahead", "handshapetypeahead-light", "handshapetypeahead-dark");

  toggleClasses(".usertypeahead", "usertypeahead-light", "usertypeahead-dark");

  toggleClasses(".lemmatypeahead", "lemmatypeahead-light", "lemmatypeahead-dark");

  toggleClasses(".pages-form", "pages-form-light", "pages-form-dark");

  toggleClasses(".form-group", "form-group-light", "form-group-dark");

  toggleClasses(".form-control", "form-control-light", "form-control-dark");

  toggleClasses(".btn-group", "btn-group-light", "btn-group-dark");

  toggleClasses(".view-tabs", "view-tabs-light", "view-tabs-dark");

  toggleClasses(".nav-tabs", "nav-tabs-light", "nav-tabs-dark");

  toggleClasses(".query-toggles", "query-toggles-light", "query-toggles-dark");

  toggleClasses(".preview", "preview-light", "preview-dark");

  toggleClasses(".color-form", "color-form-light", "color-form-dark");

  $(".color-field-choices").each(function () {
        var dark_mode = $(this).attr("data-mode");
        if ($(this).hasClass("color-field-choices-light")) {
            $(this).removeClass("color-field-choices-light");
            $(this).addClass("color-field-choices-dark");
            if (dark_mode == 'False') {
                location.reload();
            };
        } else if ($(this).hasClass("color-field-choices-dark")) {
            $(this).removeClass("color-field-choices-dark");
            $(this).addClass("color-field-choices-light");
            if (dark_mode == 'True') {
                location.reload();
            };
        }
  });
}

function set_dark_mode(){
    $.ajax({
        url : set_dark_mode_url,
        type: 'POST',
        data: {},
        datatype: "json"
     });
     toggle_dark_mode();
}
