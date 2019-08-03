jQuery(function ($) {
  $(document).ready(function () {
    // Stripe loaded in html
    var stripe = Stripe($('#stripeApiKey').val())

    // Create stripe ui elements
    var elements = stripe.elements()
    var cardNumber = elements.create('cardNumber')
    var cardExpiry = elements.create('cardExpiry')
    var cardCvc = elements.create('cardCvc')

    function init () {
      $('#cc-details #ach-details #crypto-details').collapse()

      $('#paymentTypesACH').prop('checked', true)

      // we only need to mount these elements if we are collecting cc details
      if ($('#card-number').length > 0) {
        // mount stripe ui elements
        cardNumber.mount('#card-number')
        cardExpiry.mount('#card-expiry')
        cardCvc.mount('#card-cvc')
      }

      // dynamically show payment form depending on payment type
      $('input[type=radio][name=paymentType]').change(function () {
        if (this.value === 'CC') {
          $('#cc-details').collapse('show')
          $('#ach-details').collapse('hide')
          $('#crypto-details').collapse('hide')
        } else if (this.value === 'ACH') {
          $('#cc-details').collapse('hide')
          $('#ach-details').collapse('show')
          $('#crypto-details').collapse('hide')
        } else if (this.value === 'DEFAULT') {
          $('#cc-details').collapse('hide')
          $('#ach-details').collapse('hide')
          $('#crypto-details').collapse('hide')
        } else {
          $('#cc-details').collapse('hide')
          $('#ach-details').collapse('hide')
          $('#crypto-details').collapse('show')
        }
      })
    }

    function disableSensitiveInputs () {
      $('select[name=achAccountType], input[name=achRoutingNumber], input[name=achAccountNumber], input[name=achAccountName]').prop('disabled', true)
    }

    // validate / submit the subscribe-form
    var validateOpts = {
      errorClass: 'help-block',
      rules: {
        amount: {
          min: 172,
          required: function () {
            return $('input[name=amount]').length > 0
          },
        },
        paymentType: {
          required: true,
        },
        achAccountName: {
          required: function () {
            return $('#paymentTypesACH').is(':checked')
          },
        },
        achAccountType: {
          required: function () {
            return $('#paymentTypesACH').is(':checked')
          },
        },
        achRoutingNumber: {
          minlength: 9,
          maxlength: 9,
          required: function () {
            return $('#paymentTypesACH').is(':checked')
          },
        },
        achAccountNumber: {
          rangelength: [4, 17],
          required: function () {
            return $('#paymentTypesACH').is(':checked')
          },
        },
        signupAcknowledgement: {
          required: function () {
            return $('input[name=signupAcknowledgement]').length > 0
          },
        },
        chargeAcknowledgement: {
          required: function () {
            return $('input[name=chargeAcknowledgement]').length > 0
          },
        },
      },
      highlight: function (element) {
        $(element).closest('.form-group').addClass('has-error')
      },
      success: function (element) {
        $(element).closest('.form-group').removeClass('has-error')
      },
      submitHandler: function (form) {
        var promise
        var isStripe = false

        if ($('#paymentTypesCC').is(':checked')) {
          isStripe = true
          promise = stripe.createToken(cardNumber)
        } else if ($('#paymentTypesACH').is(':checked')) {
          isStripe = true
          var data = {
            country: 'us',
            currency: 'usd',
            routing_number: $('input[name=achRoutingNumber]').val(),
            account_number: $('input[name=achAccountNumber]').val(),
            account_holder_name: $('input[name=achAccountName]').val(),
            account_holder_type: $('select[name=achAccountType]').val(),
          }
          promise = stripe.createToken('bank_account', data)
        } else {
          // todo handle crypto
        }

        if (isStripe) {
          // clear any existing errors
          $('#stripeErrors').text('').removeClass('alert alert-danger')

          promise.then(function (result) {
            if (result.error) {
              // Inform the customer that there was an error.
              $('#stripeErrors').text(result.error.message).addClass('alert alert-danger')
            } else {
              // Send the token to your server.
              var hiddenInput = document.createElement('input')
              hiddenInput.setAttribute('type', 'hidden')
              hiddenInput.setAttribute('name', 'stripeToken')
              hiddenInput.setAttribute('value', result.token.id)
              form.appendChild(hiddenInput)

              // don't send account info to server
              disableSensitiveInputs()
              // Submit the form
              form.submit()
            }
          })
        } else {
          // TODO handle crypto
        }
      },
    }

    $('#subscribe-form').validate(validateOpts)
    $('#edit-payment-form').validate(validateOpts)

    var amountValidateOpts = _.assign({}, validateOpts)
    delete amountValidateOpts.submitHandler
    $('#edit-payment-amount-form').validate(amountValidateOpts)

    var editPayment = $('#edit-payment')
    var editPaymentVisible = false
    var editPaymentAmount = $('#edit-payment-amount')
    var editPaymentAmountVisible = false
    var paymentModal = $('#paymentModal')
    paymentModal.detach()

    // we init here after paymentModal is detached, but before editPayment is detached
    if ($('#card-number').length > 0) {
      init()
    }

    if (editPayment.hasClass('hidden')) {
      editPayment.detach()
      editPayment.removeClass('hidden')
    }
    $('#edit-payment-info').click(function () {
      if (editPaymentAmountVisible) {
        editPaymentAmount.detach()
        editPaymentAmountVisible = false
      }
      editPayment.appendTo('#payment-container')
      editPaymentVisible = true
    })

    if (editPaymentAmount.hasClass('hidden')) {
      editPaymentAmount.detach()
      editPaymentAmount.removeClass('hidden')
    }
    $('#edit-payment-amount-btn').click(function () {
      if (editPaymentVisible) {
        editPayment.detach()
        editPaymentVisible = false
      }
      editPaymentAmount.appendTo('#payment-container')
      editPaymentAmountVisible = true
    })
    // $('#edit-payment-cancel').click(function (event) {
    //     editPayment.detach();
    // });

    var paymentModalInit = false
    $('#make-payment').click(function () {
      paymentModal.modal('show')
    })

    // One time payments
    paymentModal.on('shown.bs.modal', function () {
      paymentModal.appendTo('#payment-container')
      $('#edit-payment').detach()
      if (!paymentModalInit) {
        init()

        if ($('#paymentTypesDefault').length > 0) {
          $('#paymentTypesDefault').prop('checked', true)
        } else {
          $('#paymentTypesCC').prop('checked', true)
          $('#paymentTypesCC').trigger('change')
        }
        paymentModalInit = true

        var defaultSubmitHandler = validateOpts.submitHandler

        var submitting = false
        $('#submit-payment').click(function () {
          if (submitting) return
          submitting = true
          var form = document.getElementById('payment-form')
          if ($('#paymentTypesCC').is(':checked')) {
            defaultSubmitHandler(form)
          } else {
            form.submit()
          }
          submitting = false
        })

        var opts = _.assign({}, validateOpts)
        opts.rules.amount.min = 20

        $('#payment-form').validate(opts)
      }
    })

  })
})
