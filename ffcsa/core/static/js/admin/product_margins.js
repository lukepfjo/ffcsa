jQuery(function ($) {

  var isChangelist = $('.changelist-content').length == 1

  var marginElement = '<input type="text">'

  var updateMargins = function (vendorInput, unitInput, marginInput, marginChanged) {
    v = $(vendorInput)
    u = $(unitInput)
    m = $(marginInput)

    var unitVal = u.val()
    var vendorVal = v.val()

    if (marginChanged) {
      var mVal = m.val()
      if (!mVal) mVal = 32
      mVal = mVal / 100
      u.val(Math.round(vendorVal / (1 - mVal) * 100) / 100)
    } else if (unitVal) {
      if (vendorVal) {
        m.val(Math.round((unitVal - vendorVal) / unitVal * 100))
      } else {
        // default to 32% markup
        m.val(32)
        v.val(Math.round(unitVal * .68 * 100) / 100)
      }
    } else if (vendorVal) {
      m.val(32)
      u.val(Math.round(vendorVal / .68 * 100) / 100)
    } else {
      m.val(undefined)
    }
  }

  if (isChangelist) {
    $('<th>% Margin</th>').insertAfter($('.result-list thead th.column-unit_price'))

    $('.result-list tbody tr').each(function (i, row) {
      row = $(row)
      var vendorPrice = row.find('.field-vendor_price input')
      var unitPriceTd = row.find('.field-unit_price')
      var unitPrice = $(unitPriceTd).find('input')
      var margin = $('<td>' + marginElement + '</td>').insertAfter(unitPriceTd)
      $(margin).find('input').css('width', '50px')

      updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
      vendorPrice.change(function () {
        updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
      })
      unitPrice.change(function () {
        updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
      })
      $(margin).find('input').change(function () {
        updateMargins(vendorPrice, unitPrice, $(margin).find('input'), true)
      })
    })
  } else {
    $('<div class=\'form-cell\'>% Margin</div>').insertAfter($('.legend div.member-price'))

    var items = $('#variations-group').find('.items > div').not('.empty-form')
    var vendorPrice = $(items).find('.vendor_price input')
    var unitPriceDiv = $(items).find('.unit_price')
    var unitPrice = $(unitPriceDiv).find('input')
    var margin = $('<div class="item form-cell margin">' + marginElement + '</div>').insertAfter(unitPriceDiv)

    updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
    vendorPrice.change(function () {
      updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
    })
    unitPrice.change(function () {
      updateMargins(vendorPrice, unitPrice, $(margin).find('input'))
    })
    $(margin).find('input').change(function () {
      updateMargins(vendorPrice, unitPrice, $(margin).find('input'), true)
    })
  }
})