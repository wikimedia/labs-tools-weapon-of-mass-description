function sendForm() {
	swal("Your data are being processed right now");
	$('#send').disabled = true;
}

function fillItems() {
	var items = $('#items').val().split('\n');
	for (var i = 0; i < items.length; i++) {
		var item = items[i];
	}
}
