'use strict';

function load_project_submission_view(project_url)
{
    console.log('load_project_view');
    var loaded = $.Deferred();
    var project_ = null;
    var group_ = null;
    $.when(
        $.get(project_url)
    ).fail(function(data, status) {
        console.log('error loading project');
        loaded.reject("Error loading project", data.statusText);
    }).then(function(project) {
        project_ = project;
        return _get_or_register_group(project);
    }).fail(function(error_message, data) {
        console.log("Error getting group");
        loaded.reject(error_message, data.statusText);
    }).then(function(group) {
        group_ = group;
        return $.when(
            lazy_get_template('project-submission-view'),
            $.get(group_.urls.submissions),
            lazy_get_template('submission-panel-list'),
            lazy_get_template('submission-collapse-panel')
        )
    }).done(function(template,
                     submissions_ajax,
                     submission_panel_list_tmpl,
                     submission_collapse_panel_tmpl
                     ) {
        var template_helpers = {
            submission_panel_list: submission_panel_list_tmpl,
            submission_collapse_panel: submission_collapse_panel_tmpl
        };
        var rendered = _render_project_view(
            group_, project_, submissions_ajax[0], template, template_helpers);

        $('#main-area').html(rendered);

        _initialize_project_submission_view(group_, project_);

        // _poll_for_new_submissions(group);
        loaded.resolve();
    });

    return loaded.promise();
}

function _poll_for_new_submissions(group)
{
    console.log('_poll_for_new_submissions()');
    if (group.data.attributes.members.length === 1)
    {
        console.log('Group size of 1, no need to poll');
        return;
    }

    console.log('polling');
    var old_url = window.location.pathname;
    setTimeout(function() {
        var current_url = window.location.pathname;
        if (current_url !== old_url)
        {
            return;
        }

        $.get(
            group.data.links.self
        ).done(function (reloaded_group, status) {
            console.log(reloaded_group);
            var num_panels = $('#own-submissions #submission-list .panel-heading').length;
            console.log('num_panels' + ' ' + num_panels);
            if (reloaded_group.included.length > num_panels)
            {
                alert("A new submission has arrived.")
                $.when(
                    lazy_get_template('submission-panel-list'),
                    lazy_get_template('submission-collapse-panel')
                ).done(function(list_tmpl, panel_tmpl) {
                    var render_data = {'group': reloaded_group};
                    console.log(render_data);
                    var rendered = list_tmpl.render(
                        render_data, {submission_collapse_panel: panel_tmpl});
                    $('#own-submissions').html(rendered);

                    $('.submission-collapse').on('show.bs.collapse', _load_submission);
                });
            }

            _poll_for_new_submissions(reloaded_group);
        });
    }, 10000);
}

function _get_or_register_group(project)
{
    console.log('_get_or_register_group');
    console.log(project);
    var group_loaded = $.Deferred();

    // var url = _get_submission_group_url(project.data.id, [project.meta.username]);
    // $.ajax(url,
    // {
    //     statusCode: {
    //         404: function() {
    //             console.log('needs to register');
    //             var group_registered = register_group(project);
    //             group_registered.done(function(group) {
    //                 console.log('resolving');
    //                 group_loaded.resolve(group, project);
    //             });
    //         }
    //     }
    // }).
    $.get(
        project.urls.submission_groups
    ).then(function(groups_json) {
        console.log(groups_json);
        if (groups_json.user_submission_group === null)
        {
            return register_group(project);
        }
        return $.Deferred().resolve(groups_json.user_submission_group);
    }).then(function(group_url_json){
        console.log(group_url_json);
        console.log(group_url_json.url);
        return $.get(group_url_json.url);
    }).then(function(group_json){
        console.log('group loaded');
        // console.log(group_json);
        group_loaded.resolve(group_json, project);
    }).fail(function(data, status_text) {
        console.log('group load error!');
        console.log(data);
        group_loaded.reject("Error loading group", data);
    });

    return group_loaded.promise();
}

function _render_project_view(group, project, submissions, template, template_helpers)
{
    console.log('_render_project_view');
    console.log(submissions);
    var project_render_data = {
        'project': project,
        'group': group,
        'submissions': submissions
    };
    var rendered = template.render(project_render_data, template_helpers);

    return rendered;
}

// -----------------------------------------------------------------------------

function _initialize_project_submission_view(group, project)
{
    // console.log(group.included);
    _initialize_submit_widget(group, project);
    // $('.submission-collapse').on('show.bs.collapse', _load_submission);
    _initialize_view_student_submissions_widget(project);
}

