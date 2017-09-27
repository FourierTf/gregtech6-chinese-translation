# GT6-Translation RegexReplacer.py
# by Tanimodori CC-BY-NC-SA 4.0

import sys
import codecs
import re
import os.path
import json
import argparse
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())  # utf-8 output

# Paths
parser = argparse.ArgumentParser(
    description='A simple regex-based replacer dealt with GregTech6 Chinese Translasion')
parser.add_argument(
    'translated', help='Filepath of currently translated GregTech.lang')
parser.add_argument('original', help='Filepath of original GregTech.lang')
parser.add_argument(
    'glossary', help='Filepath of glossary, auto-create if not exist')
parser.add_argument('pattern', help='Filepath of regex patterns')
parser.add_argument('output', help='Filepath of output GregTech.lang')
args = parser.parse_args()

path_of_translated = args.translated
path_of_original = args.original
path_of_output = args.output
path_of_glossary = args.glossary
path_of_pattern = args.pattern

# Settings

# To delete item only exist in translated file - Must be False
delete_obsolete_item = False
# To Use translated translations instead of the processed ones
respect_translated = False
allow_partly_translation = False      # To allow unknown mainWord in translation
# LearnGlossary = True                # To learn Glossary


class pattern:
    instances = []

    def __init__(self, nameString, valueString, repl, priority=-1):
        self.nameString = nameString
        self.nameRegex = re.compile(nameString)
        self.valueString = valueString
        self.valueRegex = re.compile(valueString)
        self.repl = repl
        self.priority = priority
        pattern.instances.append(self)

    #@classmethod
    # def cleanupGlossary(cls):

    @classmethod
    def loadFile(cls, path):
        with open(path, 'r', encoding='utf-8') as f:
            arr = json.loads(f.read())
            if len(arr) > 0:
                for item in arr:
                    pattern(item['name'], item['value'],
                            item['repl'], item['priority'])


class LangItem:
    def __init__(self, key, en='', zh=''):
        self.key = key
        self.en = en
        self.zh_old = zh
        self.zh_new = zh


class LangItemCollection:
    def __init__(self, original, translated):
        """Store original and translated in one sorted dict"""
        self.items = {}
        self.loadFile(path_of_original, True, delete_obsolete_item)
        self.loadFile(path_of_translated, False, delete_obsolete_item)
        sorted(self.items.items(), key=lambda x: x[0])

    def loadFile(self, path, isoriginal, delete_obsolete=False):
        with open(path, 'r', encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l.startswith('S:'):
                    i = l.index('=')
                    k = l[2:i]
                    v = l[i + 1:]
                    if k not in self.items:
                        if (not isoriginal) and delete_obsolete:
                            continue
                        self.items[k] = LangItem(k, '', '')
                    if isoriginal:
                        self.items[k] = LangItem(k, v, '')
                    else:
                        self.items[k] = LangItem(k, '', v)

    def process(self, patterns, glossary):
        """Process this LangItemCollection with given partterns and glossary"""
        for _kv in self.items.items():
            # Decapsule
            _item = _kv[1]
            # Invalid items or items that needn't process
            if _item.en == '' or (_item.zh_old != ''and respect_translated):
                continue
            # Search for patterns whose 'name' matches item.en
            # Order by priority in desending
            _patterns_to_be_processd = sorted(filter(lambda x: x.nameRegex.match(
                _item.key) is not None, pattern.instances), key=lambda x: x.priority, reverse=True)
            _item.main_word_en = _item.en
            # If have any matched pattern's name
            if len(_patterns_to_be_processd) > 0:
                # Init a stack for item
                _item.pattern_stack = []
                for _p in _patterns_to_be_processd:
                    # Match the pattern's value
                    _matched = _p.valueRegex.match(_item.main_word_en)
                    if _matched is not None:
                        # Value matched
                        _item.pattern_stack.append(_p)
                        # Set next main word
                        _item.main_word_en = _matched.group(1)
                # Get the main word from the glossary
                _item.main_word_zh = glossary.get_main_word(
                    _item.main_word_en, _item.key)
                if _item.main_word_zh is None:
                    # No available translation of this glossary
                    # TODO add a debug info
                    if allow_partly_translation:
                        # Using partly translation
                        _item.main_word_zh = _item.main_word_en
                    else:
                        # Using the original
                        _item.zh_new = _item.zh_old
                        # Next item
                        continue
                # Have available or partly translation
                _item.zh_new = _item.main_word_zh
                # Replace in a reserved order
                for _p in _item.pattern_stack[::-1]:
                    _item.zh_new = _p.repl.format(_item.zh_new)
            else:
                # No matched patterns
                _item.zh_new = _item.zh_old

    def save_to(self, path):
        """Save this langFile to a given path"""
        with open(path, 'w', encoding='utf-8') as f:
            # Writes heading
            f.write(
                '# Configuration file\n\nenablelangfile {\n    B:UseThisFileAsLanguageFile=true\n}\n\n\nlanguagefile {\n')
            # Sort in the order of keys
            for _kv in sorted(self.items.items(), key=lambda x: x[0]):
                _item = _kv[1]
                f.write('    S:{0}={1}\n'.format(_item.key, _item.zh_new))
            # Writes ending
            f.write('}\n\n\n')

# TODO
# class PatternItem:
#    def __init__(self,name,value,repl,priority):
#        self.name=name
#        self.value=value
#        self.repl=repl
#        self.priority=priority
#
# class PatternCollection:
#    pass


class Glossary:
    def __init__(self, file_path):
        if os.path.isfile(path_of_glossary):
            try:
                with open(path_of_glossary, 'r', encoding='utf-8') as f:
                    self.items = json.load(f)
            except:
                self.items = {}
        else:
            self.items = {}

    def save_to(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False,
                      sort_keys=True, indent=4)

    def get_main_word(self, word, key):
        if word not in self.items:
            return None
        obj = self.items[word]
        if type(obj) is str:
            return obj
        else:
            fallback = None
            for k, v in obj.items():
                if k == '.*':
                    fallback = v
                    continue
                if re.match(k, key):
                    return v
            return fallback


if __name__ == '__main__':
    # Load File
    _lang = LangItemCollection(path_of_original, path_of_translated)
    pattern.loadFile(path_of_pattern)
    _g = Glossary(path_of_glossary)
    _lang.process(pattern.instances, _g)
    _lang.save_to(path_of_output)
    _g.save_to(path_of_glossary)
