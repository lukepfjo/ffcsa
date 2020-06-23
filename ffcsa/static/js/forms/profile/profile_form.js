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
    var invite_code_div = $('.input_id_invite_code')
    var delivery_info_div = $('#delivery_information')
    var addressCheckModal = $('#addressCheckModal')

    if (home_delivery_toggle.attr('checked')) {
      dropsite_div.hide()
      if (invite_code_div) invite_code_div.hide()
      delivery_info_div.show()
    }

    // behavior when modal is closed
    var success = false
    addressCheckModal.on('hide.bs.modal', function () {
      if (!success) {
        addressInput.val('')
        home_delivery_toggle.attr('checked', false)
        dropsite_div.show()
        if (invite_code_div) invite_code_div.show()
        delivery_info_div.hide()
      } else {
        dropsite_div.hide()
        if (invite_code_div) invite_code_div.hide()
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

    function setError (msg) {
      $('#address-check-group').addClass('has-error')
      $('#error-message').html(msg)
      checkCancelBtn.show()
      checkBtn.hide()
      checkBtn.removeClass('spinner')
    }

    checkBtn.click(function () {
      checkBtn.addClass('spinner')
      var p = autocomplete.getPlace()

      // invalid/incomplete address
      if (!p) {
        setError('Please enter a valid address')
        return
      }

      for (var i = 0; i < geoXml.docs[0].gpolygons.length; i++) {
        if (google.maps.geometry.poly.containsLocation(p.geometry.location, geoXml.docs[0].gpolygons[i])) {
          success = true

          addressInput.val(p.formatted_address)
          addressInput.parent('.form-group').removeClass('has-error')
          $('#save-alert').removeClass('hidden')

          // Check if we are maxed out for the zip code
          zip = null
          p.address_components.forEach(function (c) {
            if (c.types.includes('postal_code')) {
              zip = c.long_name
              return
            }
          })

          $.ajax('/zip-check/' + zip)
          .done(function (data) {
            if (data.is_full === false) {
              addressCheckModal.modal('hide')
            } else {
              success = false
              setError('Unfortunately, our delivery route is full and we can not offer home delivery to your zip code at this time. Please check again at a later date as members change drop sites from time-to-time. You can also <a href="mailto:fullfarmcsa@deckfamilyfarm.com">contact us</a> to be notified when a spot opens up!')
            }
          })
          .fail(function () {
            success = false
            setError('An error occurred. Please try again later. Please <a href="mailto:fullfarmcsa@deckfamilyfarm.com">contact us</a> if this problem persists.')
          })
        }
      }

      if (!success) {
        setError('We do not currently offer delivery service to this address. Please <a href="mailto:fullfarmcsa@deckfamilyfarm.com">contact us</a> to be notified when our delivery options expand.')
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
        if (invite_code_div) invite_code_div.show()
        delivery_info_div.hide()
      }
    })
  })
})(jQuery)
