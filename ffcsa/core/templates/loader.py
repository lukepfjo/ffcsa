import re

from django.template import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from django.template.loaders.filesystem import Loader as FileLoader
from django.template.loaders.app_directories import Loader as AppLoader

RE = re.compile("(cartridge|mezzanine|grappelli_safe)[\\\/]+([a-zA-Z]+[\\\/]+)?templates[\\\/]+admin")


class JetLoader(BaseLoader):
    """
    This loader is used to exclude any cartridge or mezzanine admin pages. This is done because they conflict with
    the JET admin theme
    """

    def __init__(self, engine):
        self.loaders = [FileLoader(engine), AppLoader(engine)]
        self.engine = engine

    def get_dirs(self):
        return self.engine.dirs

    def get_contents(self, origin):
        if origin and RE.search(origin.name):
            raise TemplateDoesNotExist(origin)
        for loader in self.loaders:
            if origin.loader == loader:
                r = loader.get_contents(origin)
                return r

    def get_template_sources(self, template_name, template_dirs=None):
        """
        Return an Origin object pointing to an absolute path in each directory
        in template_dirs. For security reasons, if a path doesn't lie inside
        one of the template_dirs it is excluded from the result set.
        """
        for loader in self.loaders:
            gen = loader.get_template_sources(template_name, template_dirs)
            for r in gen:
                yield r
