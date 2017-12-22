function sendForm() {
	swal("Your data are being processed right now");
	$('#send').disabled = true;
}

function fillItems() {
	var items = $('#items').val().split('\n');
	for (var i = 0; i < items.length; i++) {
		var item = items[i];
		var url = 'https://tools.wmflabs.org/weapon-of-mass-description/api-item?item=' + item;
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
					<td>` + item + `</td>
					<td>
							<div class="input-field">
									<input placeholder="new label" name="new_label_` + item + `" type="text">
							</div>
					<td>
							<div class="input-field">
									<input placeholder="new description" id="new_description_` + item + `" type="text">
							</div>
					</td>
					<td>Wikipedia</td>
					<td>` + labelhtml + `</td>
					<td>` + descriptionhtml + `</td>
			</tr>`;
			$('tbody').append(html);
		});
	}
}
