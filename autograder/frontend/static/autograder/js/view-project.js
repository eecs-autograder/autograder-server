'use strict';

function load_project_submission_view(project_url)
{
    console.log('load_project_view');
    var loaded = $.Deferred();
    // console.log(project_url);
    // var project_loaded = ;
    $.when(
        $.get(project_url)
    ).then(function(project) {
        return _get_or_register_group(project);
    }).then(function(group, project) {
        console.log('wheee');
        console.log(group);
        console.log(project);

        $.when(
            lazy_get_template('project-submission-view'),
            lazy_get_template('submission-panel-list'),
            lazy_get_template('submission-collapse-panel')
        ).done(function(template,
                        submission_panel_list_tmpl,
                        submission_collapse_panel_tmpl) {
            var template_helpers = {
                submission_panel_list: submission_panel_list_tmpl,
                submission_collapse_panel: submission_collapse_panel_tmpl
            };
            var rendered = _render_project_view(
                group, project, template, template_helpers);

            $('#main-area').html(rendered);

            _initialize_project_submission_view()

            loaded.resolve();
        });
    });

    return loaded.promise();
}

function _get_or_register_group(project)
{
    console.log('_get_or_register_group');
    console.log(project);
    var group_loaded = $.Deferred();

    var url = get_submission_group_url(project.data.id, project.meta.username);
    $.ajax(url,
    {
        statusCode: {
            404: function() {
                console.log('needs to register');
                var group_registered = register_group(project);
                group_registered.done(function(group) {
                    console.log('resolving');
                    group_loaded.resolve(group, project);
                });
            }
        }
    }).done(function(group) {
        console.log('group loaded');
        group_loaded.resolve(group, project);
    });

    console.log('returning promise');
    return group_loaded.promise();
}

function _render_project_view(group, project, template, template_helpers)
{
    console.log('_render_project_view');
    console.log(group);
    console.log(project);
    console.log(template_helpers);
    var project_render_data = {
        'project': project,
        'group': group
    };
    var rendered = template.render(project_render_data, template_helpers);
    console.log(rendered);

    return rendered;
}

function _initialize_project_submission_view(group, project)
{
    _initialize_submit_widget(group, project);
    setup_collapsibles($('.submission-collapse'));
    view_student_submissions_widget_init(project);
}

// -----------------------------------------------------------------------------

function _initialize_submit_widget(group, project)
{
    console.log('project rendered');
    console.log($('#fileupload'));
    $('#fileupload').fileupload({
        'url': "/submissions/submission/",
        'dropZone': $('#dropzone'),
        'singleFileUploads': false,
        'done': function(event, response) {
            on_submit_success(event, response, group.data.id);
        }
    });

    $(document).bind('dragover', function (e) {
        var dropZone = $('#dropzone'),
            timeout = window.dropZoneTimeout;
        if (!timeout) {
            dropZone.addClass('in');
        } else {
            clearTimeout(timeout);
        }
        var found = false,
            node = e.target;
        do {
            if (node === dropZone[0]) {
                found = true;
                break;
            }
            node = node.parentNode;
        } while (node != null);
        if (found) {
            dropZone.addClass('hover');
        } else {
            dropZone.removeClass('hover');
        }
        window.dropZoneTimeout = setTimeout(function () {
            window.dropZoneTimeout = null;
            dropZone.removeClass('in hover');
        }, 100);
    });
}

function on_submit_success(event, response, group_id)
{
    console.log(response);
    var submission = response.result.data;
    console.log(submission);
    console.log('doneeee');

    $('#upload-progress').empty();

    // var node_id = "submission-" + String(submission.data.id) + "-" + String(group_id)

    var submission_widget = $.parseHTML(
        $.templates('#submission-collapse-panel').render(submission));

    console.log(submission_widget);

    var collapsible_context = $('<div>').append(submission_widget);
    var collapsible = $('.submission-collapse', collapsible_context);
    console.log(collapsible);
    setup_collapsibles(collapsible);

    $('#submission-list .panel').prepend(submission_widget);

    collapsible.collapse();
}

function setup_collapsibles(selector)
{
    // console.log('setting up');
    // console.log(selector);
    selector.on('show.bs.collapse', function() {
        // console.log('oiueqroiwuer');
        var url = $('a', this).attr('href');
        var context = $('.panel-body', this);
        load_submission(url, context);
    });
}

function load_submission(url, context)
{
    $.get(url).done(function(data, status) {
        // console.log(data);
        // console.log(context);
        render_and_fix_links('view-submission', data, context);
        var status = data.data.attributes.status;
        if (status === 'being_graded' || status === 'received' ||
            status === 'queued')
        {
            console.log('will try again a few seconds');
            setTimeout(function() {load_submission(url, context);}, 5000);
        }
    });
}

function view_student_submissions_widget_init(project)
{
    $('#load-student-submissions-button').click(function(event){
        event.preventDefault();
        $('#student-submission-view .error').remove();
        var email = $('#requested-email').val();
        if (!is_umich_email(email))
        {
            $('#requested-email').after(
                '<span class="error">Please enter a valid umich.edu email address</span>');
            return;
        }
        var url = get_submission_group_url(
            project.data.id, email);
        $.get(
            url
        ).done(function (data, status) {
            $.when(render_and_fix_links('submission-list', data, $('#student-submissions'))).done(
                setup_collapsibles($('#student-submissions .submission-collapse'))
            );
        });
    });
    $('#requested-email').keypress(function(event) {
        if (event.which === 13) // enter key pressed
        {
            $('#load-student-submissions-button').click();
        }
    });
}

function get_submission_group_url(project_id, username)
{
    return "/submission-groups/submission-group/?" + $.param(
        {'project_id': project_id,
         'username': username});
}

