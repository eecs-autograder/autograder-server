function load_submitted_file_view(resource_url)
{
	var loaded = $.Deferred();
	$.when(
		$.get(resource_url),
		lazy_get_template('view-submitted-file')
	).done(function(file_content, template) {
        var file_data = String(file_content[0]);
        console.log(file_data);
        var render_data = {
            'content': file_data
        };
        // console.log(render_data.content);
        var rendered = template.render(render_data);
        console.log(rendered);
        $('#main-area').html(rendered);

        loaded.resolve();
    }).fail(function(error_message, data) {
        loaded.reject(error_message, data.statusText);
    });

    return loaded.promise();
}
