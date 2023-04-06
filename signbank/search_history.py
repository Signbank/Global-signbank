from signbank.dictionary.models import *
from signbank.dictionary.forms import *
from django.shortcuts import get_object_or_404
from signbank.dictionary.field_choices import fields_to_fieldcategory_dict


def get_multiselect_fields():
    fields_with_choices = fields_to_fieldcategory_dict()
    fields_with_choices['definitionRole'] = 'NoteType'
    fields_with_choices['hasComponentOfType'] = 'MorphologyType'
    return fields_with_choices.keys()


def available_query_parameters_in_search_history():
    available_parameters = []
    available_subclasses = QueryParameter.__subclasses__()
    for classmodel in available_subclasses:
        if hasattr(classmodel, 'QUERY_FIELDS'):
            available_parameters = available_parameters + classmodel.QUERY_FIELDS
    parameters = [t1 for (t1, t2) in available_parameters]
    # now make the fields match the format of query parameters by adding [] to multiselect fields
    multiselect_fields = get_multiselect_fields()
    fields_as_query_parameter = []
    for p in parameters:
        if p in multiselect_fields:
            fields_as_query_parameter.append(p + '[]')
        elif p in ['glosssearch', 'lemma', 'keyword']:
            for language in Language.objects.all():
                language_field = p + '_' + language.language_code_2char
                fields_as_query_parameter.append(language_field)
        else:
            fields_as_query_parameter.append(p)
    return fields_as_query_parameter


def languages_in_query(queryid):
    query = get_object_or_404(SearchHistory, id=queryid)
    multiparameters_of_query = QueryParameterMultilingual.objects.filter(search_history=query)
    languages = multiparameters_of_query.values('fieldLanguage')
    languageids = [lang['fieldLanguage'] for lang in languages]
    language_objects = Language.objects.filter(id__in=languageids).distinct()
    return language_objects


def display_parameters(query):
    # this method displays the parameters as a string, using ** to separate each
    # for the multi-select fields the choices are shown together

    if not isinstance(query, SearchHistory):
        return ""

    parameter_dict = dict()
    # for the language search fields, this dictionary is used to group them together
    # so searches on annotation or lemma or keyword fields appear next to each other
    # this groups them by language
    parameters_multilingual_dict = dict()
    for translation in query.parameters.all():
        if translation.is_fieldchoice():
            field_choice = translation.queryparameterfieldchoice
            field_name = field_choice.display_verbose_fieldname()
            if field_name not in parameter_dict.keys():
                parameter_dict[field_name] = []
            parameter_dict[field_name].append(field_choice.fieldValue.name)
        elif translation.is_handshape():
            handshape = translation.queryparameterhandshape
            field_name = handshape.display_verbose_fieldname()
            if field_name not in parameter_dict.keys():
                parameter_dict[field_name] = []
            parameter_dict[field_name].append(handshape.fieldValue.name)
        elif translation.is_semanticfield():
            semanticfield = translation.queryparametersemanticfield
            field_name = semanticfield.display_verbose_fieldname()
            if field_name not in parameter_dict.keys():
                parameter_dict[field_name] = []
            parameter_dict[field_name].append(semanticfield.fieldValue.name)
        elif translation.is_derivationhistory():
            derivationhistory = translation.queryparameterderivationhistory
            field_name = derivationhistory.display_verbose_fieldname()
            if field_name not in parameter_dict.keys():
                parameter_dict[field_name] = []
            parameter_dict[field_name].append(derivationhistory.fieldValue.name)
        elif translation.is_boolean():
            nullbooleanfield = translation.queryparameterboolean
            field_name = nullbooleanfield.display_verbose_fieldname()
            if field_name not in parameter_dict.keys():
                parameter_dict[field_name] = []
            parameter_dict[field_name].append(str(nullbooleanfield.fieldValue))
        elif translation.is_multilingual():
            multilingual = translation.queryparametermultilingual
            field_name = multilingual.fieldName
            field_name_verbose = multilingual.display_verbose_fieldname()
            if field_name == 'tags':
                display_tag = multilingual.fieldValue.replace("_", " ")
                if field_name_verbose not in parameter_dict.keys():
                    parameter_dict[field_name_verbose] = [display_tag]
                else:
                    parameter_dict[field_name_verbose].append(display_tag)
            elif field_name in ['definitionContains', 'createdBy', 'translation', 'search']:
                parameter_dict[field_name_verbose] = [multilingual.fieldValue]
            else:
                if field_name not in parameters_multilingual_dict.keys():
                    parameters_multilingual_dict[field_name] = dict()
                if field_name_verbose not in parameters_multilingual_dict[field_name].keys():
                    parameters_multilingual_dict[field_name][field_name_verbose] = []
                parameters_multilingual_dict[field_name][field_name_verbose].append(multilingual.fieldValue)
        else:
            pass
    # now add the grouped language search fields
    for search_field in parameters_multilingual_dict.keys():
        for verbose_field in parameters_multilingual_dict[search_field].keys():
            parameter_dict[verbose_field] = parameters_multilingual_dict[search_field][verbose_field]

    parameters_string = " ** ".join(key + ": " + ", ".join(values) for (key, values) in parameter_dict.items())
    return parameters_string


