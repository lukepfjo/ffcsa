jQuery(function ($) {
    $(document).ready(function () {
        // validate / submit the donate-form
        var validateOpts = {
            errorClass: 'help-block',
            highlight: function (element) {
                $(element).closest('.form-group').addClass('has-error');
            },
            success: function (element) {
                $(element).closest('.form-group').removeClass('has-error');
            },
        };

        var donateModal = $('#donateModal');
        donateModal.detach();

        var donateModalInit = false;
        $('#donate-button').click(function () {
            donateModal.modal('show');
        });

        // One time payments
        donateModal.on('shown.bs.modal', function () {
            donateModal.appendTo('body');
            if (!donateModalInit) {
                donateModalInit = true;

                $('#submit-donation').click(function () {
                    var form = document.getElementById('donate-form');
                    if (!$(form).valid()) return;
                    form.submit();
                });

                $('#donate-form').validate(validateOpts);
            }
        })

    });
});
