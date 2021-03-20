import sublime
import sublime_plugin
import re
import sys
import collections

ST3 = sublime.version() >= '3000'

try:
    from . import inflection
except ValueError: # HACK: for ST2 compatability
    import inflection

# SECTION: FUNCTIONS WITHOUT SIDE EFFECTS THAT ARE USED TO COMPOSE COMMANDS
def isa(*types):
    return lambda x: isinstance(x, types)

iterable = isa(collections.Iterable)

def offset_region(region, offset):
    return sublime.Region(region.a + offset, region.b + offset)

def order_regions(regions):
    order = lambda r: (r.begin(), r.end())
    return sorted(regions, key=order)

class Replacement:
    def __init__(self, region, text): 
        self.region = region
        self.text = text
        self.selection = sublime.Region(region.begin(), region.begin()+len(text))

# SECTION: FUNCTIONS WITH SIDE EFFECTS THAT ARE USED TO COMPOSE COMMANDS
def set_selection(view, regions):
    # NOTE: we need to materialize a possible iterator before clearing selection,
    #       as mapping selection is a common techique.
    if iterable(regions):
        regions = list(regions)

    view.sel().clear()
    add_selection(view, regions)
    view.show(view.sel())

def add_selection(view, regions):
    if iterable(regions):
        if ST3:
            view.sel().add_all(list(regions))
        else:
            # .add_all() doesn't work with python lists in ST2
            for region in regions:
                view.sel().add(r)
    else:
        view.sel().add(regions)

def set_replacements(view, edit, replacements):
    replacements = list(replacements) if iterable(replacements) else replacements
    regions = order_regions([replacement.region for replacement in replacements])
    for region1, region2 in zip(regions, regions[1:]):
        if region1.intersects(region2): return # do nothing if replacements step over each other
    selections = []
    offset = 0
    for replacement in replacements:
        view.replace(edit, offset_region(replacement.region, offset), replacement.text)
        selections.append(offset_region(replacement.selection, offset))
        offset += len(replacement.text) - replacement.region.size()
    set_selection(view, selections)

class PluralizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        set_replacements(self.view, edit,
            map(lambda selection: Replacement(selection, inflection.pluralize(self.view.substr(selection))), 
                self.view.sel()))

class SingularizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        set_replacements(self.view, edit,
            map(lambda selection: Replacement(selection, inflection.singularize(self.view.substr(selection))), 
                self.view.sel()))

class OrdinalizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        set_replacements(self.view, edit,
            map(lambda selection: Replacement(selection, inflection.ordinalize(self.view.substr(selection))), 
                self.view.sel()))

class TransliterateToAsciiCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        set_replacements(self.view, edit,
            map(lambda selection: Replacement(selection, inflection.transliterate(self.view.substr(selection))), 
                self.view.sel()))

