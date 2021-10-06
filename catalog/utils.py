from isbnlib import classify
from isbnlib.dev import ServiceIsDownError
from titlecase import titlecase


def get_classifier_tags(isbn: str) -> list[str]:
    try:
        classifiers = classify(isbn)
    except ServiceIsDownError:
        return []
    tags = []
    for system, value in classifiers.items():
        if system.lower() == 'fast':
            for number, description in value.items():
                tags.append(f'fast:{number};{description}')
        else:
            tags.append(f'{system.lower()}:{value}')
    return tags


def getlines(text: str) -> list[str]:
    return list(str(s) for s in filter(len, (map(str.strip, text.splitlines()))))


def split_title(title: str, separator: str = ' - ') -> list[str, str]:
    if separator in title:
        return [titlecase(s) for s in title.split(separator, 1)]
    else:
        return [titlecase(title), '']
