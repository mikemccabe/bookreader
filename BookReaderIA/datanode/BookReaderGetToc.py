import sys
from iabook import Book
from lxml import etree
import re
import json

abbyy_ns = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'

def main(args):
    (item_id, doc, path, callback) = args

    iabook = Book(item_id, doc, path)
    toc = get_toc(iabook)

    print '%s( %s )' % (callback, json.dumps(toc))

# This version: very quick, very dirty!  Just gather every word on the
# toc page until we come to a number.  Assume the number is a page
# number, and use the gathered words as the chapter title.
#
# With just a few heuristics to keep from going too badly astray.
def get_toc(iabook):
    scandata = iabook.get_scandata()
    djvu = iabook.get_djvu_xml()
    #abbyy = iabook.get_abbyy()

    context = etree.iterparse(djvu, tag='OBJECT')
    # context = etree.iterparse(abbyy, tag=abbyy_ns+'page')

    scandata_ns = iabook.scandata_ns

    result = []
    seen_toc_page = False
    leafcount = iabook.get_leafcount()
    if leafcount is None:
        leafcount = 999 # low, but this'll exclude dates
    sd_iter = iabook.get_scandata_pages_djvu()
    # sd_iter = iabook.get_scandata_pages()
    for i, (event, page) in enumerate(context):
        page_scandata = sd_iter.next()
        if page_scandata is None:
            continue
        page_type = page_scandata.find(scandata_ns + 'pageType').text.lower()
        # print "%s: %s" % (i, page_type)
        if page_type != 'contents':
            if seen_toc_page:
                # also check here to see if it might be one.
                break
            else:
                continue
        seen_toc_page = True
        seen_arabic = False
        
        pobj = djvupage(page)
        # pobj = abbyypage(page)
        words_so_far = []
        firstword = True
        prev_word = ''
        for word in pobj.get_words():
            if firstword:
                if word.lower() == 'contents':
                    prev_word = word
                    continue
                firstword = False
            if not seen_arabic:
                as_r = rnum_to_int(word)
            else:
                as_r = 0
            as_d = 0
            if word.isdigit():
                as_d = int(word)
            if as_d > leafcount:
                as_d = 0
            if (len(words_so_far) > 0
                and (as_d != 0 or as_r != 0)
                and prev_word.lower() not in labels):
                labelwords, titlewords = guess_label(words_so_far)
                if as_r != 0:
                    pagenum = word
                else:
                    pagenum = as_d
                    seen_arabic = True
                result.append({'level':0, 'label':(' '.join(labelwords)).strip(),
                               'title':(' '.join(titlewords)).strip(), 'pagenum':pagenum})
                words_so_far = []
            else:
                words_so_far.append(word)
            prev_word = word

        page.clear()
    return result

labels = ('chapter', 'part', 'section', 'book',
#              'preface', 'appendix', 'footnotes'
          )
def guess_label(words):
    labelwords = []
    if len(words) > 1:
        if words[0].lower() in labels:
            labelwords.append(words.pop(0))
            if len(words) > 1 and (words[0].isdigit()
                                   or rnum_to_int(words[0]) != 0):
                labelwords.append(words.pop(0))
    return labelwords, words

rnums = {
    'i':1, 'ii':2, 'iii':3, 'iv':4, 'v':5,
    'vi':6, 'vii':7, 'viii':8, 'ix':9, 'x':10,
    'xi':11, 'xii':12, 'xiii':13, 'xiv':14, 'xv':15,
    'xvi':16, 'xvii':17, 'xviii':18, 'xix':19, 'xx':10,
    'xxi':21, 'xxii':22, 'xxiii':23, 'xxiv':24, 'xxv':25,
    'xxvi':26, 'xxvii':27, 'xxviii':28, 'xxix':29, 'xxx':30,
    'xxxi': 31, 'xxxii': 32, 'xxxiii': 33, 'xxxiv':34, 'xxxv':35,
    'xxxvi':36, 'xxxvii':37, 'xxxviii':38, 'xxxix':39, 'xl':40,
    'xli':41, 'xlii':42, 'xliii':43, 'xliv':44, 'xlv':45,
    'xlvi':46, 'xlvii':47, 'xlviii':48, 'xlix':49, 'l':50,
    'li':51, 'lii':52, 'liii':53, 'liv':54, 'lv':55,
    'lvi':56, 'lvii':57, 'lviii':58, 'lix':59, 'lx':60,
    'lxi':61, 'lxii':62, 'lxiii':63, 'lxiv':64, 'lxv':65,
    'lxvi':66, 'lxvii':67, 'lxviii':68, 'lxix':69, 'lxx':70,
    # lxx lccc
    }
def rnum_to_int(r):
    r = r.lower()
    if r in rnums:
        return rnums[r]
    return 0

    
class djvupage(object):
    def __init__(self, page):
        self.page = page
    def get_words(self):
        lines = self.page.findall('.//LINE')
        for line in lines:
            words = line.findall('.//WORD')
            for word in words:
                text = word.text
                text = re.sub(r'[\s.:]', '', text)
                yield text


class abbyypage(object):
    def __init__(self, page):
        self.page = page
    def get_words(self):
        findexpr = './/'+abbyy_ns+'charParams'
        chars = []
        for char in self.page.findall(findexpr):
            if char.get('wordStart') == 'true':
                if len(chars) > 0:
                    yield ''.join(c.text for c in chars)
                    chars = []
            if char.text not in (' ', '.', '"', '\'', ':'):
                chars.append(char)
            else:
                pass
        if len(chars) > 0:
            yield ''.join(c.text for c in chars)
            chars = []


if __name__ == '__main__':
    main(sys.argv[1:])
