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
      if (unitPrice.attr('type') === 'hidden') {
        // if here, then there are multiple variations, so we don't need the margin input
        $('<td>-</td>').insertAfter(unitPriceTd)
        return
      }
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
    var margin_inputs = $('.field-margin > input')

    function init (i, input) {
      var vendorPrice = $('#' + input.id.replace('-margin', '-vendor_price'))
      var unitPrice = $('#' + input.id.replace('-margin', '-unit_price'))

      updateMargins(vendorPrice, unitPrice, input)
      vendorPrice.change(function () {
        updateMargins(vendorPrice, unitPrice, input)
      })
      unitPrice.change(function () {
        updateMargins(vendorPrice, unitPrice, input)
      })
      $(input).change(function () {
        updateMargins(vendorPrice, unitPrice, input, true)
      })
    }

    margin_inputs.each(init)

    django.jQuery(document).on('formset:added', function (event, $row, formsetName) {
      if (formsetName === 'variations') {
        $row.find('.field-margin > input').each(init)
      }
    })
  }
})