import json
import pathlib
import re
from typing import Union

import pandas

try:
    from utils import compress
except:
    import pathlib
    import sys

    sys.path.append(pathlib.Path(__file__).parent.parent.__str__())
    from utils import compress


def docx_handler(file_path: Union[pathlib.Path, str]) -> pathlib.Path:
    docx_path = compress.uncompress(file_path)
    content = docx_path.joinpath('word/document.xml').read_text(encoding='utf-8')
    content = re.sub(r'[\r\n]', '', content)
    content = re.sub(r'<w:p\s.+?<w:t(\s[^<>]*?)?>', '\n', content)
    content = re.sub(r'<[^<>]+>', '', content)
    resolved_path = pathlib.Path(docx_path.__str__() + '_resolved.txt')
    with open(resolved_path, 'w', encoding='utf-8') as _f:
        _f.write(content)
    return resolved_path


def xlsx_handler(file_path: Union[pathlib.Path, str]):
    xlsx_file = pandas.read_excel(file_path, sheet_name=None)

    with open(pathlib.Path(file_path.__str__() + '_resolved.txt'), 'w', encoding='utf-8') as _f:
        for sheet in xlsx_file:
            _f.write(xlsx_file[sheet].to_dict(orient='index').__str__() + '\n')


def pptx_handler():
    pass


if __name__ == '__main__':
    # docx_handler('cache/utils.docx')
    # xlsx_handler('cache/tttt/email.xlsx')
    pass
