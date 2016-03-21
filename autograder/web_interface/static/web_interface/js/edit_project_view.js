function load_edit_project_view(project_url)
{
    console.log('load_edit_project_view');

    var loaded = $.Deferred();
    var project = null;
    $.when(
        $.get(project_url)
    ).then(function(project_json) {
        project = project_json;
        return $.when(
            $.get(project.urls.autograder_test_cases),
            $.get(project.urls.uploaded_files),
            lazy_get_template('edit_project_view'),
            lazy_get_template('test_case_panel'),
            lazy_get_template('test_case_form')
        )
    }).done(function(ag_tests_ajax, project_files_ajax, project_tmpl,
                    test_panel_tmpl, test_form_tmpl) {
        _render_edit_project_view(
            project, ag_tests_ajax[0], project_files_ajax[0],
            project_tmpl, test_panel_tmpl, test_form_tmpl);
        loaded.resolve();
    });

    return loaded.promise();
}

function _render_edit_project_view(
    project, ag_tests, project_files, project_tmpl, test_panel_tmpl, test_form_tmpl)
{
    console.log(project);
    var tmpl_context = {
        project: project,
        ag_tests: ag_tests,
        project_files: project_files,
    };
    var tmpl_helpers = {
        test_case_panel: test_panel_tmpl,
        test_case_form: test_form_tmpl,
        populate_fields: true,
        in_array: in_array
    };
    $('#main-area').html(project_tmpl.render(tmpl_context, tmpl_helpers));

    // file upload set-up
    $.when(
        lazy_get_template('upload-ready-project-file'),
        lazy_get_template('download-ready-project-file')
    ).done(function(upload_tmpl, download_tmpl) {
        $('#project_file_upload').fileupload({
            url: project.urls.uploaded_files,
            uploadTemplateId: null,
            downloadTemplateId: null,
            paramName: 'files',
            uploadTemplate: function(data) {
                return upload_tmpl.render(data);
            },
            downloadTemplate: function(data) {
                console.log(data);
                return download_tmpl.render(data);
            },
            // done: function(event, response) {
            //     console.log(event);
            //     console.log(response);
            //     $('#file_list .files').append(
            //         download_tmpl.render(response.result));

            // },
            getFilesFromResponse: function(data) {
                console.log('getFilesFromResponse');
                console.log(data.result);
                if ($.isArray(data.result))
                {
                    return data.result;
                }
                return [data.result];
            }
        });

        $('#file_list .files').append(
            download_tmpl.render(project_files));

        // $.each(project.data.attributes.project_files, function(index, value) {
        //     $('#file_list .files').append(download_tmpl.render(value));
        // });
    });

    // settings set-up
    $('#datetimepicker').datetimepicker({
        defaultDate: project.closing_time
    });

    $('#add_required_file_slot_button').click(function() {
        $(this).before(
            "<input type='text' class='form-control' name='required_student_files''>"
        );
    });

    console.log('waaaaaaaa');
    $('#project_fields_form').submit(function(e) {
        _save_project_settings(e, project);
    });

    // test case edit set-up
    $('#test_cases form').each(function() {
        $(this).submit(_save_test_form_handler);
    });

    $('#test_cases .delete-test-btn').each(function() {
        $(this).click(_delete_test_button_handler);
    });

    var add_test_fields_tmpl_helpers = {
        test_case_form: test_form_tmpl,
        type_override: $('#test_type').val(),
        populate_fields: false
    };

    console.log(tmpl_context);
    var add_test_fields = $(
        test_form_tmpl.render(tmpl_context, add_test_fields_tmpl_helpers));
    $('#add_test_fields').append(add_test_fields.html());

    $('#add_test_form').submit(function(e) {
        e.preventDefault();
        var new_test = _extract_test_case_form_fields($(this));
        new_test['type'] = _extract_single_text_field($(this), 'test_type'),

        // new_test.data.relationships = {
        //     'project': project
        // };
        _add_test_case_button_handler(
            project, new_test, test_panel_tmpl, test_form_tmpl);
    });
}

function _save_test_form_handler(e)
{
    console.log('saving');
    e.preventDefault();
    var button = $('button', this)
    button.button('loading');
    var url = $(this).attr('patch_url');
    var patch_data = _extract_test_case_form_fields($(this));
    $.patchJSON(url, patch_data).done(function() {
        button.button('reset');
    }).fail(function(response) {
        console.log('error!!');
        console.log(response);
    });
}

function _add_test_case_button_handler(
    project, new_test, test_panel_tmpl, test_form_tmpl)
{
    var tmpl_helpers = {
        test_case_form: test_form_tmpl,
        populate_fields: true,
        in_array: in_array
    };

    $.postJSON(
        project.urls.autograder_test_cases, new_test
    ).done(function(test_response) {
        var new_link = $('<a href=/ag-test' + test_response.url + ' data-role="ajax"></a>');
        new_link.text(test_response.name);
        var divvy = $('<div></div>');
        divvy.html(new_link);
        $('#test_cases').append(divvy);

        // var new_test_panel = test_panel_tmpl.render(tmpl_context, tmpl_helpers);
        // $('#test_cases .panel').append(new_test_panel);
        // var forms = $('#test_cases form');
        // $(forms[forms.length - 1]).submit(_save_test_form_handler);
        // var delete_buttons = $('#test_cases .delete-test-btn');
        // $(delete_buttons[delete_buttons.length - 1]).click(
        //     _delete_test_button_handler);
        // $('#add_test_case').collapse();
    });
}

