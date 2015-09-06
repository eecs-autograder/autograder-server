function load_edit_project_view(project_url)
{
    console.log('load_edit_project_view');

    var loaded = $.Deferred();

    $.when(
        $.get(project_url),
        lazy_get_template('edit_project_view'),
        lazy_get_template('test_case_panel'),
        lazy_get_template('test_case_form')
    ).done(function(project_ajax, project_tmpl,
                    test_panel_tmpl, test_form_tmpl) {
        var widget = _render_edit_project_view(
            project_ajax[0], project_tmpl, test_panel_tmpl, test_form_tmpl);
        loaded.resolve();
    });

    return loaded.promise();
}

function _render_edit_project_view(
    project, project_tmpl, test_panel_tmpl, test_form_tmpl)
{
    console.log(project);
    var tmpl_helpers = {
        test_case_panel: test_panel_tmpl,
        test_case_form: test_form_tmpl,
        populate_fields: true,
        in_array: $.inArray
    };
    $('#main-area').html(project_tmpl.render(project, tmpl_helpers));
    // $("a[data-role='ajax']").click(ajax_link_click_handler);
    $('#save-button').click(function(e) {
        _save_project_button_click_handler(e, project);
    });


    var add_test_fields_tmpl_helpers = {
        test_case_form: test_form_tmpl,
        type_override: $('#test_type').val(),
        populate_fields: false
    };

    var add_test_fields = $(
        test_form_tmpl.render(project, add_test_fields_tmpl_helpers));
    $('#add_test_fields').append(add_test_fields.html());

    $('#add_test_form').submit(function(e) {
        e.preventDefault();
        // var new_panel = test_panel_tmpl.render({} , tmpl_helpers);
    });
}

function _save_project_button_click_handler(e, project)
{
    console.log(project);
    var new_feedback_config = {
        return_code_feedback_level: $('#return_code_feedback_level').val(),
        output_feedback_level: $('#output_feedback_level').val(),
        compilation_feedback_level: $('#compilation_feedback_level').val(),
        valgrind_feedback_level: $('#valgrind_feedback_level').val(),
        points_feedback_level: $('#points_feedback_level').val()
    };
    project.data.attributes.test_case_feedback_configuration = new_feedback_config;

    project.data.attributes.visible_to_students = (
        $('#visible_to_students').is(':checked'));
    project.data.attributes.disallow_student_submissions = (
        $('#disallow_student_submissions').is(':checked'));
    project.data.attributes.allow_submissions_from_non_enrolled_students = (
        $('#allow_submissions_from_non_enrolled_students').is(':checked'));

    var closing_time = $('#closing_time').val();
    if (closing_time.trim() === '')
    {
        closing_time = null;
    }
    project.data.attributes.closing_time = closing_time;
    project.data.attributes.min_group_size = $('#min_group_size').val().trim();
    project.data.attributes.max_group_size = $('#max_group_size').val().trim();

    $.patchJSON(
        project.data.links.self, project
    ).done(function() {
        console.log('save successful');
    });
}
