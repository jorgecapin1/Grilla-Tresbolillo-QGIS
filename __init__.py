# -*- coding: utf-8 -*-
def classFactory(iface):
    from .tresbolillo_plugin import TresbolilloGridGeneratorPlugin
    return TresbolilloGridGeneratorPlugin(iface)