function _delete_test_button_handler()
{
    var delete_url = $(this).attr('delete_url');
    var button = $(this);
    $.ajax(delete_url, {method: 'DELETE'}).done(function() {
        var span_id = button.attr('span_id');
        var span = $('#' + span_id);
        span.remove();
    });
}

function _extract_test_case_form_fields(form)
{
    console.log(form);
    var test_case = {
        'type': _extract_single_text_field(form, 'test_type', true),
        'name': _extract_single_text_field(form, 'name', true),
        // 'hide_from_students': _extract_checkbox_bool(form, 'hide_from_students'),
        'command_line_arguments': _extract_delimited_text_field(form, 'command_line_arguments'),
        'standard_input': _extract_single_text_field(form, 'standard_input'),
        'test_resource_files': _extract_checkbox_group_vals(form, 'test_resource_files'),
        'student_resource_files': _extract_checkbox_group_vals(form, 'student_resource_files'),
        'time_limit': _extract_single_text_field(form, 'time_limit', true, null),
        'expected_return_code': _extract_single_text_field(form, 'expected_return_code', true, null),
        'expect_any_nonzero_return_code': _extract_checkbox_bool(form, 'expect_any_nonzero_return_code'),
        'expected_standard_output': _extract_single_text_field(form, 'expected_standard_output'),
        'expected_standard_error_output': _extract_single_text_field(form, 'expected_standard_error_output'),
        'use_valgrind': _extract_checkbox_bool(form, 'use_valgrind'),
        'valgrind_flags': _extract_delimited_text_field(form, 'valgrind_flags'),

        'points_for_correct_return_code': _extract_single_text_field(form, 'points_for_correct_return_code', true, 0),
        'points_for_correct_output': _extract_single_text_field(form, 'points_for_correct_output', true, 0),
        'deduction_for_valgrind_errors': _extract_single_text_field(form, 'deduction_for_valgrind_errors', true, 0),
        'points_for_compilation_success': _extract_single_text_field(form, 'points_for_compilation_success', true, 0)
    };
    if (test_case.type === 'interpreted_test_case')
    {
        test_case.interpreter = _extract_single_text_field(form, 'interpreter')
        test_case.interpreter_flags = _extract_delimited_text_field(form, 'interpreter_flags')
        test_case.entry_point_filename = _extract_single_text_field(form, 'entry_point_filename')
    }
    else
    {
        test_case.compiler = _extract_single_text_field(form, 'compiler')
        test_case.compiler_flags = _extract_delimited_text_field(form, 'compiler_flags')
        test_case.student_files_to_compile_together = _extract_checkbox_group_vals(form, 'student_files_to_compile_together')
        test_case.project_files_to_compile_together = _extract_checkbox_group_vals(form, 'project_files_to_compile_together')
        test_case.executable_name = _extract_single_text_field(form, 'executable_name')
    }
    console.log(test_case);
    return test_case;
}

function _extract_single_text_field(form, name, trim_whitespace, default_val)
{
    console.log(name);
    var selector = $(':input[name="' + name + '"]', form);
    var value = selector.val();
    if (trim_whitespace)
    {
        value = value.trim();
    }

    if (value === '' && default_val !== undefined)
    {
        return default_val;
    }

    return value;
}

function _extract_checkbox_bool(form, name)
{
    return $(':input[name="' + name + '"]', form).is(':checked');
}

function _extract_checkbox_group_vals(form, name)
{
    var selector = $(':input[name="' + name + '"]:checked', form);
    var values = [];
    selector.each(function() {
        values.push($(this).val());
    });

    return values;
}

function _extract_delimited_text_field(form, name, delimiter)
{
    if (delimiter === undefined)
    {
        delimiter = ' ';
    }

    var values = _extract_single_text_field(form, name, true).split(delimiter);
    var filtered = [];
    for (index in values)
    {
        if (values[index] !== '')
        {
            filtered.push(values[index]);
        }
    }
    return filtered;
}

function _save_project_settings(e, project)
{
    console.log(project);
    e.preventDefault();
    // var new_feedback_config = {
    //     return_code_feedback_level: $('#return_code_feedback_level').val(),
    //     output_feedback_level: $('#output_feedback_level').val(),
    //     compilation_feedback_level: $('#compilation_feedback_level').val(),
    //     valgrind_feedback_level: $('#valgrind_feedback_level').val(),
    //     points_feedback_level: $('#points_feedback_level').val()
    // };
    // project.data.attributes.test_case_feedback_configuration = new_feedback_config;

    project.visible_to_students = ($('#visible_to_students').is(':checked'));
    project.disallow_student_submissions = (
        $('#disallow_student_submissions').is(':checked'));
    project.allow_submissions_from_non_enrolled_students = (
        $('#allow_submissions_from_non_enrolled_students').is(':checked'));

    var closing_time = $('#datetimepicker').data(
        'DateTimePicker').viewDate().toISOString();
    if ($('#closing_time').val().trim() === '')
    {
        closing_time = null;
    }
    console.log(closing_time);
    project.closing_time = closing_time;
    project.min_group_size = $('#min_group_size').val().trim();
    project.max_group_size = $('#max_group_size').val().trim();

    var required_files = [];
    $(':input[name="required_student_files"]').each(function() {
        var val = $(this).val().trim();
        if (val !== '')
        {
            required_files.push(val);
        }
    });
    console.log(required_files);
    project.required_student_files = required_files;

    $.patchJSON(
        project.urls.self, project
    ).done(function() {
        console.log('save successful');
    });
}