function _initialize_submit_widget(group, project)
{
    var uploaded_files = [];
    $('#fileupload').fileupload({
        url: group.urls.submissions,
        maxFileSize: 10000000, // 10MB
        dropZone: $('#dropzone'),
        singleFileUploads: false,
        add: function(event, data) {
            $.each(data.files, function(index, file) {
                uploaded_files.push(file);
                $('#upload-table .files').append(
                    '<tr class="template-upload">' +
                        '<td>' +
                            '<span class="preview"></span>' +
                        '</td>' +
                        '<td>' +
                            '<p class="name">' + file.name + '</p>' +
                            '<strong class="error text-danger"></strong>' +
                        '</td>' +
                    '</tr>'
                );
                console.log(uploaded_files);
            });
        },
        done: function(event, response) {
            _on_submit_success(event, response);
        },
        fail: function(event, response) {
            console.log('error')
            console.log(response);
            $('#upload-progress').empty();
            $('#fileupload .error').remove();

            // var error_dict = $.parseJSON(response._response.jqXHR.responseText);
            // console.log(error_dict)
            var error = $('<div class="error">');
            console.log(event);
            error.text('ERROR: ' + response._response.jqXHR.responseText);
            $('#fileupload').append(error);
        },
    });

    $('#submit-button').click(function(event) {
        console.log('form submit');
        event.preventDefault();
        console.log(uploaded_files);
        if (uploaded_files.length === 0)
        {
            return false;
        }

        console.log('sending...');
        $('#fileupload').fileupload('send', {files: uploaded_files});
        console.log('clearing upload list');
        uploaded_files = [];
        console.log(uploaded_files);
    });

    $('#clear-files-button').click(function(event) {
        event.preventDefault();
        uploaded_files = [];
        $('#upload-table .files').empty();
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
        } while (node !== null);
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

        $.get(
            project.urls.submission_groups, {'group_contains': email}
        ).then(function(group_query_json) {
            console.log(group_query_json);
            return $.get(group_query_json.submission_groups[0].url);
        }).then(function(group_json) {
            return $.get(group_json.urls.submissions);   
        }).done(function(submissions_json) {
            $('#student-submissions').empty();
            $.each(submissions_json.submissions, function(index, value) {
                $('#student-submissions').append(
                    $('<div><a href="/submission' + value.url + '" data-role="ajax">' +
                      to_local_date(value.timestamp) + '</a></div>')
                );
            });
        //     return $.when(


        //         $.get(_get_submission_group_url(project.id, [email])),
        //         lazy_get_template('submission-panel-list'),
        //         lazy_get_template('submission-collapse-panel')
        // }
        // ).done(function(group_response, panel_list_tmpl, collapse_panel_tmpl) {
        //     var template_context = {
        //         submission_collapse_panel: collapse_panel_tmpl,
        //         panel_id_suffix: 'student'
        //     };
        //     var rendered = panel_list_tmpl.render(
        //         {group: group_response[0]}, template_context);
        //     $('#student-submissions').html(rendered);
        //     $('#student-submissions .collapse').on('show.bs.collapse', _load_submission);
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
    console.log('_on_submit_success');
    console.log(response);
    var submission = response.result;
    console.log(submission);
    $('#upload-progress').empty();
    $('#fileupload .error').remove();

    var link = $('<div><a href=/submission' + submission.url + ' data-role="ajax">' + to_local_date(submission.timestamp) + '</a></div>')
    $('#own-submissions').prepend(link);

    // lazy_get_template('submission-collapse-panel').done(function(template) {
    //     var rendered = $.parseHTML(template.render(submission));
    //     $('#own-submissions #submission-list .panel').prepend(rendered);

    //     var collapsible = $('#submission-' + String(submission.id));
    //     collapsible.on('show.bs.collapse', _load_submission);
    //     collapsible.collapse();
    // });
}

// function _load_submission(event, url, render_location)
// {
//     console.log(url);
//     if (url === undefined)
//     {
//         url = $('a', this).attr('href');
//     }
//     if (render_location === undefined)
//     {
//         render_location = $('.panel-body', this);
//     }

//     $.get(
//         url
//     ).then(function(submission) {
//         console.log(submission);
//         return _render_submission(submission, render_location)
//     }).then(function(submission) {
//         var status = submission.status;
//         if (status === 'being_graded' || status === 'received' ||
//             status === 'queued')
//         {
//             var old_url = window.location.pathname;
//             console.log('will try again a few seconds');
//             setTimeout(function() {
//                 var current_url = window.location.pathname;
//                 if (current_url === old_url)
//                 {
//                     _load_submission(event, url, render_location);
//                 }
//             }, 5000);
//         }
//     });
// }

// function _render_submission(submission, render_location)
// {
//     var finished_rendering = $.Deferred();

//     lazy_get_template('view-submission').done(function(template) {
//         render_location.html(template.render(submission));
//         finished_rendering.resolve(submission);
//     });

//     return finished_rendering.promise();
// }

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

