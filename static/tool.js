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
			console.log(data);
			for (var i = 0; i < data.items[0].labels.length; i++) {
				var lang = data.items[0].labels[i].language;
				var label = data.items[0].labels[i].value;
				labelhtml += "<li>" + lang + ": " + label + "</li>";
			}
			labelhtml += "</ul>";
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
					<td>$3.76</td>
			</tr>`;
			$('tbody').append(html);
		});
	}
}
