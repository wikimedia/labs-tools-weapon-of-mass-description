function sendSettings() {
  var payload = {
      suggestitems: Number($('input[name="suggestitems"]').val()),
      atleastonelang: false,
      openlinksinnewtab: false,
      optinoverride: false,
  };
  $.postJSON('api-settings', payload, function (data) {
    swal("Settings submitted", "", "success");
    console.log(data);
  });
}
