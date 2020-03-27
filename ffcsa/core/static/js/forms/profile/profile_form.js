(function ($) {
  $(function () {
    geoXml = new geoXML3.parser()
    geoXml.parse(static_url + 'docs/delivery_area.kml')

    var defaultBounds = new google.maps.LatLngBounds(
      new google.maps.LatLng(44.222193, -123.207548))

    var options = {
      bounds: defaultBounds,
      types: ['address'],
    }

    var home_delivery_toggle = $('#id_home_delivery')
    var dropsite_div = $('.input_id_drop_site')
    var delivery_info_div = $('#delivery_information')
    var addressCheckModal = $('#addressCheckModal')

    if (home_delivery_toggle.attr('checked')) {
      dropsite_div.hide()
      delivery_info_div.show()
    }

    // behavior when modal is closed
    var success = false
    addressCheckModal.on('hide.bs.modal', function () {
      if (!success) {
        home_delivery_toggle.attr('checked', false)
        dropsite_div.show()
        delivery_info_div.hide()
      } else {
        dropsite_div.hide()
        delivery_info_div.show()
      }
    })

    var modalAddressInput = $('#address-check-input')
    var addressInput = $('#id_delivery_address')
    var checkBtn = $('#check-address')
    var changeBtn = $('#change_address')
    var checkCancelBtn = $('#check-address-cancel')

    var autocomplete = new google.maps.places.Autocomplete(modalAddressInput[0], options)
    autocomplete.addListener('place_changed', function () {
      checkBtn.show()
      checkCancelBtn.hide()
    })

    changeBtn.click(function (e) {
      e.preventDefault()
      addressCheckModal.modal('show')
    })

    checkBtn.click(function () {
      checkBtn.addClass('spinner')
      var p = autocomplete.getPlace()

      // invalid/incomplete address
      if (!p) {
        $('#address-check-group').addClass('has-error')
        $('#error-message').html('Please enter a valid address')
        return
      }

      for (var i = 0; i < geoXml.docs[0].gpolygons.length; i++) {
        if (google.maps.geometry.poly.containsLocation(p.geometry.location, geoXml.docs[0].gpolygons[i])) {
          success = true

          addressInput.val(p.formatted_address)
          addressInput.parent('.form-group').removeClass('has-error')

          addressCheckModal.modal('hide')
        }
      }

      if (!success) {
        $('#address-check-group').addClass('has-error')
        $('#error-message').html('We do not currently offer delivery service to this address. Please <a href="mailto:fullfarmcsa@deckfamilyfarm.com">contact us</a> to be notified when our delivery options expand.')
        checkCancelBtn.show()
        checkBtn.hide()
        checkBtn.removeClass('spinner')
      }
    })

    // behavior when modal is opened
    addressCheckModal.on('shown.bs.modal', function () {
      success = false

      checkBtn.show()
      checkCancelBtn.hide()
      checkBtn.removeClass('spinner')
      $('#address-check-group').removeClass('has-error')
      $('#error-message').html('')
    })

    // show/hide dropsite & address information when the toggle is changed
    home_delivery_toggle.change(function () {
      if (home_delivery_toggle.attr('checked')) {
        addressCheckModal.modal('show')
      } else {
        dropsite_div.show()
        delivery_info_div.hide()
      }
    })
  })
})(jQuery)
