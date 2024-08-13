

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
  $(".panel-default").each(function () {
        if ($(this).hasClass("panel-light")) {
            $(this).removeClass("panel-light");
            $(this).addClass("panel-default-dark");
        } else if ($(this).hasClass("panel-default-dark")) {
            $(this).removeClass("panel-default-dark");
            $(this).addClass("panel-light");
        }
  });
  $(".panel-heading").each(function () {
        if ($(this).hasClass("panel-light")) {
            $(this).removeClass("panel-light");
            $(this).addClass("panel-heading-dark");
        } else if ($(this).hasClass("panel-heading-dark")) {
            $(this).removeClass("panel-heading-dark");
            $(this).addClass("panel-light");
        }
  });
  $(".collapse").each(function () {
        if ($(this).hasClass("collapse-light")) {
            $(this).removeClass("collapse-light");
            $(this).addClass("collapse-dark");
        } else if ($(this).hasClass("collapse-dark")) {
            $(this).removeClass("collapse-dark");
            $(this).addClass("collapse-light");
        }
  });
  $(".well").each(function () {
        if ($(this).hasClass("well-light")) {
            $(this).removeClass("well-light");
            $(this).addClass("well-dark");
        } else if ($(this).hasClass("well-dark")) {
            $(this).removeClass("well-dark");
            $(this).addClass("well-light");
        }
  });
  $(".navbar").each(function () {
        if ($(this).hasClass("navbar-light")) {
            $(this).removeClass("navbar-light");
            $(this).addClass("navbar-dark");
        } else if ($(this).hasClass("navbar-dark")) {
            $(this).removeClass("navbar-dark");
            $(this).addClass("navbar-light");
        }
  });
  $(".navbar-nav").each(function () {
        if ($(this).hasClass("navbar-nav-light")) {
            $(this).removeClass("navbar-nav-light");
            $(this).addClass("navbar-nav-dark");
        } else if ($(this).hasClass("navbar-nav-dark")) {
            $(this).removeClass("navbar-nav-dark");
            $(this).addClass("navbar-nav-light");
        }
  });
  $(".navbar-form").each(function () {
        if ($(this).hasClass("navbar-form-light")) {
            $(this).removeClass("navbar-form-light");
            $(this).addClass("navbar-form-dark");
        } else if ($(this).hasClass("navbar-form-dark")) {
            $(this).removeClass("navbar-form-dark");
            $(this).addClass("navbar-form-light");
        }
  });
  $(".navbar-text").each(function () {
        if ($(this).hasClass("navbar-text-light")) {
            $(this).removeClass("navbar-text-light");
            $(this).addClass("navbar-text-dark");
        } else if ($(this).hasClass("navbar-text-dark")) {
            $(this).removeClass("navbar-text-dark");
            $(this).addClass("navbar-text-light");
        }
  });
  $(".dropdown").each(function () {
        if ($(this).hasClass("dropdown-light")) {
            $(this).removeClass("dropdown-light");
            $(this).addClass("dropdown-dark");
        } else if ($(this).hasClass("dropdown-dark")) {
            $(this).removeClass("dropdown-dark");
            $(this).addClass("dropdown-light");
        }
  });
  $(".dropdown-menu").each(function () {
        if ($(this).hasClass("dropdown-menu-light")) {
            $(this).removeClass("dropdown-menu-light");
            $(this).addClass("dropdown-menu-dark");
        } else if ($(this).hasClass("dropdown-menu-dark")) {
            $(this).removeClass("dropdown-menu-dark");
            $(this).addClass("dropdown-menu-light");
        }
  });
  $(".text-container").each(function () {
        if ($(this).hasClass("text-container-light")) {
            $(this).removeClass("text-container-light");
            $(this).addClass("text-container-dark");
        } else if ($(this).hasClass("text-container-dark")) {
            $(this).removeClass("text-container-dark");
            $(this).addClass("text-container-light");
        }
  });
  $(".interface-language").each(function () {
        if ($(this).hasClass("interface-language-light")) {
            $(this).removeClass("interface-language-light");
            $(this).addClass("interface-language-dark");
        } else if ($(this).hasClass("interface-language-dark")) {
            $(this).removeClass("interface-language-dark");
            $(this).addClass("interface-language-light");
        }
  });
  $(".input-group").each(function () {
        if ($(this).hasClass("input-group-light")) {
            $(this).removeClass("input-group-light");
            $(this).addClass("input-group-dark");
        } else if ($(this).hasClass("input-group-dark")) {
            $(this).removeClass("input-group-dark");
            $(this).addClass("input-group-light");
        }
  });
  $(".btn-default").each(function () {
        if ($(this).hasClass("btn-default-light")) {
            $(this).removeClass("btn-default-light");
            $(this).addClass("btn-default-dark");
        } else if ($(this).hasClass("btn-default-dark")) {
            $(this).removeClass("btn-default-dark");
            $(this).addClass("btn-default-light");
        }
  });
  $(".btn-action").each(function () {
        if ($(this).hasClass("btn-action-light")) {
            $(this).removeClass("btn-action-light");
            $(this).addClass("btn-action-dark");
        } else if ($(this).hasClass("btn-action-dark")) {
            $(this).removeClass("btn-action-dark");
            $(this).addClass("btn-action-light");
        }
  });
  $(".tbody").each(function () {
        if ($(this).hasClass("tbody-light")) {
            $(this).removeClass("tbody-light");
            $(this).addClass("tbody-dark");
        } else if ($(this).hasClass("tbody-dark")) {
            $(this).removeClass("tbody-dark");
            $(this).addClass("tbody-light");
        }
  });
  $(".thead").each(function () {
        if ($(this).hasClass("thead-light")) {
            $(this).removeClass("thead-light");
            $(this).addClass("thead-dark");
        } else if ($(this).hasClass("thead-dark")) {
            $(this).removeClass("thead-dark");
            $(this).addClass("thead-light");
        }
  });
  $(".tr").each(function () {
        if ($(this).hasClass("tr-light")) {
            $(this).removeClass("tr-light");
            $(this).addClass("tr-dark");
        } else if ($(this).hasClass("tr-dark")) {
            $(this).removeClass("tr-dark");
            $(this).addClass("tr-light");
        }
  });
  $(".td").each(function () {
        if ($(this).hasClass("td-light")) {
            $(this).removeClass("td-light");
            $(this).addClass("td-dark");
        } else if ($(this).hasClass("td-dark")) {
            $(this).removeClass("td-dark");
            $(this).addClass("td-light");
        }
  });
  $(".th").each(function () {
        if ($(this).hasClass("th-light")) {
            $(this).removeClass("th-light");
            $(this).addClass("th-dark");
        } else if ($(this).hasClass("th-dark")) {
            $(this).removeClass("th-dark");
            $(this).addClass("th-light");
        }
  });
  $(".table-condensed").each(function () {
        if ($(this).hasClass("table-condensed-light")) {
            $(this).removeClass("table-condensed-light");
            $(this).addClass("table-condensed-dark");
        } else if ($(this).hasClass("table-condensed-dark")) {
            $(this).removeClass("table-condensed-dark");
            $(this).addClass("table-condensed-light");
        }
  });
  $(".table-responsive").each(function () {
        if ($(this).hasClass("table-responsive-light")) {
            $(this).removeClass("table-responsive-light");
            $(this).addClass("table-responsive-dark");
        } else if ($(this).hasClass("table-responsive-dark")) {
            $(this).removeClass("table-responsive-dark");
            $(this).addClass("table-responsive-light");
        }
  });
  $(".table-bordered").each(function () {
        if ($(this).hasClass("table-bordered-light")) {
            $(this).removeClass("table-bordered-light");
            $(this).addClass("table-bordered-dark");
        } else if ($(this).hasClass("table-bordered-dark")) {
            $(this).removeClass("table-bordered-dark");
            $(this).addClass("table-bordered-light");
        }
  });
  $(".table-frequency").each(function () {
        if ($(this).hasClass("table-frequency-light")) {
            $(this).removeClass("table-frequency-light");
            $(this).addClass("table-frequency-dark");
        } else if ($(this).hasClass("table-frequency-dark")) {
            $(this).removeClass("table-frequency-dark");
            $(this).addClass("table-frequency-light");
        }
  });
  $(".frequency-table").each(function () {
        if ($(this).hasClass("frequency-table-light")) {
            $(this).removeClass("frequency-table-light");
            $(this).addClass("frequency-table-dark");
        } else if ($(this).hasClass("frequency-table-dark")) {
            $(this).removeClass("frequency-table-dark");
            $(this).addClass("frequency-table-light");
        }
  });
  $(".frequency-cell").each(function () {
        if ($(this).hasClass("frequency-cell-light")) {
            $(this).removeClass("frequency-cell-light");
            $(this).addClass("frequency-cell-dark");
        } else if ($(this).hasClass("frequency-cell-dark")) {
            $(this).removeClass("frequency-cell-dark");
            $(this).addClass("frequency-cell-light");
        }
  });
  $(".search-form").each(function () {
        if ($(this).hasClass("search-form-light")) {
            $(this).removeClass("search-form-light");
            $(this).addClass("search-form-dark");
        } else if ($(this).hasClass("search-form-dark")) {
            $(this).removeClass("search-form-dark");
            $(this).addClass("search-form-light");
        }
  });
  $(".span-text").each(function () {
        if ($(this).hasClass("span-text-light")) {
            $(this).removeClass("span-text-light");
            $(this).addClass("span-text-dark");
        } else if ($(this).hasClass("span-text-dark")) {
            $(this).removeClass("span-text-dark");
            $(this).addClass("span-text-light");
        }
  });
  $(".span-text").each(function () {
        if ($(this).hasClass("span-text-content-light")) {
            $(this).removeClass("span-text-content-light");
            $(this).addClass("span-text-content-dark");
        } else if ($(this).hasClass("span-text-content-dark")) {
            $(this).removeClass("span-text-content-dark");
            $(this).addClass("span-text-content-light");
        }
  });
  $(".morphtypeahead").each(function () {
        if ($(this).hasClass("morphtypeahead-light")) {
            $(this).removeClass("morphtypeahead-light");
            $(this).addClass("morphtypeahead-dark");
        } else if ($(this).hasClass("morphtypeahead-dark")) {
            $(this).removeClass("morphtypeahead-dark");
            $(this).addClass("morphtypeahead-light");
        }
  });
  $(".handshapetypeahead").each(function () {
        if ($(this).hasClass("handshapetypeahead-light")) {
            $(this).removeClass("handshapetypeahead-light");
            $(this).addClass("handshapetypeahead-dark");
        } else if ($(this).hasClass("handshapetypeahead-dark")) {
            $(this).removeClass("handshapetypeahead-dark");
            $(this).addClass("handshapetypeahead-light");
        }
  });
  $(".usertypeahead").each(function () {
        if ($(this).hasClass("usertypeahead-light")) {
            $(this).removeClass("usertypeahead-light");
            $(this).addClass("morphtypeahead-dark");
        } else if ($(this).hasClass("usertypeahead-dark")) {
            $(this).removeClass("usertypeahead-dark");
            $(this).addClass("usertypeahead-light");
        }
  });
  $(".lemmatypeahead").each(function () {
        if ($(this).hasClass("lemmatypeahead-light")) {
            $(this).removeClass("lemmatypeahead-light");
            $(this).addClass("lemmatypeahead-dark");
        } else if ($(this).hasClass("lemmatypeahead-dark")) {
            $(this).removeClass("lemmatypeahead-dark");
            $(this).addClass("lemmatypeahead-light");
        }
  });
  $(".pages-form").each(function () {
        if ($(this).hasClass("pages-form-light")) {
            $(this).removeClass("pages-form-light");
            $(this).addClass("pages-form-dark");
        } else if ($(this).hasClass("pages-form-dark")) {
            $(this).removeClass("pages-form-dark");
            $(this).addClass("pages-form-light");
        }
  });
  $(".form-group").each(function () {
        if ($(this).hasClass("form-group-light")) {
            $(this).removeClass("form-group-light");
            $(this).addClass("form-group-dark");
        } else if ($(this).hasClass("form-group-dark")) {
            $(this).removeClass("form-group-dark");
            $(this).addClass("form-group-light");
        }
  });
  $(".form-control").each(function () {
        if ($(this).hasClass("form-control-light")) {
            $(this).removeClass("form-control-light");
            $(this).addClass("form-control-dark");
        } else if ($(this).hasClass("form-control-dark")) {
            $(this).removeClass("form-control-dark");
            $(this).addClass("form-control-light");
        }
  });
   $(".btn-group").each(function () {
        if ($(this).hasClass("btn-group-light")) {
            $(this).removeClass("btn-group-light");
            $(this).addClass("btn-group-dark");
        } else if ($(this).hasClass("btn-group-dark")) {
            $(this).removeClass("btn-group-dark");
            $(this).addClass("btn-group-light");
        }
  });
  $(".view-tabs").each(function () {
        if ($(this).hasClass("view-tabs-light")) {
            $(this).removeClass("view-tabs-light");
            $(this).addClass("view-tabs-dark");
        } else if ($(this).hasClass("view-tabs-dark")) {
            $(this).removeClass("view-tabs-dark");
            $(this).addClass("view-tabs-light");
        }
  });
  $(".nav-tabs").each(function () {
        if ($(this).hasClass("nav-tabs-light")) {
            $(this).removeClass("nav-tabs-light");
            $(this).addClass("nav-tabs-dark");
        } else if ($(this).hasClass("nav-tabs-dark")) {
            $(this).removeClass("nav-tabs-dark");
            $(this).addClass("nav-tabs-light");
        }
  });
  $(".query-toggles").each(function () {
        if ($(this).hasClass("query-toggles-light")) {
            $(this).removeClass("query-toggles-light");
            $(this).addClass("query-toggles-dark");
        } else if ($(this).hasClass("query-toggles-dark")) {
            $(this).removeClass("query-toggles-dark");
            $(this).addClass("query-toggles-light");
        }
  });
  $(".preview").each(function () {
        if ($(this).hasClass("preview-light")) {
            $(this).removeClass("preview-light");
            $(this).addClass("preview-dark");
        } else if ($(this).hasClass("preview-dark")) {
            $(this).removeClass("preview-dark");
            $(this).addClass("preview-light");
        }
  });
  $(".color-form").each(function () {
        if ($(this).hasClass("color-form-light")) {
            $(this).removeClass("color-form-light");
            $(this).addClass("color-form-dark");
        } else if ($(this).hasClass("color-form-dark")) {
            $(this).removeClass("color-form-dark");
            $(this).addClass("color-form-light");
        }
  });
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
