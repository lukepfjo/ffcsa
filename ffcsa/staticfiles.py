from collections import OrderedDict

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.contrib.staticfiles.utils import matches_patterns


class ExcludableManifestStaticFilesStorage(ManifestStaticFilesStorage):
    # TODO remove this. w/o, admin files were throwing an error
    manifest_strict = False

    def post_process(self, paths, *args, **kwargs):
        # print(paths.keys())
        # filtered_paths = [p for p in paths if p not in self._ignored_files]
        filtered_paths = OrderedDict()
        for p, val in paths.items():
            if not matches_patterns(p, settings.STATICFILES_IGNORE):
                filtered_paths[p] = val
        return super().post_process(filtered_paths, *args, **kwargs)
