"""Read FTB's optional-comma SNBT for structural validation only."""
import json
import re


class Parser:
    def __init__(self, text):
        self.text, self.pos = text, 0

    def skip(self):
        while self.pos < len(self.text):
            if self.text[self.pos].isspace() or self.text[self.pos] == ',':
                self.pos += 1
            elif self.text.startswith('//', self.pos):
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end < 0 else end + 1
            elif self.text.startswith('/*', self.pos):
                end = self.text.find('*/', self.pos + 2)
                if end < 0:
                    raise ValueError('Unterminated comment')
                self.pos = end + 2
            else:
                break

    def string(self):
        quote, start = self.text[self.pos], self.pos
        self.pos += 1
        escaped = False
        while self.pos < len(self.text):
            char = self.text[self.pos]
            self.pos += 1
            if char == quote and not escaped:
                token = self.text[start:self.pos]
                if quote == '"':
                    return json.loads(token)
                return token[1:-1].replace("\\'", "'").replace('\\\\', '\\')
            escaped = char == '\\' and not escaped
        raise ValueError('Unterminated quoted string')

    def token(self, key=False):
        start = self.pos
        excluded = '\t\r\n ,{}[]' + (':' if key else '')
        while self.pos < len(self.text) and self.text[self.pos] not in excluded:
            self.pos += 1
        if self.pos == start:
            raise ValueError(f'Expected token at {self.pos}')
        return self.text[start:self.pos]

    def value(self):
        self.skip()
        if self.pos >= len(self.text):
            raise ValueError('Unexpected end of SNBT')
        char = self.text[self.pos]
        if char in '\"\'':
            return self.string()
        if char == '{':
            self.pos += 1
            result = {}
            while True:
                self.skip()
                if self.text[self.pos] == '}':
                    self.pos += 1
                    return result
                key = self.string() if self.text[self.pos] in '\"\'' else self.token(True)
                self.skip()
                if self.text[self.pos] != ':':
                    raise ValueError(f'Expected colon after {key} at {self.pos}')
                self.pos += 1
                if key in result:
                    raise ValueError(f'Duplicate key {key}')
                result[key] = self.value()
        if char == '[':
            self.pos += 1
            self.skip()
            if self.text[self.pos:self.pos + 2] in ['B;', 'I;', 'L;']:
                self.pos += 2
            result = []
            while True:
                self.skip()
                if self.text[self.pos] == ']':
                    self.pos += 1
                    return result
                result.append(self.value())
        token = self.token()
        if token in ['true', 'false']:
            return token == 'true'
        if re.fullmatch(r'[+-]?\d+[bBsSlL]?', token):
            return int(token.rstrip('bBsSlL'))
        if re.fullmatch(r'[+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?[fFdD]?', token):
            return float(token.rstrip('fFdD'))
        return token


def loads(text):
    parser = Parser(text)
    result = parser.value()
    parser.skip()
    if parser.pos != len(text):
        raise ValueError(f'Trailing SNBT at {parser.pos}')
    return result
