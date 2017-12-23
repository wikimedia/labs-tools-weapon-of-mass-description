function sendForm() {
	swal("Your data are being processed right now");
	$('#send').disabled = true;
	var items = $("input[name^='new_label_']");
	var payload = [];
	for (var i = 0; i < items.length; i++) {
		var label = items[i].value;
		var description = $("input[name=" + items[i].name.replace('label', 'description') + "]").val();
		var qid = items[i].name.replace('new_label_', '');
		var imagepayload = {
				'label': label,
				'description': description,
				'qid': qid,
				'lang': $('#langs').val()
		};
		payload.push(imagepayload);
		console.log(qid);
	}
	$.postJSON('https://tools.wmflabs.org/weapon-of-mass-description/api-edit', payload, function (data) {
		console.log(data);
		$('#send')[0].disabled = false;
		$('tbody').empty();
	})
}

function fillItems() {
	$('tbody').empty();
	var items = $('#items').val().split('\n');
	for (var i = 0; i < items.length; i++) {
		var item = items[i];
		var url = 'https://tools.wmflabs.org/weapon-of-mass-description/api-item?item=' + item;
		if ($('#spokablelangs').val() != "") {
			url += "&langs=" + $('#spokablelangs').val().replaceAll('\n', '|');
		}
		$.getJSON(url, function (data) {
			var labelhtml = "<ul>";
			for (var j = 0; j < data.items[0].labels.length; j++) {
				var lang = data.items[0].labels[j].language;
				var label = data.items[0].labels[j].value;
				labelhtml += "<li>" + lang + ": " + label + "</li>";
			}
			labelhtml += "</ul>";
			var descriptionhtml = "<ul>"
			for (var j = 0; j < data.items[0].descriptions.length; j++) {
				var lang = data.items[0].descriptions[j].language;
				var description = data.items[0].descriptions[j].value;
				descriptionhtml += "<li>" + lang + ": " + description + "</li>";
			}
			descriptionhtml += "</ul>";
			var html = `
			<tr>
					<td><a href="https://wikidata.org/entity/` + item + `">` + item + `</a></td>
					<td>
							<div class="input-field">
									<input placeholder="new label" name="new_label_` + item + `" type="text">
							</div>
					<td>
							<div class="input-field">
									<input placeholder="new description" name="new_description_` + item + `" type="text">
							</div>
					</td>
					<td>Wikipedia</td>
					<td>` + labelhtml + `</td>
					<td>` + descriptionhtml + `</td>
			</tr>`;
			$('tbody').append(html);
		});
		$('#send')[0].disabled = false;
	}
}


$( document ).ready(function() {
	$.getJSON('https://tools.wmflabs.org/weapon-of-mass-description/api-langs', function (data) {
		for (var i = 0; i < data['langs'].length; i++) {
			if (data['langs'][i]['code'] == 'cs') {
				var row = '<option value="' + data['langs'][i]['code'] + '" selected>' + data['langs'][i]['name'] + '</option>';
			}
			else {
				var row = '<option value="' + data['langs'][i]['code'] + '">' + data['langs'][i]['name'] + '</option>';
			}
			$('#langs').append(row);
		}
	});
});
