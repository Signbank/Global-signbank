


var csrf_token = '{{csrf_token}}';

//Keep track of the original values of the changes made, so we can rewind it later if needed
//Keep track of the new values in order to generate hyperlinks for Handshapes
var original_values_for_changes_made = new Array();
var new_values_for_changes_made = new Array();

function toggle_preview(e) {
    var toggle_category = ".preview_" + e.value;
    $(toggle_category).toggle();
};

function update_view_and_remember_original_color(change_summary)
{
//    console.log('inside callback');
	split_values_count = change_summary.split('\t').length - 1;
	if (split_values_count > 0)
	{
        split_values = change_summary.split('\t');
//        console.log(split_values);
        category = split_values[0];
        fieldid = split_values[1];
//        console.log('field '+category+' '+fieldid);
        original_value = split_values[2];
        new_value = split_values[3];
        choice_id = split_values[4];

        id = $(this).attr('id');
        $(this).html(new_value);
        var field_choice_td_id = category + '_' + fieldid;
        var field_choice_column = document.getElementById(field_choice_td_id+'_display');
        field_choice_column.setAttribute("style", "background-color:#"+new_value+"; width:600px; vertical-align: middle;");
        var search_selected_item = 'select_items_'+category+'_'+choice_id;
//        console.log(search_selected_item);
        var field_choice_preview = document.getElementById(search_selected_item);
        field_choice_preview.style.backgroundColor = "#"+new_value;

        var this_class = field_choice_preview.getAttribute("class");
        if (this_class == "same-as-selected") {
            var search_same_as_selected = "select_selected_"+category;
//            console.log(search_same_as_selected);
            var search_selected_preview = document.getElementById(search_same_as_selected);
            search_selected_preview.style.backgroundColor = "#"+new_value;
        }
        if (new_value == '-' || new_value == ' ' || new_value == '' || new_value == 'None' || new_value == 0 )
        {
            console.log("new value is empty, new value is: ", new_value);
            $(this).parent().attr("value", original_value);
            $(this).html(original_value);
        }
    }
}

// initiallly hide the field choice category panels
$(document).ready(function(){
<!--    configure_edit();-->
    $("tr .collapse").collapse('hide');

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


    $("form[id^=update_color]").each(function() {
        var label = $(this).attr("id");
        var split_label = label.split('_');
        var category = split_label[2];
        var choice_id = split_label[3];
    <!--    console.log(category+' '+choice_id);-->
        var action_link = $(this).attr("action");
    <!--    console.log(action_link);-->
        var new_color = $(this).children('input[name="field_color"]').val();
    <!--    console.log(new_color);-->
        $(this).on('submit', function(e) {
            e.preventDefault();

            $.ajax({
                data: $(this).serialize(),
                type: 'POST',
                url: action_link,
                success: update_view_and_remember_original_color
            });
        });
    });

});

header_elt = document.getElementsByClassName("color-field-choices");
header_elt_l = header_elt.length;
for (i = 0; i < header_elt_l; i++) {
    header_color_field_choices = header_elt[i];
    second_column = header_color_field_choices.getElementsByTagName("th")[1]
<!--    console.log('found element');-->
    second_column.style.width = "400px";
}

var x, i, j, l, ll, selElmnt, a, b, c;
/* Look for any elements with the class "custom-select": */
x = document.getElementsByClassName("custom-select");
l = x.length;
for (i = 0; i < l; i++) {
  category_xi = x[i].getAttribute("id");
<!--  console.log(category_xi);-->
  selElmnt = x[i].getElementsByTagName("select")[0];
  ll = selElmnt.length;
  /* For each element, create a new DIV that will act as the selected item: */
  a = document.createElement("DIV");
  a.setAttribute("class", "select-selected");
  a.setAttribute("id", "select_selected_"+category_xi);
  a.style.width = "380px";
  a.style.overflow = "visible";
  a.innerHTML = selElmnt.options[selElmnt.selectedIndex].innerHTML;
  x[i].appendChild(a);
  /* For each element, create a new DIV that will contain the option list: */
  b = document.createElement("DIV");
  b.setAttribute("class", "select-items select-hide");
  b.style.overflow = "scroll";
  b.style.width = "392px";
<!--  console.log('scroll set');-->
  for (j = 0; j < ll; j++) {
    /* For each option in the original select element,
    create a new DIV that will act as an option item: */
    c = document.createElement("DIV");
    c.innerHTML = selElmnt.options[j].innerHTML;
    var option_j_color = selElmnt.options[j].getAttribute("id");
    var res = option_j_color.split("_");
    var j_color = '#' + res[3];
    var item_choice_id = res[2];
    c.setAttribute("id", "select_items_"+category_xi+"_"+item_choice_id);
    c.style.backgroundColor = j_color;
    c.addEventListener("click", function(e) {
        /* When an item is clicked, update the original select box,
        and the selected item: */
        var y, i, k, s, h, sl, yl;
        s = this.parentNode.parentNode.getElementsByTagName("select")[0];
        sl = s.length;
        h = this.parentNode.previousSibling;
        for (i = 0; i < sl; i++) {
          if (s.options[i].innerHTML == this.innerHTML) {
            s.selectedIndex = i;
            h.innerHTML = this.innerHTML;
            y = this.parentNode.getElementsByClassName("same-as-selected");
            var selected_color = this.style.backgroundColor;
<!--            console.log(selected_color);-->
            yl = y.length;
            for (k = 0; k < yl; k++) {
              y[k].removeAttribute("class");
            }
            this.setAttribute("class", "same-as-selected");
            this.parentNode.parentNode.getElementsByClassName("select-selected")[0].style.backgroundColor = selected_color;
            break;
          }
        }
        h.click();
    });
    b.appendChild(c);
  }
  x[i].appendChild(b);
  a.addEventListener("click", function(e) {
    /* When the select box is clicked, close any other select boxes,
    and open/close the current select box: */
    e.stopPropagation();
    closeAllSelect(this);
    this.nextSibling.classList.toggle("select-hide");
    this.classList.toggle("select-arrow-active");
  });
}

function closeAllSelect(elmnt) {
  /* A function that will close all select boxes in the document,
  except the current select box: */
  var x, y, i, xl, yl, arrNo = [];
  x = document.getElementsByClassName("select-items");
  y = document.getElementsByClassName("select-selected");
  xl = x.length;
  yl = y.length;
  for (i = 0; i < yl; i++) {
    if (elmnt == y[i]) {
      arrNo.push(i)
    } else {
      y[i].classList.remove("select-arrow-active");
    }
  }
  for (i = 0; i < xl; i++) {
    if (arrNo.indexOf(i)) {
      x[i].classList.add("select-hide");
    }
  }
}

/* If the user clicks anywhere outside the select box,
then close all select boxes: */
document.addEventListener("click", closeAllSelect);

