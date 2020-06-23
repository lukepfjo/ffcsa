;(function ($) {
  $(function () {

    var variations = $('#add-cart input[name=variation]')

    var showImage = function (id) {
      var image = $(id)
      if (image.length == 1) {
        $('#product-images-large li').hide()
        image.show()
      }
    }

    // on selection of an option, reduce the list of variations to the one
    // matching all the selected options - if there is one, show it and hide
    // the others
    variations.change(function (event) {
      var variation = $(event.target)
      // var variation = $.grep(variations, function(v) {
      //     var valid = true;
      //     $.each(selections, function() {
      //         valid = valid && v[this.name] == this[this.selectedIndex].value;
      //     });
      //     return valid;
      // });
      // if (variation.length == 1) {
      $('#variations li').hide()
      var sku = variation.val()
      $('#variation-' + sku).show()
      // showImage('#image-' + sku.image_id + '-large');
      // }
    })
    // variations.change();

    // show enlarged image on thumbnail click
    $('#product-images-thumb a').click(function () {
      showImage('#' + $(this).attr('id') + '-large')
      return false
    })

  })
})(jQuery)
