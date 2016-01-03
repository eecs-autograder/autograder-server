'use strict';

function to_local_date(date_str)
{
    return new Date(date_str).toLocaleString();
}

function diff_to_table(diff)
{
    var slot1 = [];
    var slot2 = [];

    for (var index in diff)
    {
        var item = diff[index];
        var prefix = item.slice(0, 2)
        if (prefix === '- ')
        {
            slot1.push(item);
        }
        else if (prefix === '+ ')
        {
            slot2.push(item);
        }
        else if (prefix === '  ') // two spaces
        {
            _pad_if_needed(slot1, slot2);
            slot1.push(item);
            slot2.push(item);
        }
    }

    _pad_if_needed(slot1, slot2);

    var container = $('<div>');
    var table = $((
        '<table class="table table-condensed table-bordered">' +
            '<thead>' +
                '<tr>' +
                    '<th>Expected</th>' +
                    '<th>Actual</th>' +
                '</tr>' +
            '</thead>' +
        '</table>'
    ));
    for (var index in slot1)
    {
        var row = $('<tr>');
        var left = $('<td>');
        var right = $('<td>');
        left.text(slot1[index]);
        right.text(slot2[index]);
        row.append(left, right);
        table.append(row);
    }
    // console.log(table.html());
    container.append(table);
    return container.html();
}

function _pad_if_needed(slot1, slot2)
{
    if (slot1.length === slot2.length)
    {
        return;
    }

    var to_pad = null;
    var bigger = null;
    if (slot1.length > slot2.length)
    {
        bigger = slot1;
        to_pad = slot2;
    }
    else
    {
        bigger = slot2;
        to_pad = slot1
    }

    while (to_pad.length < bigger.length)
    {
        to_pad.push('');
    }
}