def get_query_parameters(query):
    # this method converts the search parameters to match the format of the query parameters in the session
    search_history_parameters = dict()

    if not isinstance(query, SearchHistory):
        return search_history_parameters

    sh_parameters = query.parameters.all()
    for shp in sh_parameters:
        if shp.is_fieldchoice():
            field_choice = shp.queryparameterfieldchoice
            field_name = field_choice.fieldName + '[]'
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            field_machine_value = field_choice.fieldValue.machine_value if field_choice.fieldValue else 0
            search_history_parameters[field_name].append(str(field_machine_value))
        elif shp.is_handshape():
            handshape = shp.queryparameterhandshape
            field_name = handshape.fieldName + '[]'
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            field_machine_value = handshape.fieldValue.machine_value if handshape.fieldValue else 0
            search_history_parameters[field_name].append(str(field_machine_value))
        elif shp.is_semanticfield():
            semanticfield = shp.queryparametersemanticfield
            field_name = semanticfield.fieldName + '[]'
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            field_machine_value = semanticfield.fieldValue.machine_value if semanticfield.fieldValue else 0
            search_history_parameters[field_name].append(str(field_machine_value))
        elif shp.is_derivationhistory():
            derivationhistory = shp.queryparameterderivationhistory
            field_name = derivationhistory.fieldName + '[]'
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            field_machine_value = derivationhistory.fieldValue.machine_value if derivationhistory.fieldValue else 0
            search_history_parameters[field_name].append(str(field_machine_value))
        elif shp.is_boolean():
            nullbooleanfield = shp.queryparameterboolean
            field_name = nullbooleanfield.fieldName
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            NEUTRALBOOLEANCHOICES = {'None': '1', 'True': '2', 'False': '3'}
            YESNOCHOICES = {'None': 'unspecified', 'True': 'yes', 'False': 'no'}
            RELATIONCHOICES = {'None': '0', 'True': '1', 'False': '2'}
            if field_name == 'defspublished':
                field_value = YESNOCHOICES[str(nullbooleanfield.fieldValue)]
            elif field_name == 'hasRelationToForeignSign':
                field_value = RELATIONCHOICES[str(nullbooleanfield.fieldValue)]
            else:
                field_value = NEUTRALBOOLEANCHOICES[str(nullbooleanfield.fieldValue)]
            search_history_parameters[field_name] = field_value
        elif shp.is_multilingual():
            multilingual = shp.queryparametermultilingual
            if multilingual.fieldName in ['tags', 'definitionContains', 'createdBy', 'translation', 'search']:
                field_name = multilingual.fieldName
            else:
                field_name = multilingual.fieldName + '_' + multilingual.fieldLanguage.language_code_2char
            if field_name not in search_history_parameters.keys():
                search_history_parameters[field_name] = []
            if field_name == 'tags':
                # tags are multi-select
                search_history_parameters[field_name].append(multilingual.fieldValue)
            else:
                search_history_parameters[field_name] = multilingual.fieldValue
    return search_history_parameters


def fieldnames_from_query_parameters(query_parameters):
    glosssearch = "glosssearch_"
    lemmasearch = "lemma_"
    keywordsearch = "keyword_"

    fieldnames = []
    for key in query_parameters:
        if key == 'search_type':
            continue
        elif key[-2:] == '[]':
            fieldnames.append(key[:-2])
        elif key.startswith(glosssearch) or key.startswith(lemmasearch) or key.startswith(keywordsearch):
            fieldnames.append(key[:-3])
        else:
            fieldnames.append(key)
    return fieldnames


