function load_edit_ag_test_view(url)
{
    var loaded = $.Deferred();
    var ag_test_json_ = null;
    var project_json_ = null;

    $.when(
        $.get(url)
    ).then(function(ag_test_json){
        ag_test_json_ = ag_test_json;
        return $.get(ag_test_json_.urls.project);
    }).then(function(project_json) {
        project_json_ = project_json;
        return $.when(
            $.get(project_json.urls.uploaded_files),
            lazy_get_template('test_case_form')
        );
    }).done(function(project_files_ajax, template) {
        _render_ag_test_view(
            ag_test_json_, project_json_, project_files_ajax[0], template);
        loaded.resolve();
    });

    return loaded.promise();
}

function _render_ag_test_view(ag_test_json, project, project_files, template)
{
    var context = {
        populate_fields: true,
        ag_test: ag_test_json,
        project: project,
        project_files: project_files
    };
    console.log(context);

    $('#main-area').html(template.render(context));    
}

function _save_test_form_handler(e)
{
    console.log('saving');
    e.preventDefault();
    var button = $('button', this);
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

