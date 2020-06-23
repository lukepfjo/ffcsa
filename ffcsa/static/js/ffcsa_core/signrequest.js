jQuery(function ($) {
  var conf = {
    subdomain: 'ffcsa', // if you are using this for a specific team set the subdomain here
    api: 'v1',
    who: 'o',
    // signers: 'first_email@example.com,second_email@example.com',
    from_email: 'fullfarmcsa@deckfamilyfarm.com',
    close: true,  // close the popup when done? default: true
    // or use next:
    next: '',  // redirect to this url when done signing themselves,
    frontend_id: '', // optional shared secret set on document to grant access to users even if they don't have access to team
  }
// these are also optional, the popup will be centered in the window opening the popup
  var popup_conf = {
    width: 460,  // width of the popup in pixels, default 460
    height: 600, // height of the popup in pixels, default the height of the window opening the popup
  }

  $('button#signrequest').on('click', function () {
    var popup = SignRequest.browser.openLoadingPopup()  // open a popup on button click right away

    popup.onAny(function (event_type, payload, event) {
      // all listeners created on the loading popup will also be registered on the popup events fired later after the we call
      // SignRequest.browser.openPopupForDocUuid...
      console.log('Event received: ' + event_type + ', payload: ' + JSON.stringify(payload))
    })

    // Async call some endpoint on your backend that creates a document using the REST API.
    $.get('/signrequest-data').then(function (response) {
      conf.signers = response.email
      // instead of opening a new popup we use the one that is 'loading' as otherwise
      // most browser popup blockers will block opening a new window here (the opening of the window comes too late after the user click).
      // we assume here your endpoint returns the uuid of the document created in the response
      SignRequest.browser.openPopupForTemplateUuid(response.template_uuid, conf, {sr_popup: popup})
      // `{sr_popup: popup}` make the library use an existing popup instead of creating a new one
    })
  })
})