def save_query_parameters(request, query_name, query_parameters):

    glosssearch = "glosssearch_"
    lemmasearch = "lemma_"
    keywordsearch = "keyword_"

    search_history = SearchHistory(user=request.user, queryName=query_name)
    search_history.save()
    for key in query_parameters:
        if key == 'search_type':
            continue
        elif key[-2:] == '[]':
            # multiple choice fields have a list of values
            if key[:-2] in ['domhndsh', 'subhndsh', 'final_domhndsh', 'final_subhndsh']:
                choices_for_category = Handshape.objects.filter(machine_value__in=query_parameters[key])
                for query_value in choices_for_category:
                    qp = QueryParameterHandshape(fieldName=key[:-2], fieldValue=query_value, search_history=search_history)
                    qp.save()
                    search_history.parameters.add(qp)
            elif key[:-2] in ['semField']:
                choices_for_category = SemanticField.objects.filter(machine_value__in=query_parameters[key])
                for query_value in choices_for_category:
                    qp = QueryParameterSemanticField(fieldName=key[:-2], fieldValue=query_value, search_history=search_history)
                    qp.save()
                    search_history.parameters.add(qp)
            elif key[:-2] in ['derivHist']:
                choices_for_category = DerivationHistory.objects.filter(machine_value__in=query_parameters[key])
                for query_value in choices_for_category:
                    qp = QueryParameterDerivationHistory(fieldName=key[:-2], fieldValue=query_value, search_history=search_history)
                    qp.save()
                    search_history.parameters.add(qp)
            else:
                field = key[:-2]
                if field == 'definitionRole':
                    field_category = Definition._meta.get_field('role').field_choice_category
                elif field == 'hasComponentOfType':
                    field_category = MorphologyDefinition._meta.get_field('role').field_choice_category
                else:
                    field_category = Gloss._meta.get_field(field).field_choice_category
                choices_for_category = FieldChoice.objects.filter(field__iexact=field_category, machine_value__in=query_parameters[key])
                for query_value in choices_for_category:
                    qp = QueryParameterFieldChoice(fieldName=key[:-2], fieldValue=query_value, search_history=search_history)
                    qp.save()
                    search_history.parameters.add(qp)
        elif key in ['weakdrop', 'weakprop', 'domhndsh_letter', 'domhndsh_number',
                     'subhndsh_letter', 'subhndsh_number', 'repeat', 'altern', 'inWeb', 'isNew',
                     'excludeFromEcv', 'hasvideo', 'hasothermedia', 'defspublished', 'hasRelationToForeignSign']:
            NEUTRALBOOLEANCHOICES = {'0': None, '1': None, '2': True, '3': False}
            UNKNOWNBOOLEANCHOICES = {'0': False, '2': True, '3': False}
            if key in ['weakdrop', 'weakprop']:
                query_value = NEUTRALBOOLEANCHOICES[query_parameters[key]]
            elif key in ['domhndsh_letter', 'domhndsh_number', 'subhndsh_letter', 'subhndsh_number']:
                query_value = UNKNOWNBOOLEANCHOICES[query_parameters[key]]
            elif key in ['repeat', 'altern']:
                query_value = UNKNOWNBOOLEANCHOICES[query_parameters[key]]
            elif key in ['defspublished']:
                query_value = query_parameters[key] == 'yes'
            elif key in ['hasRelationToForeignSign']:
                query_value = query_parameters[key] == '1'
            else:
                # inWeb, isNew , excludeFromEcv, hasvideo, hasothermedia
                query_value = query_parameters[key] == '2'
            qp = QueryParameterBoolean(fieldName=key, fieldValue=query_value,
                                       search_history=search_history, multiselect=False)
            qp.save()
            search_history.parameters.add(qp)
        elif key.startswith(glosssearch):
            search_field = glosssearch[:-1]
            search_value = query_parameters[key]
            language_code_2char = key[len(glosssearch):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            qp = QueryParameterMultilingual(fieldName=search_field, fieldLanguage=language,
                                            fieldValue=search_value, search_history=search_history, multiselect=False)
            qp.save()
            search_history.parameters.add(qp)
        elif key.startswith(lemmasearch):
            search_field = lemmasearch[:-1]
            search_value = query_parameters[key]
            language_code_2char = key[len(lemmasearch):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            qp = QueryParameterMultilingual(fieldName=search_field, fieldLanguage=language,
                                            fieldValue=search_value, search_history=search_history, multiselect=False)
            qp.save()
            search_history.parameters.add(qp)
        elif key.startswith(keywordsearch):
            search_field = keywordsearch[:-1]
            search_value = query_parameters[key]
            language_code_2char = key[len(keywordsearch):]
            language = Language.objects.get(language_code_2char=language_code_2char)
            qp = QueryParameterMultilingual(fieldName=search_field, fieldLanguage=language,
                                            fieldValue=search_value, search_history=search_history, multiselect=False)
            qp.save()
            search_history.parameters.add(qp)
        elif key == 'tags':
            search_field = key
            tag_values = query_parameters[key]
            language_code_2char = LANGUAGE_CODE
            language = Language.objects.get(language_code_2char=language_code_2char)
            for tag_value in tag_values:
                qp = QueryParameterMultilingual(fieldName=search_field, fieldLanguage=language,
                                                fieldValue=tag_value, search_history=search_history)
                qp.save()
                search_history.parameters.add(qp)
        elif key in ['definitionContains', 'createdBy', 'translation', 'search']:
            search_field = key
            search_value = query_parameters[key]
            language_code_2char = LANGUAGE_CODE
            language = Language.objects.get(language_code_2char=language_code_2char)
            qp = QueryParameterMultilingual(fieldName=search_field, fieldLanguage=language,
                                            fieldValue=search_value, search_history=search_history, multiselect=False)
            qp.save()
            search_history.parameters.add(qp)
        else:
            continue
    search_history.save()

