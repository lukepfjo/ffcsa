(function ($) {
  $(function () {
    var variations = $('.product-quick-add-form select[name=variation]')

    // on selection of an option, reduce the list of variations to the one
    // matching all the selected options - if there is one, show it and hide
    // the others
    variations.change(function () {
      var variation = $(this)
      variation.closest('form').find('#variations li').hide()
      var sku = variation.val()
      $('#variation-' + sku).show()
    })
  })
})(jQuery);
