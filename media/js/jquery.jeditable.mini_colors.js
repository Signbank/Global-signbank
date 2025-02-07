
(function ($) {
	$.fn.editable = function (target, options) {
		if ('disable' == target) {
			$(this).data('disabled.editable', true);
			return;
		}
		if ('enable' == target) {
			$(this).data('disabled.editable', false);
			return;
		}
		if ('destroy' == target) {
			$(this).unbind($(this).data('event.editable')).removeData('disabled.editable').removeData('event.editable');
			return;
		}
		var settings = $.extend({
		},
		$.fn.editable.defaults, {
			target: target
		},
		options);
		var plugin = $.editable.types[settings.type].plugin || function () {
		};
		var submit = $.editable.types[settings.type].submit || function () {
		};
		var buttons = $.editable.types[settings.type].buttons || $.editable.types[ 'defaults'].buttons;
		var content = $.editable.types[settings.type].content || $.editable.types[ 'defaults'].content;
		var element = $.editable.types[settings.type].element || $.editable.types[ 'defaults'].element;
		var reset = $.editable.types[settings.type].reset || $.editable.types[ 'defaults'].reset;
		var callback = settings.callback || function () {
		};
		var onedit = settings.onedit || function () {
		};
		var onsubmit = settings.onsubmit || function () {
		};
		var onreset = settings.onreset || function () {
		};
		var onerror = settings.onerror || reset;
		if (settings.tooltip) {
			$(this).attr('title', settings.tooltip);
		}
		settings.autowidth = 'auto' == settings.width;
		settings.autoheight = 'auto' == settings.height;
		return this.each(function () {
			var self = this;
			var savedwidth = $(self).width();
			var savedheight = $(self).height();
			$(this).data('event.editable', settings.event);
			if (! $.trim($(this).html())) {
				$(this).html(settings.placeholder);
			}
			$(this).bind(settings.event, function (e) {
				if (true === $(this).data('disabled.editable')) {
					return;
				}
				if (self.editing) {
					return;
				}
				if (false === onedit.apply(this,[settings, self])) {
					return;
				}
				hide_other_forms(this.id);
				e.preventDefault();
				e.stopPropagation();
				if (settings.tooltip) {
					$(self).removeAttr('title');
				}
				if (0 == $(self).width()) {
					settings.width = savedwidth; settings.height = savedheight;
				} else {
					if (settings.width != 'none') {
						settings.width = settings.autowidth ? $(self).width(): settings.width;
					}
					if (settings.height != 'none') {
						settings.height = settings.autoheight ? $(self).height(): settings.height;
					}
				}
				if ($(this).html().toLowerCase().replace(/(;|")/g, '') == settings.placeholder.toLowerCase().replace(/(;|")/g, '')) {
					$(this).html('');
				}
				self.editing = true; self.revert = $(self).html();
				$(self).html('');
				var form = $('<form />');
				if (settings.cssclass) {
					if ('inherit' == settings.cssclass) {
						form.attr('class', $(self).attr('class'));
					} else {
						form.attr('class', settings.cssclass);
					}
				}
				if (settings.style) {
					if ('inherit' == settings.style) {
						form.attr('style', $(self).attr('style'));
						form.css('display', $(self).css('display'));
					} else {
						form.attr('style', settings.style);
					}
				}
				var input = element.apply(form,[settings, self]);
				var input_content; if (settings.loadurl) {
					var t = setTimeout(function () {
						input.disabled = true; content.apply(form,[settings.loadtext, settings, self]);
					},
					100);
					var loaddata = {
					};
					loaddata[settings.id] = self.id;
					if ($.isFunction(settings.loaddata)) {
						$.extend(loaddata, settings.loaddata.apply(self,[self.revert, settings]));
					} else {
						$.extend(loaddata, settings.loaddata);
					}
					$.ajax({
						type: settings.loadtype, url: settings.loadurl, data: loaddata, async: false, success: function (result) {
							window.clearTimeout(t);
							input_content = result; input.disabled = false;
						}
					});
				} else if (settings.data) {
					input_content = settings.data; if ($.isFunction(settings.data)) {
						input_content = settings.data.apply(self,[self.revert, settings]);
					}
				} else {
					input_content = self.revert;
				}
				content.apply(form,[input_content, settings, self]);
				input.attr('name', settings.name);
				buttons.apply(form,[settings, self]);
				$(self).append(form);
				plugin.apply(form,[settings, self]);
				$(':input:visible:enabled:first', form).focus();
				if (settings.select) {
					input.select();
				}
				input.keydown(function (e) {
					if (e.keyCode == 27) {
						e.preventDefault();
						reset.apply(form,[settings, self]);
					}
				});
				var t; if ('cancel' == settings.onblur) {
					input.blur(function (e) {
						t = setTimeout(function () {
							reset.apply(form,[settings, self]);
						},
						500);
					});
				} else if ('submit' == settings.onblur) {
					input.blur(function (e) {
						t = setTimeout(function () {
							form.submit();
						},
						200);
					});
				} else if ($.isFunction(settings.onblur)) {
					input.blur(function (e) {
						settings.onblur.apply(self,[input.val(), settings]);
					});
				} else {
					input.blur(function (e) {
					});
				}
				form.submit(function (e) {
					if (t) {
						clearTimeout(t);
					}
					e.preventDefault();
					if (false !== onsubmit.apply(form,[settings, self])) {
						if (false !== submit.apply(form,[settings, self])) {
							if ($.isFunction(settings.target)) {
								var str = settings.target.apply(self,[input.val(), settings]);
								$(self).html(str);
								self.editing = false; callback.apply(self,[self.innerHTML, settings]);
								if (! $.trim($(self).html())) {
									$(self).html(settings.placeholder);
								}
							} else {
								var submitdata = {
								};
								submitdata[settings.name] = input.val();
								submitdata[settings.id] = self.id;
								if ($.isFunction(settings.submitdata)) {
									$.extend(submitdata, settings.submitdata.apply(self,[self.revert, settings]));
								} else {
									$.extend(submitdata, settings.submitdata);
								}
								if (settings.type == 'text' || settings.type == 'checkbox') {
								    submitdata[settings.name] = input.val();
								}
								if ('PUT' == settings.method) {
									submitdata[ '_method'] = 'put';
								}
								$(self).html(settings.indicator);
								var ajaxoptions = {
									type: 'POST', data: submitdata, datatype: 'text', url: settings.target, success: function (result, status) {
										if (ajaxoptions.datatype == 'text') {
											$(self).html(result);
										}
										self.editing = false; callback.apply(self,[result, settings]);
										if (! $.trim($(self).html())) {
											$(self).html(settings.placeholder);
										}
									},
									error: function (xhr, status, error) {
										onerror.apply(form,[settings, self, xhr]);
									}
								};
								var this_val = $('#' + settings.params.field).attr('value');
								if (settings.type == 'text') {
									$.extend(settings.submitdata, {
										"value": input.val()
									});
								};
								$.extend(ajaxoptions, settings.ajaxoptions);
								$.ajax(ajaxoptions);
							}
						}
					}
					$(self).attr('title', settings.tooltip);
					return false;
				});
			});
			this.reset = function (form) {
				if (this.editing) {
					if (false !== onreset.apply(form,[settings, self])) {
						$(self).html(self.revert);
						self.editing = false; if (! $.trim($(self).html())) {
							$(self).html(settings.placeholder);
						}
						if (settings.tooltip) {
							$(self).attr('title', settings.tooltip);
						}
					}
				}
			};
		});
	};
	$.editable = {
		types: {
			defaults: {
				element: function (settings, original) {
					var input = $('<input type="hidden"></input>');
					$(this).append(input);
					return (input);
				},
				content: function (string, settings, original) {
					$(':input:first', this).val(string);
				},
				reset: function (settings, original) {
					original.reset(this);
				},
				buttons: function (settings, original) {
					var form = this;
                    
					var td_value = $('#' + settings.params.field).attr('value');
                    var td_value_width = (td_value === undefined) ? settings.width : td_value.length * 16;

					if (settings.submit) {
						if (settings.submit.match(/>$/)) {
							var submit = $(settings.submit).click(function () {
								if (submit.attr("type") != "submit") {
									form.submit();
								}
							});
							if (settings.type == "textarea") {
							    var submitlefttext = 0;
                                submit.css({
                                    'display': 'block', 'position': 'relative', 'left': submitlefttext
                                });
							} else if (settings.type == "multiselect" || settings.type == 'text') {
							    var submitlefttext = settings.width + 100;
                                submit.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': submitlefttext
    	                            });
								} else if (settings.type == 'select') {
                                submit.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': td_value_width+150

                                });								
							} else {
                                submit.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': settings.submitleft
                                });
                            }
						} else {
							var submit = $('<button type="submit" />');
                            submit.css({
                                'display': 'inline-block', 'position': 'absolute', 'left': settings.submitleft
                            });							
							submit.html(settings.submit);
						}
						$(this).append(submit);
					}
					if (settings.cancel) {
						if (settings.cancel.match(/>$/)) {
							var cancel = $(settings.cancel);
							if (settings.type == "textarea") {
							    var cancellefttext = 0;
                                cancel.css({
                                    'display': 'block', 'position': 'relative', 'left': cancellefttext
                                });
							} else if (settings.type == "multiselect" || settings.type == 'text') {
								var cancellefttext = settings.width;
                                cancel.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': cancellefttext
                                });
							} else if (settings.type == 'select') {
                                cancel.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': td_value_width+50									
                                });
							} else {
                                cancel.css({
                                    'display': 'inline-block', 'position': 'absolute', 'left': settings.cancelleft
                                });
                            }
						} else {
							var cancel = $('<button type="cancel" />');
                            cancel.css({
                                'display': 'inline-block', 'position': 'absolute', 'left': settings.cancelleft
                            });							
							cancel.html(settings.cancel);
						}
						$(this).append(cancel);
						$(cancel).click(function (event) {
							if ($.isFunction($.editable.types[settings.type].reset)) {
								var reset = $.editable.types[settings.type].reset;
							} else {
								var reset = $.editable.types[ 'defaults'].reset;
							}
							reset.apply(form,[settings, original]);
							return false;
						});
					}
				}
			},
			text: {
				element: function (settings, original) {
					var input = $('<input />');
					if (settings.width != 'none') {
						input.width(settings.width);
					}
					if (settings.height != 'none') {
						input.height(settings.height);
					}
					input.attr('autocomplete', 'off');
					input.css({
                                'display': 'inline-block', 'position': 'relative', 'width': '420px'
                    });
					$(this).append(input);
					return (input);
				}
			},
			textarea: {
				element: function (settings, original) {
					var textarea = $('<textarea />');
					if (settings.rows) {
						textarea.attr('rows', settings.rows);
					} else if (settings.height != "none") {
					    var notestextarea = settings.height;
					    if (settings.height > 20) {
					        // more than one row for this field
					        notestextarea = notestextarea * 2;
					    }
						textarea.height(notestextarea);
					}
					if (settings.cols) {
						textarea.attr('cols', settings.cols);
					} else if (settings.width != "none") {
						textarea.width(settings.width);
					}
					$(this).append(textarea);
					return (textarea);
				}
			},
			select: {
				element: function (settings, original) {
                    var dropdown_button = $('<button />');
                    dropdown_button.attr('id', 'preview_' + settings.params.field);
                    dropdown_button.attr('class', 'btn dropdown-toggle');
                    dropdown_button.attr('type', 'button');
                    dropdown_button.attr('data-toggle', 'dropdown');
                    dropdown_button.attr('aria-haspopup', 'true');
                    dropdown_button.attr('aria-expanded', 'false');
                    dropdown_button.css({
                        'display': 'inline-block', 'width': 'auto', 'color': 'red', 'position': 'relative', 'z-index': 0, 'left': '0px'
                    });
                    var td_value = $('#' + settings.params.field).attr('value');
                    var row_class = $('#' + settings.params.field).parent().attr('class');
                    if (settings.params.field == 'weakdrop' || settings.params.field == 'weakprop') {
                        if (td_value == 'None' || td_value == 'True' || td_value == 'False') {
                            // get translated display value
                            td_value = handedness_weak_choices[td_value];
                        }
                    };
                    if (row_class != 'empty_row' && td_value != 'None') {
                        dropdown_button.html(td_value);
                    } else {
                        dropdown_button.html('------');
                    };
                    $(this).append(dropdown_button);
					var select = $('<ul />');
					select.attr('class', 'dropdown-menu shadow-sm p-3 mb-5 bg-white rounded');
					select.attr('id', 'ul_' + settings.params.field);
					if (settings.params.field == 'weakdrop' || settings.params.field == 'weakprop') {
					    select.css({'overflow-y': 'scroll', 'list-style-type': 'none',
					        'max-height': '200px', 'position': 'absolute', 'min-width': '80px'
					    });
					} else {
					    select.css({'overflow-y': 'scroll', 'list-style-type': 'none',
					        'max-height': '200px', 'position': 'absolute', 'z-index': 10
					    });
					};
					select.attr('role', 'listbox');
					$(this).append(select);
					return (select);
				},
				content: function (data, settings, original) {
					if (String == data.constructor) {
						eval('var json = ' + data);
					} else {
						var json = data;
					}
					for (var key in json) {
						if (! json.hasOwnProperty(key)) {
							continue;
						}
						if ('selected' == key) {
							continue;
						}
						var key_color = (settings.params === undefined) ? 'fffff': settings.params.colors[key];
						var option = $('<li />');
						option.attr('value', key);
						option.attr('name',json[key]);
						option.attr('id',json[key]);
						option.append(json[key]);
						option.attr('class', 'dropdown-item');
						option.attr('data-value', key);
						option.css({
							'color': 'black', 'background-color': '#' + key_color
						});;
						$('ul', this).append(option);
					};
					var chosen_offset = 0;
					$('ul', this).children().each(function (index) {
						var indie = (settings.params === undefined) ? -1: settings.params.a;
						if ($(this).data('value') == indie || $(this).text() == $.trim(original.revert)) {
							$.extend(settings.submitdata, {
								"value": settings.params.a
							});
							$(this).attr('class', 'dropdown-item active');
							chosen_offset = index*20;
						} else {
							var this_val = $(this).data('value');
							$(this).click(function () {
								$('#' + settings.params.field).attr("value", settings.params.choices[this_val]);
								$('#preview_' + settings.params.field).html(settings.params.choices[this_val]);
								$(this).siblings().each(function () {
									$(this).attr('class', 'dropdown-item')
								});; $(this).attr('class', 'dropdown-item active');
								$.extend(settings.submitdata, {
									"value": this_val
								});
							});
						}
					});
					$(this).keypress(function(e){
					    var touched = String.fromCharCode(e.charCode);
					    touched = touched.toUpperCase();
					    var this_ul = '#ul_' + settings.params.field;
                        var this_li = $(this_ul).find('li[id^="'+touched+'"]')[0];
                        var scroller = 0;
                        if (this_li) {
                            scroller = this_li.offsetTop;
                        };
                        $('.dropdown-menu').animate({
                            scrollTop: scroller
                        }, 1000);
					});
					$(this).click(function(){
                        scroller = chosen_offset;
                        $('.dropdown-menu').animate({
                            scrollTop: scroller
                        }, 1000);
					});
				}
			}
		},
		addInputType: function (name, input) {
			$.editable.types[name] = input;
		}
	};
	$.fn.editable.defaults = {
		name: 'value', id: 'id', type: 'text', width: 'auto', height: 'auto', event: 'click.editable', onblur: 'cancel', loadtype: 'POST', loadtext: 'Loading...', placeholder: 'Click to edit', loaddata: {
		},
		submitdata: {
		},
		ajaxoptions: {
		}
	};
})(jQuery);