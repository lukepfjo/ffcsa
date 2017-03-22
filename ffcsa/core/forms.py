from mezzanine.pages.admin import PageAdminForm


class CategoryAdminForm(PageAdminForm):
    def clean_content(form):
        # make the content field not required for Category Pages
        return form.cleaned_data.get("content")
