'use strict';

function load_project_submission_view(project_url)
{
    console.log('load_project_view');
    var loaded = $.Deferred();
    $.when(
        $.get(project_url)
    ).then(function(project) {
        return _get_or_register_group(project);
    }).then(function(group, project) {
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

            _initialize_project_submission_view(group, project);

            loaded.resolve();
        });
    });

    return loaded.promise();
}

function _get_or_register_group(project)
{
    console.log('_get_or_register_group');
    var group_loaded = $.Deferred();

    var url = _get_submission_group_url(project.data.id, [project.meta.username]);
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
        console.log(group);
        group_loaded.resolve(group, project);
    });

    return group_loaded.promise();
}

function _render_project_view(group, project, template, template_helpers)
{
    console.log('_render_project_view');
    var project_render_data = {
        'project': project,
        'group': group
    };
    var rendered = template.render(project_render_data, template_helpers);

    return rendered;
}

// -----------------------------------------------------------------------------

function _initialize_project_submission_view(group, project)
{
    console.log(group.included);
    _initialize_submit_widget(group, project);
    $('.submission-collapse').on('show.bs.collapse', _load_submission);
    _initialize_view_student_submissions_widget(project);
}

function _initialize_submit_widget(group, project)
{
    $('#fileupload').fileupload({
        'url': "/submissions/submission/",
        'dropZone': $('#dropzone'),
        'singleFileUploads': false,
        'done': function(event, response) {
            _on_submit_success(event, response, group.data.id);
        },
        'fail': function(event, response) {
            console.log('error')
            $('#upload-progress').empty();
            $('#fileupload .error').remove();

            var error_dict = $.parseJSON(response._response.jqXHR.responseText);
            console.log(error_dict)
            var error = $('<div class="error">');
            console.log(response);
            console.log(event);
            error.text('ERROR: ' + error_dict.errors.meta);
            $('#fileupload').append(error);
        },
        // 'always': function() {
        //     console.log('always');
        //     $('#upload-progress').empty();
        //     $('#fileupload .error').remove();
        // }
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

function _initialize_view_student_submissions_widget(project)
{
    $('#load-student-submissions-button').click(function(event){
        event.preventDefault();
        $('#student-submission-view .error').remove();
        var email = $('#requested-email').val().trim();
        if (!is_umich_email(email))
        {
            $('#requested-email').after(
                '<span class="error">Please enter a valid umich.edu email address</span>');
            return;
        }
        $.when(
            $.get(_get_submission_group_url(project.data.id, [email])),
            lazy_get_template('submission-panel-list'),
            lazy_get_template('submission-collapse-panel')
        ).done(function(group_response, panel_list_tmpl, collapse_panel_tmpl) {
            var template_context = {
                submission_collapse_panel: collapse_panel_tmpl,
                panel_id_suffix: 'student'
            };
            var rendered = panel_list_tmpl.render(
                {group: group_response[0]}, template_context);
            $('#student-submissions').html(rendered);
            $('#student-submissions .collapse').on('show.bs.collapse', _load_submission);
        }).fail(function() {
            $('#requested-email').after(
                '<span class="error">No submissions found for this student</span>');
        });
    });
    $('#requested-email').keypress(function(event) {
        if (event.which === 13) // enter key pressed
        {
            $('#load-student-submissions-button').click();
        }
    });
}

// -----------------------------------------------------------------------------

function _on_submit_success(event, response, group_id)
{
    var submission = response.result.data;
    $('#upload-progress').empty();
    $('#fileupload .error').remove();

    lazy_get_template('submission-collapse-panel').done(function(template) {
        var rendered = $.parseHTML(template.render(submission));
        $('#own-submissions #submission-list .panel').prepend(rendered);

        var collapsible = $('#submission-' + String(submission.id));
        collapsible.on('show.bs.collapse', _load_submission);
        collapsible.collapse();
    });
}

function _load_submission(event, url, render_location)
{
    if (url === undefined)
    {
        url = $('a', this).attr('href');
    }
    if (render_location === undefined)
    {
        render_location = $('.panel-body', this);
    }

    $.get(
        url
    ).then(function(submission) {
        console.log(submission)
        return _render_submission(submission, render_location)
    }).then(function(submission) {
        var status = submission.data.attributes.status;
        if (status === 'being_graded' || status === 'received' ||
            status === 'queued')
        {
            console.log('will try again a few seconds');
            setTimeout(function() {
                _load_submission(event, url, render_location);
            }, 5000);
        }
    });
}

function _render_submission(submission, render_location)
{
    var finished_rendering = $.Deferred();

    lazy_get_template('view-submission').done(function(template) {
        render_location.html(template.render(submission));
        finished_rendering.resolve(submission);
    });

    return finished_rendering.promise();
}

function _get_submission_group_url(project_id, usernames)
{
    var url = "/submission-groups/submission-group/?project_id=" + String(project_id);
    $.each(usernames, function(index, username) {
        url += '&usernames=' + username
    });
    console.log(url);
    return url;

    // + $.param(
    //     {'project_id': project_id,
    //      'usernames': usernames});
}

