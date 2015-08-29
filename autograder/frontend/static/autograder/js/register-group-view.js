function process_group_registration(project_data)
{
    console.log('process_group_registration');
    var max_size = project_data.data.attributes.max_group_size
    var min_size = project_data.data.attributes.min_group_size;

    var registration_view_rendered = render_and_fix_links(
        'register-group-view', {'max_group_size': max_size});

    var deferred = $.Deferred();

    $.when(registration_view_rendered).done(function() {
        initialize_group_registration_view(
            min_size, max_size, project_data, deferred);
    });
    return deferred.promise();
}

function initialize_group_registration_view(
    min_size, max_size, project_data, deferred)
{
    console.log('initialize_group_registration_view');
    $('#register-group-button').click(function(event) {
        register_group_button_click_handler(
            event, min_size, max_size, project_data, deferred);
    });
    $('#work-alone-box').click(function() {
        if ($(this).is(':checked'))
        {
            $('#partner-list').hide();
            return;
        }
        $('#partner-list').show();
    });
}

function register_group_button_click_handler(
    event, min_size, max_size, project_data, deferred)
{
    // event.preventDefault();
    console.log('register_group_button_click_handler');
    $(".error").remove();

    var members = [get_user_email()];
    if ($('#work-alone-box').is(':checked'))
    {
        submit_group_request(members, project_data);
        return;
    }

    $('#register-group-form :text').each(function(i, field) {
        if (field.name !== 'members')
        {
            return;
        }
        var email = $.trim(field.value);
        if (email === '')
        {
            // Skip blank fields
            return;
        }

        if (!is_umich_email(email))
        {
            $(this).after('<span class="error">Please enter a "umich.edu" email address</span>');
            return;
        }
        members.push(field.value);
    });
    if (members.length > max_size)
    {
        $('#partner-list').append(
            '<div>Please enter at most ' + String(max_size - 1) +
            ' email(s)</div>');
        return;
    }
    if (members.length < min_size || members.length === 0)
    {
        $('#partner-list').append(
            '<div class="error">Please enter at least ' +
            String(min_size - 1) + ' email(s)</div>');
        return;
    }

    submit_group_request(members, project_data, deferred);
}

function submit_group_request(members, project_data, deferred)
{
    console.log('submit_group_members');
    // console.log(members);
    // console.log(project_data);
    var request_data = {
        'data': {
            'type': 'submission_group',
            'attributes': {
                'members': members,
            },
            'relationships': {
                'project': {
                    'data': {
                        'type': 'project',
                        'id': project_data.data.id
                    }
                }
            }
        }
    }

    $.postJSON(
        "/submission-groups/submission-group/", request_data
    ).done(function(group_data, status) {
        console.log('resolving');
        deferred.resolve(group_data, project_data);
    }).fail(function(data, status) {
        // console.log(data);
        var response_json = data.responseJSON;
        // console.log(data.responseJSON);
        // console.log(response_json.errors.meta);
        var error_html = '<div class="error"><div>Errors</div><ul>'
        $.each(response_json.errors.meta.members, function(i, message) {
            error_html += $('<li/>').text(message).html();
        });
        error_html += '</ul></div></div>';
        // console.log(error_html);
        $('#partner-list').after(error_html);
    });
}



